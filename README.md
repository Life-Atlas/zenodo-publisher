# zenodo-publish

Markdown to Zenodo DOI in one command — with AI-powered multi-agent peer review.

```bash
python publish.py --file paper.md --title "My Paper" --description "Abstract here"
# → DOI: 10.5281/zenodo.XXXXXXX
```

## What it does

1. Converts your Markdown file to a styled PDF
2. Creates a deposit on Zenodo via the REST API
3. Uploads the PDF
4. Sets metadata (title, abstract, keywords, license, related works)
5. Publishes and returns the DOI

Your paper is immediately citable, indexed by DataCite, and (if linked) auto-harvested by ORCID.

## Before you publish: author identity and record hygiene

Read this section before every deposit. It exists because SMILE v6.5.0 went out on 3 September 2026 with the wrong ORCID, five months after the right one had been established.

**The author's ORCID is `0009-0001-4011-8201`.** It is the maintained record (profile built April 2026: biography, 11 employments, 6 works). `0000-0001-7970-2707` is an empty account from 2013 that resolves to the same name and must never be used. `publish.py`'s default creator carries the right one; if you pass `--creator`, pass the right one. As of 5 September 2026 every record in the account (150, all versions) carries `0009-0001-4011-8201`; 51 of them were corrected that day by metadata edit.

**Metadata on a published record can be corrected without a new version.** The sequence against `https://zenodo.org/api/deposit/depositions/<id>` is `POST actions/edit` → `GET` the deposition → change `metadata` → `PUT` `{"metadata": …}` with the `doi` and `prereserve_doi` keys removed → `POST actions/publish`. It works on superseded versions too. Use it for an ORCID, a typo, a keyword; use a new version only when a file changes.

**A new version with binary files (DOCX + PDF) does not go through `publish.py`,** which converts Markdown and uploads one PDF. The REST sequence is `POST <id>/actions/newversion` → `GET` the `latest_draft` → delete the inherited files → `PUT` each file to the draft's `bucket` → `PUT` metadata (`version`, `publication_date`, `creators`, `description`; never a `doi`) → `POST actions/publish` → `GET /api/records/<new id>` and check `version` and `creators[0].orcid` before calling it done. A working script is kept with the SMILE build kit at `OneDrive - Winniio AB\WINNIIO 2026\SMILE\01-Current\v6.5.0-build\publish_v650.py` (`--src <record> --version <x.y.z>`).

**SMILE lives under concept DOI `10.5281/zenodo.20175405`.** Cite the concept DOI for "latest"; cite a version record only when the sentence is about that version. Current: v6.5.1, record 22369538 (5 September 2026). The winniio-site repo checks its own text against Zenodo's latest version (`scripts/check-smile-version.mjs`) after every SMILE publish.

## Setup

```bash
git clone https://github.com/Life-Atlas/zenodo-publisher.git
cd zenodo-publisher
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Zenodo token
```

