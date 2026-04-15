# Scoring System

## 5 Dimensions, Weighted Composite

| Dimension | Weight | What It Measures |
|-----------|--------|-----------------|
| **STS / Theoretical Rigour** | 25% | Frameworks applied not just cited. ANT translation traced. Boundary objects typed. Counter-arguments engaged. |
| **Engineering / Technical** | 20% | Claims supported. Architecture coherent. Existing vs proposed clear. Competing tools acknowledged. |
| **IS / Management** | 15% | Benefits-driven argument. Maturity models compared. Frameworks falsifiable. Platform economics if applicable. |
| **Domain Relevance** | 20% | Practitioners would use this. Feasible with current tech. Domain references complete. |
| **Quality / APA** | 20% | APA 7th compliant. No orphan refs. Tone academic. Limitations honest. Future research explicit. |

## Formula

```
Composite = (STS × 0.25) + (Engineering × 0.20) + (IS × 0.15) + (Domain × 0.20) + (APA × 0.20)
```

## Rating Bands

| Score | Rating | Action |
|-------|--------|--------|
| 9.5 – 10.0 | **PUBLISH** | Immediate publish |
| 9.0 – 9.5 | **PUBLISH** | Publish, minor polish optional |
| 8.0 – 9.0 | **MINOR REVISION** | Fix specific issues, re-review |
| 7.0 – 8.0 | **MAJOR REVISION** | Full revision cycle |
| 6.0 – 7.0 | **RESTRUCTURE** | Core argument needs rework |
| < 6.0 | **REJECT** | Fundamental issues |

## Per-Dimension Rubric

### 10/10
Every framework analytically deployed with worked example. Counter-arguments engaged. Novel contributions clearly distinguished from existing work. Zero unsupported claims. Zero citation errors.

### 8/10
Frameworks applied (not just cited). Most counter-arguments addressed. Claims supported by literature. Architecture coherent. Minor gaps.

### 6/10
Frameworks correctly cited with some application. Decorative in places. Some unsupported claims. Missing domain references.

### 4/10
Name-dropping. Frameworks cited but never used analytically. Significant gaps. Missing competing tools/approaches.

### 2/10
Misuse of theoretical concepts. Factually incorrect claims. Fundamental formatting failures.

## Review Pipeline

```
Article (Markdown)
    ↓
[5 Reviewers in Parallel]
  ├── STS Reviewer
  ├── Engineering Reviewer
  ├── IS/Management Reviewer
  ├── Domain Expert
  └── Quality/APA Reviewer
    ↓
[Score Computation]
  → Weighted composite
  → Rating band
  → Must-fix list
    ↓
[Decision]
  ≥ threshold → Publish (publish.py)
  < threshold → Revise → Re-review → Iterate
```

Maximum 3 revision cycles before human review.
