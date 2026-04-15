#!/usr/bin/env python3
"""
MAGS Peer Review Pipeline — Multi-agent academic review before publishing.

Runs 5 parallel reviewer personas against an article, scores it on a
5-dimension weighted scale, and produces a consolidated revision checklist.

Can be used standalone (Anthropic API) or inside Claude Code (Agent tool).

Usage (standalone):
    python review.py --file paper.md
    python review.py --file paper.md --threshold 9.0 --model claude-sonnet-4-6

Usage (Claude Code):
    See CLAUDE_CODE_USAGE.md for Agent tool prompts.

Environment:
    ANTHROPIC_API_KEY  — Required for standalone mode.
"""

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

# ---------------------------------------------------------------------------
# Reviewer definitions
# ---------------------------------------------------------------------------

REVIEWERS = {
    "sts": {
        "name": "STS / Theoretical Rigour",
        "weight": 0.25,
        "prompt": """You are a senior reviewer for Social Studies of Science.
Review this paper for theoretical rigour.

Check specifically:
- Is Actor-Network Theory used analytically (Callon's four moments of translation) or decoratively?
- Are boundary objects typed per Star & Griesemer's taxonomy (repository, ideal type, coincident boundary, standardised form)?
- Is absorptive capacity (Cohen & Levinthal) specified with mechanism, not just cited?
- Are counter-arguments engaged (Star 2010, Trompette & Vinck 2009)?
- Is the Granovetter/Hansen weak ties extension grounded or speculative?

Score 1-10. List must-fix issues. Identify genuinely novel contributions.
Be harsh but fair. Under 400 words.

PAPER:
{content}""",
    },

    "engineering": {
        "name": "Engineering / Technical Accuracy",
        "weight": 0.20,
        "prompt": """You are a senior reviewer for IEEE Transactions on Industrial Informatics.
Review this paper for technical accuracy and engineering rigour.

Check specifically:
- Are technical claims supported by references or data?
- Is the proposed architecture/pipeline technically coherent?
- Are performance claims quantified? If not, are they honestly flagged as estimates?
- Is there a clear distinction between what exists and what is proposed?
- Are open research challenges honestly acknowledged?
- Are competing tools/platforms in the domain acknowledged?

Score 1-10. List must-fix issues. Identify technically sound sections.
Be harsh but fair. Under 400 words.

PAPER:
{content}""",
    },

    "is_management": {
        "name": "IS / Management Contribution",
        "weight": 0.15,
        "prompt": """You are a senior reviewer for European Journal of Information Systems.
Review this paper for IS theory and practice contributions.

Check specifically:
- Is the benefits-driven argument (Ward & Daniel 2006) properly developed with a benefits dependency network?
- Is the NUDE/NUDED/NUDEDA framework grounded (Weill & Broadbent 1998)?
- Is there comparison with existing maturity models (CMMI, Gartner, TOGAF)?
- Is the SMILE methodology falsifiable with entry/exit criteria?
- Are IS frameworks applied analytically, not just cited?
- Is there engagement with platform economics literature if applicable?

Score 1-10. List must-fix issues. Identify IS contributions.
Be harsh but fair. Under 400 words.

PAPER:
{content}""",
    },

    "domain": {
        "name": "Domain Expert",
        "weight": 0.20,
        "prompt": """You are a domain expert in the field this paper addresses.
Review for practical relevance and accuracy.

Check specifically:
- Are industry-specific claims accurate and current?
- Would practitioners in this field find this useful or is it academic hand-waving?
- Are the proposed solutions feasible with current technology?
- Are there missing references from the domain that any expert would expect?
- Does the paper acknowledge competing approaches/tools already deployed?
- Are quantitative claims sourced?

Score 1-10. List must-fix issues. Identify practical value.
Be harsh but fair. Under 400 words.

PAPER:
{content}""",
    },

    "quality": {
        "name": "Quality / APA Compliance",
        "weight": 0.20,
        "prompt": """You are a journal production editor checking APA 7th edition compliance.

Check specifically:
- Abstract under 250 words?
- Keywords 8-12, lowercase?
- All references cited in body text (no orphans)?
- All in-text citations have corresponding reference list entries?
- APA formatting of references (author, year, title, journal, DOI)?
- Logical flow between sections?
- Tone consistent (academic, not manifesto or pitch deck)?
- Limitations section present and honest?
- Future research suggestions present?
- No unsupported claims or purple prose?
- No unverified DOIs or suspicious citation metadata?

Score 1-10. List ALL formatting issues. Flag logical gaps.
Under 300 words.

PAPER:
{content}""",
    },
}


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