Get your token at [zenodo.org/account/settings/applications](https://zenodo.org/account/settings/applications). Scopes needed: `deposit:write` + `deposit:actions`.

## Usage

### New publication

```bash
python publish.py \
  --file paper.md \
  --title "The Reality Construct" \
  --description "Position paper on digital twins as boundary-spanning objects." \
  --keywords "digital twins,boundary objects,actor-network theory"
```

### Dry run (creates draft, doesn't publish)

```bash
python publish.py --file paper.md --title "Test" --dry-run
```

### Update an existing deposit (new version)

```bash
python publish.py \
  --file paper-v2.md \
  --title "The Reality Construct (v2)" \
  --update 19586835
```

The original DOI continues to resolve. The new version gets its own DOI. Both are linked.

### Link related works

```bash
python publish.py \
  --file paper.md \
  --title "Domain Paper" \
  --related "10.5281/zenodo.19587944:continues,10.5281/zenodo.19586851:references"
```

Relations: `continues`, `isPartOf`, `references`, `isSupplementTo`, `isCitedBy`, `isNewVersionOf`, etc. ([full list](https://developers.zenodo.org/#representation)).

### Custom creator

```bash
python publish.py \
  --file paper.md \
  --title "Paper" \
  --creator "Doe, Jane:MIT:0000-0000-0000-0001"
```

Format: `Last, First:Affiliation:ORCID` (affiliation and ORCID optional).

### Sandbox (testing)

```bash
python publish.py --file paper.md --title "Test" --sandbox
```

Uses `sandbox.zenodo.org` — separate token needed from [sandbox.zenodo.org/account/settings/applications](https://sandbox.zenodo.org/account/settings/applications).

## All options

| Flag | Description | Default |
|------|-------------|---------|
| `--file` | Path to Markdown file | *required* |
| `--title` | Publication title | *required* |
| `--description` | Abstract (HTML supported) | title |
| `--keywords` | Comma-separated keywords | none |
| `--type` | `workingpaper`, `article`, `preprint`, `report` | `workingpaper` |
| `--date` | Publication date (YYYY-MM-DD) | today |
| `--creator` | `Last, First:Affiliation:ORCID` | see `.env` |
| `--related` | DOI:relation pairs, comma-separated | none |
| `--update` | Deposit ID to create new version of | none (new) |
| `--funding` | Zenodo grant IDs, comma-separated | none |
| `--communities` | Zenodo community IDs, comma-separated | none |
| `--dry-run` | Create draft but don't publish | false |
| `--sandbox` | Use sandbox.zenodo.org | false |

## PDF quality

The tool tries two PDF backends:

1. **WeasyPrint** (recommended) — styled HTML-to-PDF with proper typography. Needs system libraries (`libpango`, `libcairo`). Native on Linux/Mac, requires [GTK for Windows](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation).

2. **ReportLab** (fallback) — pure Python, works everywhere, basic formatting. Install with `pip install reportlab`.

## AI Peer Review

Before publishing, run your article through 5 parallel AI reviewers:

```bash
# Standalone (requires ANTHROPIC_API_KEY)
python review.py --file paper.md --threshold 9.0

# Output:
#   STS / Theoretical Rigour: 8.5/10
#   Engineering / Technical:  8.0/10
#   IS / Management:          9.0/10
#   Domain Expert:            8.5/10
#   Quality / APA:            9.0/10
#   
#   COMPOSITE: 8.6
#   RATING: MINOR REVISION
#   ✗ BELOW threshold (9.0). Revision needed. Gap: 0.4 points
```

Five reviewer personas score across weighted dimensions:

| Dimension | Weight | What It Measures |
|-----------|--------|-----------------|
| STS / Theoretical Rigour | 25% | Frameworks applied, not just cited |
| Engineering / Technical | 20% | Claims supported, architecture coherent |
| IS / Management | 15% | Benefits-driven, falsifiable methodology |
| Domain Relevance | 20% | Practitioners would use this |
| Quality / APA | 20% | Formatting, references, tone |

The review → fix → re-review loop typically improves articles from 5-6 (first draft) to 8.5+ within 3-4 rounds.

See [SCORING.md](SCORING.md) for the full rubric and [CLAUDE_CODE_USAGE.md](CLAUDE_CODE_USAGE.md) for Claude Code integration.

```bash
# Save full review as JSON
python review.py --file paper.md --output review.json

# Use a different model
python review.py --file paper.md --model claude-opus-4-6
```

## GitHub Actions

To auto-publish on release:

```yaml
# .github/workflows/publish.yml
name: Publish to Zenodo
on:
  release:
    types: [published]
jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - run: |
          python publish.py \
            --file ${{ github.event.release.body }} \
            --title "${{ github.event.release.name }}"
        env:
          ZENODO_TOKEN: ${{ secrets.ZENODO_TOKEN }}
```

## License

MIT

## Author

Nicolas Waern — [WINNIIO AB](https://winniio.io) — [ORCID](https://orcid.org/0009-0001-4011-8201)

Built as part of the [Life Atlas](https://lifeatlas.online) research programme.
