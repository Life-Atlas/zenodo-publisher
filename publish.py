#!/usr/bin/env python3
"""
zenodo-publish — Markdown to Zenodo in one command.

Converts a Markdown file to PDF, deposits it on Zenodo, and returns a DOI.
Supports new deposits, version updates, and related-work linking.

Usage:
    # New publication
    python publish.py --file paper.md --title "My Paper" --description "Abstract here"

    # Dry run (creates draft, doesn't publish)
    python publish.py --file paper.md --title "My Paper" --dry-run

    # Update existing deposit with new version
    python publish.py --file paper.md --title "My Paper v2" --update 19586835

    # Link to related works
    python publish.py --file paper.md --title "My Paper" --related "10.5281/zenodo.19587944:continues"

    # Use sandbox for testing
    python publish.py --file paper.md --title "Test" --sandbox

    # Custom creator (overrides default)
    python publish.py --file paper.md --title "Paper" --creator "Doe, Jane:MIT:0000-0000-0000-0001"

Environment:
    ZENODO_TOKEN  — Personal access token (deposit:write + deposit:actions scopes)
                    Get one at: https://zenodo.org/account/settings/applications
                    Store in .env file or set as environment variable.
"""

import argparse
import os
import re
import sys
import tempfile
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

ZENODO_BASE = "https://zenodo.org/api"
ZENODO_SANDBOX = "https://sandbox.zenodo.org/api"

DEFAULT_CREATOR = {
    "name": "Waern, Nicolas",
    "affiliation": "WINNIIO AB",
    "orcid": "0009-0001-4011-8201",
}
DEFAULT_LICENSE = "cc-by-4.0"


# ---------------------------------------------------------------------------
# PDF conversion
# ---------------------------------------------------------------------------

def md_to_pdf(md_path: Path, pdf_path: Path) -> None:
    """Convert Markdown to PDF. Tries weasyprint (styled), then reportlab (basic)."""
    md_text = md_path.read_text(encoding="utf-8")

    # Option 1: weasyprint (best quality — needs system libs on Windows)
    try:
        import markdown as md_lib
        from weasyprint import HTML

        html = md_lib.markdown(md_text, extensions=["tables", "fenced_code"])
        full_html = f"""<!DOCTYPE html><html><head>
        <meta charset="utf-8"/>
        <style>
            body {{ font-family: Georgia, 'Times New Roman', serif; max-width: 750px;
                   margin: 40px auto; padding: 0 20px; font-size: 12pt; line-height: 1.6;
                   color: #111; }}
            h1 {{ font-size: 18pt; margin-bottom: 8px; }}
            h2 {{ font-size: 14pt; margin-top: 24px; border-bottom: 1px solid #ccc;
                  padding-bottom: 4px; }}
            h3 {{ font-size: 12pt; margin-top: 16px; }}
            blockquote {{ border-left: 3px solid #ccc; margin: 12px 0; padding: 8px 16px;
                         color: #555; font-style: italic; }}
            table {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
            th, td {{ border: 1px solid #ccc; padding: 6px 10px; font-size: 10pt; }}
            th {{ background: #f5f5f5; }}
            code {{ background: #f4f4f4; padding: 2px 4px; font-size: 10pt; }}
            pre {{ background: #f4f4f4; padding: 12px; overflow-x: auto; font-size: 9pt; }}
            hr {{ border: none; border-top: 1px solid #ddd; margin: 20px 0; }}
        </style></head><body>{html}</body></html>"""
        HTML(string=full_html).write_pdf(str(pdf_path))
        return
    except ImportError:
        pass

    # Option 2: reportlab (basic but always available)
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from xml.sax.saxutils import escape

        doc = SimpleDocTemplate(str(pdf_path), pagesize=A4,
                                leftMargin=25*mm, rightMargin=25*mm,
                                topMargin=20*mm, bottomMargin=20*mm)
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('Title2', parent=styles['Title'], fontSize=16, spaceAfter=12)
        h2_style = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=13, spaceAfter=8, spaceBefore=14)
        h3_style = ParagraphStyle('H3', parent=styles['Heading3'], fontSize=11, spaceAfter=6, spaceBefore=10)
        body_style = ParagraphStyle('Body2', parent=styles['Normal'], fontSize=10, leading=14, spaceAfter=6)
        quote_style = ParagraphStyle('Quote', parent=body_style, leftIndent=20, rightIndent=20, fontName='Times-Italic')

        story = []
        for line in md_text.splitlines():
            stripped = line.strip()
            if not stripped:
                story.append(Spacer(1, 4))
            elif stripped.startswith('# ') and not stripped.startswith('## '):
                story.append(Paragraph(escape(stripped[2:]), title_style))
            elif stripped.startswith('## '):
                story.append(Paragraph(escape(stripped[3:]), h2_style))
            elif stripped.startswith('### '):
                story.append(Paragraph(escape(stripped[4:]), h3_style))
            elif stripped.startswith('> '):
                story.append(Paragraph(escape(stripped[2:]), quote_style))
            elif stripped.startswith('---'):
                story.append(Spacer(1, 8))
            elif stripped.startswith('|'):
                clean = stripped.replace('|', ' | ').strip()
                story.append(Paragraph(escape(clean), body_style))
            else:
                safe = escape(stripped)
                safe = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', safe)
                safe = re.sub(r'\*(.+?)\*', r'<i>\1</i>', safe)
                story.append(Paragraph(safe, body_style))
        doc.build(story)
        return
    except ImportError:
        pass

    sys.exit(
        "ERROR: No PDF converter found.\n"
        "Install one of:\n"
        "  pip install markdown weasyprint   (best quality, needs system libs)\n"
        "  pip install reportlab             (basic, always works)"
    )