SCORE_BANDS = {
    (9.5, 10.0): ("PUBLISH", "Immediate publish to Zenodo"),
    (9.0, 9.5):  ("PUBLISH", "Publish — minor polish optional"),
    (8.0, 9.0):  ("MINOR REVISION", "Address specific issues, re-review quality only"),
    (7.0, 8.0):  ("MAJOR REVISION", "Full revision, re-review all dimensions"),
    (6.0, 7.0):  ("RESTRUCTURE", "Core argument needs rework"),
    (0.0, 6.0):  ("REJECT", "Fundamental issues — reconsider approach"),
}


def compute_composite(scores: dict) -> float:
    """Compute weighted composite from dimension scores."""
    total = 0.0
    for key, reviewer in REVIEWERS.items():
        if key in scores:
            total += scores[key] * reviewer["weight"]
    return round(total, 2)


def get_band(score: float) -> tuple:
    """Get the rating band for a composite score."""
    for (lo, hi), (rating, action) in SCORE_BANDS.items():
        if lo <= score < hi:
            return rating, action
    return "PUBLISH", "Publish"


def parse_score(review_text: str) -> float:
    """Extract numeric score from reviewer output."""
    import re
    # Look for patterns like "Score: 8/10", "8.5/10", "Score: 8"
    patterns = [
        r'[Ss]core[:\s]+(\d+\.?\d*)\s*/\s*10',
        r'[Ss]core[:\s]+(\d+\.?\d*)',
        r'(\d+\.?\d*)\s*/\s*10',
    ]
    for pattern in patterns:
        match = re.search(pattern, review_text)
        if match:
            return float(match.group(1))
    return 5.0  # default if parsing fails


# ---------------------------------------------------------------------------
# Standalone mode (Anthropic API)
# ---------------------------------------------------------------------------

def review_standalone(article_path: Path, model: str, threshold: float) -> dict:
    """Run all 5 reviewers via Anthropic API in parallel."""
    if not HAS_ANTHROPIC:
        sys.exit("ERROR: pip install anthropic  (needed for standalone mode)")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("ERROR: ANTHROPIC_API_KEY not set.")

    client = anthropic.Anthropic(api_key=api_key)
    content = article_path.read_text(encoding="utf-8")

    results = {}

    def run_reviewer(key: str, reviewer: dict) -> tuple:
        prompt = reviewer["prompt"].format(content=content)
        response = client.messages.create(
            model=model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text
        score = parse_score(text)
        return key, score, text

    print(f"\nReviewing: {article_path.name}")
    print(f"Model: {model}")
    print(f"Threshold: {threshold}")
    print(f"Running 5 reviewers in parallel...\n")

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {
            pool.submit(run_reviewer, key, rev): key
            for key, rev in REVIEWERS.items()
        }
        for future in as_completed(futures):
            key, score, text = future.result()
            results[key] = {"score": score, "review": text}
            print(f"  {REVIEWERS[key]['name']}: {score}/10")

    # Compute composite
    scores = {k: v["score"] for k, v in results.items()}
    composite = compute_composite(scores)
    rating, action = get_band(composite)

    print(f"\n{'='*50}")
    print(f"COMPOSITE: {composite}")
    print(f"RATING: {rating}")
    print(f"ACTION: {action}")
    print(f"{'='*50}")

    if composite >= threshold:
        print(f"\n✓ PASSES threshold ({threshold}). Ready to publish.")
    else:
        print(f"\n✗ BELOW threshold ({threshold}). Revision needed.")
        print(f"  Gap: {round(threshold - composite, 2)} points")

    return {
        "file": str(article_path),
        "scores": scores,
        "composite": composite,
        "rating": rating,
        "reviews": {k: v["review"] for k, v in results.items()},
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(
        description="Multi-agent peer review for academic papers.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --file paper.md
  %(prog)s --file paper.md --threshold 9.5 --model claude-sonnet-4-6
  %(prog)s --file paper.md --output review.json
        """,
    )
    p.add_argument("--file", required=True, help="Path to Markdown article")
    p.add_argument("--threshold", type=float, default=9.0,
                    help="Minimum composite score to pass (default: 9.0)")
    p.add_argument("--model", default="claude-sonnet-4-6",
                    help="Anthropic model ID (default: claude-sonnet-4-6)")
    p.add_argument("--output", default=None,
                    help="Save full review to JSON file")
    args = p.parse_args()

    article_path = Path(args.file).expanduser().resolve()
    if not article_path.exists():
        sys.exit(f"ERROR: File not found: {article_path}")

    result = review_standalone(article_path, args.model, args.threshold)

    if args.output:
        out = Path(args.output)
        out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"\nFull review saved to: {out}")


if __name__ == "__main__":
    main()
