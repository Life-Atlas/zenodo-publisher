# Using the Review Pipeline in Claude Code

The review pipeline can run inside Claude Code using the Agent tool for parallel reviewer execution.

## Quick Start

Ask Claude Code:

```
Review my article at publications/drafts/000-reality-construct/article.md 
using the 5-reviewer pipeline. Score all dimensions and tell me what prevents 9.5.
```

## Manual Agent Calls

For maximum control, spawn 5 reviewer agents in a single message:

```
Agent({
  description: "STS review",
  subagent_type: "code-reviewer",
  prompt: "You are a senior STS reviewer. Read [path]. Score 1-10 on theoretical rigour...",
  run_in_background: true
})

Agent({
  description: "Engineering review", 
  subagent_type: "code-reviewer",
  prompt: "You are a senior IEEE reviewer. Read [path]. Score 1-10 on technical accuracy...",
  run_in_background: true
})

// ... 3 more reviewers
```

All 5 run in parallel. Collect results, compute weighted composite, identify fixes.

## Review → Fix → Re-Review Loop

```
Round 1: Draft article → 5 reviewers → Score (typically 5-7)
         ↓
Round 2: Fix must-fix issues → 5 reviewers → Score (typically 7-8)
         ↓
Round 3: Fix remaining issues → 5 reviewers → Score (typically 8-8.5)
         ↓
Round 4+: Precision fixes → targeted reviewers → Score (8.5-9+)
```

Each round addresses the specific issues flagged by reviewers. Engineering papers typically cap at ~8.5 without empirical data. Conceptual/theoretical papers can reach 9.0+ through iterative refinement.

## Batch Review

Review multiple articles in one agent call:

```
Agent({
  description: "Batch review 4 articles",
  prompt: "ALL FIVE reviewers. Read each article, score each. Under 200 words per article.
    1. path/to/article-a.md
    2. path/to/article-b.md  
    3. path/to/article-c.md
    4. path/to/article-d.md"
})
```

## Full Pipeline: Review → Publish

```python
# 1. Review
python review.py --file paper.md --threshold 9.0 --output review.json

# 2. If passes threshold, publish
python publish.py --file paper.md --title "Paper Title" --description "Abstract"

# 3. If fails, fix issues and re-review
python review.py --file paper-v2.md --threshold 9.0
```

## Observed Score Trajectories

From the April 15, 2026 session (11 articles, 50+ review rounds):

| Round | Typical Score | What Improves |
|-------|--------------|---------------|
| R1 (first draft) | 5.0 – 7.0 | Baseline |
| R2 (first revision) | 7.0 – 8.0 | Missing refs, citation errors, anonymisation |
| R3 (second revision) | 8.0 – 8.5 | Theoretical depth, domain grounding, APA compliance |
| R4+ (precision) | 8.5 – 9.0 | Worked examples, counter-arguments, ontological honesty |

The structural ceiling for position papers without empirical data is approximately 8.5–9.0. Papers with even minimal empirical grounding (one benchmark, one deployment metric) can push past 9.0.