# ---------------------------------------------------------------------------
# Zenodo API
# ---------------------------------------------------------------------------

def api(method: str, path: str, token: str, base: str, **kwargs) -> requests.Response:
    """Make an authenticated Zenodo API call."""
    url = base.rstrip("/") + path
    headers = {"Authorization": f"Bearer {token}"}
    if "json" in kwargs:
        headers["Content-Type"] = "application/json"
    resp = getattr(requests, method)(url, headers=headers, **kwargs)
    if not resp.ok:
        sys.exit(f"Zenodo API error {resp.status_code}: {resp.text[:500]}")
    return resp


def parse_creator(s: str) -> dict:
    """Parse 'Name, First:Affiliation:ORCID' into a creator dict."""
    parts = s.split(":")
    creator = {"name": parts[0]}
    if len(parts) > 1 and parts[1]:
        creator["affiliation"] = parts[1]
    if len(parts) > 2 and parts[2]:
        creator["orcid"] = parts[2]
    return creator


def parse_related(s: str) -> list:
    """Parse 'doi1:relation1,doi2:relation2' into related_identifiers list."""
    if not s:
        return []
    result = []
    for item in s.split(","):
        parts = item.strip().split(":")
        if len(parts) >= 2:
            # Handle DOIs that contain colons (10.5281/zenodo.XXX)
            doi = ":".join(parts[:-1])
            relation = parts[-1]
            result.append({
                "identifier": doi,
                "relation": relation,
                "scheme": "doi",
            })
    return result


def build_metadata(args: argparse.Namespace) -> dict:
    """Build Zenodo metadata payload from CLI args."""
    keywords = [k.strip() for k in args.keywords.split(",")] if args.keywords else []

    creator = parse_creator(args.creator) if args.creator else DEFAULT_CREATOR

    pub_type = "workingpaper"
    if args.type == "article":
        pub_type = "article"
    elif args.type == "preprint":
        pub_type = "preprint"
    elif args.type == "report":
        pub_type = "report"

    meta: dict = {
        "upload_type": "publication",
        "publication_type": pub_type,
        "access_right": "open",
        "license": DEFAULT_LICENSE,
        "language": "eng",
        "title": args.title,
        "description": args.description or args.title,
        "creators": [creator],
        "keywords": keywords,
        "publication_date": args.date or None,
    }

    # Remove None values
    meta = {k: v for k, v in meta.items() if v is not None}

    related = parse_related(args.related)
    if related:
        meta["related_identifiers"] = related

    if args.funding:
        meta["grants"] = [{"id": g.strip()} for g in args.funding.split(",")]

    if args.communities:
        meta["communities"] = [{"identifier": c.strip()} for c in args.communities.split(",")]

    return {"metadata": meta}


# ---------------------------------------------------------------------------
# Main flows
# ---------------------------------------------------------------------------

def new_deposit(args: argparse.Namespace, token: str, base: str, pdf_path: Path) -> None:
    """Create a new deposit, upload PDF, set metadata, optionally publish."""
    deposit = api("post", "/deposit/depositions", token, base, json={}).json()
    dep_id = deposit["id"]
    bucket_url = deposit["links"]["bucket"]
    print(f"Deposit created: id={dep_id}")

    upload_pdf(token, bucket_url, pdf_path)

    meta = build_metadata(args)
    api("put", f"/deposit/depositions/{dep_id}", token, base, json=meta)
    print("Metadata set.")

    if args.dry_run:
        print(f"\nDry-run: deposit id={dep_id} saved but NOT published.")
        print(f"Preview: {base.replace('/api','')}/deposit/{dep_id}")
        return

    pub = api("post", f"/deposit/depositions/{dep_id}/actions/publish", token, base).json()
    print_doi(pub)


