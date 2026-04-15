# zenodo-publish

Markdown to Zenodo DOI in one command.

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

Nicolas Waern — [WINNIIO AB](https://winniio.io) — [ORCID](https://orcid.org/0000-0001-7970-2707)

Built as part of the [Life Atlas](https://lifeatlas.online) research programme.