def update_deposit(args: argparse.Namespace, token: str, base: str, pdf_path: Path) -> None:
    """Create a new version of an existing deposit."""
    old_id = args.update
    print(f"Creating new version of deposit {old_id}...")

    resp = api("post", f"/deposit/depositions/{old_id}/actions/newversion", token, base)
    new_draft_url = resp.json()["links"]["latest_draft"]

    draft = requests.get(new_draft_url, headers={"Authorization": f"Bearer {token}"}).json()
    new_id = draft["id"]
    print(f"New version draft: id={new_id}")

    # Delete old files
    for f in draft.get("files", []):
        requests.delete(
            f"{base}/deposit/depositions/{new_id}/files/{f['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )

    bucket_url = draft["links"]["bucket"]
    upload_pdf(token, bucket_url, pdf_path)

    # Update metadata (merge with existing)
    existing_meta = draft["metadata"]
    new_meta = build_metadata(args)["metadata"]
    existing_meta.update({k: v for k, v in new_meta.items() if v})
    if "publication_date" not in existing_meta or not existing_meta["publication_date"]:
        from datetime import date
        existing_meta["publication_date"] = date.today().isoformat()
    api("put", f"/deposit/depositions/{new_id}", token, base, json={"metadata": existing_meta})
    print("Metadata updated.")

    if args.dry_run:
        print(f"\nDry-run: version id={new_id} saved but NOT published.")
        print(f"Preview: {base.replace('/api','')}/deposit/{new_id}")
        return

    pub = api("post", f"/deposit/depositions/{new_id}/actions/publish", token, base).json()
    print_doi(pub)


def upload_pdf(token: str, bucket_url: str, pdf_path: Path) -> None:
    """Upload a PDF to a deposit's file bucket."""
    print(f"Uploading {pdf_path.name} ({pdf_path.stat().st_size // 1024} KB)...")
    with pdf_path.open("rb") as fh:
        resp = requests.put(
            f"{bucket_url}/{pdf_path.name}",
            headers={"Authorization": f"Bearer {token}"},
            data=fh,
        )
        if not resp.ok:
            sys.exit(f"Upload error {resp.status_code}: {resp.text[:300]}")
    print("Upload complete.")


def print_doi(pub: dict) -> None:
    """Print the published DOI."""
    doi = pub.get("doi") or pub.get("metadata", {}).get("doi", "")
    doi_url = pub.get("doi_url", f"https://doi.org/{doi}")
    print(f"\nPublished!")
    print(f"DOI: {doi}")
    print(f"URL: {doi_url}")


def main() -> None:
    args = parse_args()

    token = os.getenv("ZENODO_TOKEN")
    if not token:
        sys.exit("ERROR: ZENODO_TOKEN not set. Add it to .env or set as environment variable.")

    base = ZENODO_SANDBOX if args.sandbox else ZENODO_BASE

    md_path = Path(args.file).expanduser().resolve()
    if not md_path.exists():
        sys.exit(f"ERROR: File not found: {md_path}")

    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = Path(tmp) / (md_path.stem + ".pdf")
        print(f"Converting {md_path.name} → PDF...")
        md_to_pdf(md_path, pdf_path)
        print(f"PDF ready ({pdf_path.stat().st_size // 1024} KB)")

        if args.update:
            update_deposit(args, token, base, pdf_path)
        else:
            new_deposit(args, token, base, pdf_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Publish a Markdown file to Zenodo. Returns a DOI.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --file paper.md --title "My Paper" --description "Abstract"
  %(prog)s --file paper.md --title "My Paper" --dry-run --sandbox
  %(prog)s --file paper.md --title "v2" --update 19586835
  %(prog)s --file paper.md --title "Paper" --related "10.5281/zenodo.123:continues"
  %(prog)s --file paper.md --title "Paper" --creator "Doe, Jane:MIT:0000-0000-0000-0001"
        """,
    )
    p.add_argument("--file", required=True, help="Path to Markdown file")
    p.add_argument("--title", required=True, help="Publication title")
    p.add_argument("--description", default="", help="Abstract / description (HTML supported)")
    p.add_argument("--keywords", default="", help="Comma-separated keywords")
    p.add_argument("--type", default="workingpaper",
                    choices=["workingpaper", "article", "preprint", "report"],
                    help="Publication type (default: workingpaper)")
    p.add_argument("--date", default=None, help="Publication date (YYYY-MM-DD, default: today)")
    p.add_argument("--creator", default=None,
                    help="Creator as 'Last, First:Affiliation:ORCID' (overrides default)")
    p.add_argument("--related", default="",
                    help="Related DOIs as 'doi:relation' pairs, comma-separated. "
                         "Relations: continues, isPartOf, references, isSupplementTo, etc.")
    p.add_argument("--update", default=None, type=int,
                    help="Deposit ID to create a new version of (instead of new deposit)")
    p.add_argument("--funding", default="", help="Comma-separated Zenodo grant IDs")
    p.add_argument("--communities", default="", help="Comma-separated Zenodo community IDs")
    p.add_argument("--dry-run", action="store_true", help="Create deposit but don't publish")
    p.add_argument("--sandbox", action="store_true", help="Use sandbox.zenodo.org for testing")
    return p.parse_args()


if __name__ == "__main__":
    main()
