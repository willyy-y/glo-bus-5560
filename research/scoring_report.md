# GLO-BUS Scoring System — Reverse-Engineered Report

**Date:** 2026-09-24 · **Source bundle:** GLO-BUS Student Decisions & Reports Program v6.22.1 (`/tmp/glo-main.js`)
**Official docs:** `glo-bus.com/help/helpFiles/CDJ-Page{1,2,3,3b}.pdf`
**Status:** read-only analysis. Y7 not entered/submitted.

## 1. The five performance measures

| Measure | Investor-Expectation target (by year) |
|---|---|
| EPS | Y6 $1.25 · Y7 $2.00 · Y8 $3.00 · Y9 $4.25 · Y10 $5.50 · Y11 $7.00 · Y12 $8.50 · Y13 $10.50 · Y14 $12.50 · Y15 $14.50 |
| ROE | Y6 17.5% · Y7 20% · Y8 25% · Y9 30% · Y10 35% · Y11 40%, +2.5 pts/yr → 50% by Y15 |
| Stock price | Y6 $20 · Y7 $35 · Y8 $60 · Y9 $100 · Y10 $150 · Y11 $200 · Y12 $250 · Y13 $300 · Y14 $330 · Y15 $350 |
| Credit rating | Y6–Y7: B+ or higher · Y8–Y10: A− or higher · Y11–Y15: A or higher |
| Image rating | Y6: 70 · Y7–Y8: 72 · Y9–Y10: 75 · Y11–Y12: 77 · Y13–Y15: 80 |

Each measure gets an instructor-assigned point weight; the five sum to 100. This industry's current blend (from live CDJ data) is 50% Investor Expectation / 50% Best-in-Industry. Score weights are instructor-set scenario data, not hard-coded — if your instructor changed them, they appear in the gray-shaded narrative on CDJ pages 2–3.

> **PDF discrepancy:** Page 2's ROE target table lists different values than Page 1's narrative for some years (17% vs 17.5% in Y6, 21% vs 25% in Y8, 30% vs 35% in Y10). Page 1's full schedule is the operative one; Page 2's examples appear older. Credit targets in Page 1's text extraction are garbled for Y8–Y15 ("at least Ain") — Page 3 states: **B+ or higher Y6–Y7, A− or higher Y8–Y10, A or higher Y11–Y15.**

## 2. Investor Expectation (I.E.) scoring — current year

For EPS, ROE, stock price, and image rating — let `W` = measure weight, `T` = target, `P` = performance:

```
if P < T:   score = W × (P / T)
if P == T:  score = W
if P > T:   score = W × (1 + 0.5 × (P/T − 1)), capped at 1.20 × W
```

- Beating a target earns **+0.5% of the weight per +1% above target**, capped at **+20%** (requires performance **≥140% of target**).
- Scores are **rounded to nearest whole number**.
- **Negative EPS or negative ROE = zero points** for that measure.
- If beg. equity + end. equity ≤ 0, ROE is treated as −10000% (i.e. zero points).
- Max possible annual I.E. score = **120**.

Credit rating I.E. scores are a fixed grade×year table, not a ratio. For a 20-point credit weight:

| Grade | Y6–Y7 | Y8–Y10 | Y11–Y15 |
|---|---|---|---|
| A+ | 24 | 24 | 24 |
| A | 23 | 22 | 20 |
| A− | 22 | 20 | 18 |
| B+ | 20 | 18 | 16 |
| B | 16 | 15 | 14 |
| B− | 12 | 12 | 11 |
| C+ | 8 | 8 | 8 |
| C | 4 | 4 | 4 |
| C− | 0 | 0 | 0 |

(Scale proportionally if weight ≠ 20: score = table_value × weight/20.)

## 3. Best-in-Industry (B-I-I) scoring — current year

For EPS, ROE, stock price, image: let `L` = industry leader result. Leader's score = `W` if `L ≥ T`, else `W × L/T`. Each other company = **leader's score × (P/L)**. So effectively score ≈ `W × P / max(L, T)`. Negative EPS/ROE = 0. Max total B-I-I = 100.

Credit B-I-I is grade-based, anchored to A+ (not to the best actual grade). For a 20-point weight:

**A+ 20 · A 19 · A− 18 · B+ 16 · B 14 · B− 11 · C+ 8 · C 5 · C− 1**

(The bundle's own current-year B-I-I scoreboard renders each of the five measures this way; rounding to whole numbers.)

## 4. Weighted average and overall scores

- **Annual weighted average score** = (I.E. blend %) × (annual I.E. score) + (B-I-I blend %) × (annual B-I-I score). Instructor sets the blend; usually 50/50.
- **Game-to-date (GTD) I.E. score** = 5 component scores recomputed from game-to-date aggregates — it is **not** the average of annual I.E. scores.
- **GTD B-I-I score** = same, from GTD aggregates.
- **GTD weighted average** = blend applied to GTD components.
- **Overall GTD score** = GTD weighted average + cumulative bonus points (Bull's Eye + Leap Frog).

### GTD aggregates (exact formulas)

| Measure | GTD I.E. computation | GTD B-I-I computation |
|---|---|---|
| EPS | Weighted-avg EPS = **Σ(all years' net profit) / Σ(all years' ending shares outstanding)**; compared to **arithmetic avg of annual EPS targets** for years completed | Leader's weighted-avg EPS vs each company's; leader scaled by target if leader < avg target |
| ROE | Weighted-avg ROE = **Σ(all years' net profits) / Σ(each year's avg beginning/ending equity)**; vs arithmetic avg of annual ROE targets | Same with weighted-avg ROE; leader scaled by 15% if leader's avg ROE < 15% |
| Stock price | **Most recent year only** (no averaging) | Most recent year only |
| Credit | **Most recent year only** — current-year and GTD credit scores are identical | Most recent year only (A+ scale) |
| Image | **Average of most recent 3 years'** image ratings vs **average of the last 3 years' targets** (Page 1 also says "vs a 70 image rating target" in one place — ambiguous; the 3-year-avg-of-targets wording in Page 3 is more precise) | 3-year avg vs leader's 3-year avg; leader scaled by 70 target if below |

## 5. Bull's Eye Award (page 3b)

1 bonus point added to GTD overall score per qualifying year. Uses the **projected** revenue/EPS/image from the **Projected Company Performance box of the last saved decision entries** used to process results. All three conditions required:

1. Actual total revenue within **±5%** of projected
2. Actual EPS within **±$0.10 OR ±5%** of projected (either suffices)
3. Actual image rating within **±4 points** of projected

- Revenue/EPS percent variance = (actual − forecast) / **actual** × 100 (denominator is actual, not forecast).
- Standard rounding applies to the ±5% calculations; image rating has no decimals.
- Unlimited — one per year; practice-round awards are erased.
- Missing decisions → ineligible that year.

## 6. Leap Frog Award

- 1 bonus point to the company whose **current-year Weighted Average Score improved the most in raw points** over the prior year.
- Starts Year 7 (needs two years of data).
- Ties: **every** tied company gets the point. If **no** company improved, no award.
- Cumulative bonuses shown on CDJ page 1 GTD scoreboard.

## 7. Exact client-side formulas: EPS, ROE, credit, image

### EPS and ROE
```
EPS  = round(net profit / shares outstanding at year end, 2)
ROE  = round(net profit / avg(beginning equity, ending equity), 3)
```

### Credit rating (fully client-side, deterministic)
Inputs (each rounded before lookup):
1. **Debt ratio** = total debt / (total debt + total equity), round 3
2. **Interest coverage** = operating profit / interest expense, round 2 (if interest expense ≤ 0, forced to 1000)
3. **Default-risk ratio** = the balance-sheet ratio the bundle calls `credit_currentratio` (computed as AB1819/AB1835), round 2

Each is run through an approximate-match (Excel VLOOKUP) table; points are summed; grade = VLOOKUP(max(1,total), rating table):

- Total ≥ 345 → A+ · ≥225 → A · ≥165 → A− · ≥125 → B+ · ≥110 → B · ≥95 → B− · ≥80 → C+ · ≥65 → C · ≥1 → C−

Credit rating also feeds loan pricing: last year's grade adds to the base loan rate —
**C− +6.0% · C +4.5% · C+ +3.0% · B− +2.5% · B +2.0% · B+ +1.5% · A− +1.0% · A +0.5% · A+ +0%**

Exact tables (full data in `scoring_tables.json`):

- **Debt ratio → points:** 0→100, 0.05→97, 0.10→94, 0.15→90, 0.20→85, 0.24→81, 0.28→77, 0.32→72, 0.36→66, 0.40→60, 0.43→54, 0.46→50, 0.49→46, 0.52→42, 0.55→38, 0.58→34, 0.61→29, 0.64→23, 0.67→16, 0.70→8, 0.73→0, 0.76→−9, 0.79→−17, 0.82→−24, 0.85→−30, 0.88→−35, 0.91→−39
- **Interest coverage → points:** starts −100000→−70 … 2→5, 3→42, 5→64, 10→87, 50→100
- **Default-risk ratio → points:** 0→−47, 0.5→−5, 1→31, 2→91, 4→165, 9→220, 14→240

Key takeaway: debt ratio ≥ ~0.73 contributes nothing or negative points; coverage ≥ ~5 adds 60+; default-risk ratio ≥ ~4 adds 165 (enough for A− on that input alone).

### Image rating (fully client-side, deterministic)
```
image = min(100, round(
    (camera share pts ×4 regions + drone share pts ×4 regions
     + camera P/Q pts + drone P/Q pts) × image_year_multiplier
    + corporate_citizenship_points, 0))
```
- **Share points:** for each product × each of 4 regions = VLOOKUP(own regional share / baseline share, image_share) × (4 / #regions selling that product). For Y<9 the baseline comes from demand cells; from Y9 it's derived from industry units × company count (with an `image_special` adjustment).
- **P/Q points:** VLOOKUP(own P/Q on 0–100 scale, image_pq) — doubled (×2) if it's the only product sold, ×1 each if both. image_pq rises ~0.75 per +1 P/Q until P/Q≈60, then flattens (max 20 at P/Q=100).
- **Year multiplier (deflator):** Y6 1.000 · Y7 .985 · Y8 .970 · Y9 .955 · Y10 .940 · Y11 .925 · Y12 .910 · Y13 .895 · Y14 .880 · Y15 .865 — targets rise while the multiplier shrinks, so you must grow share/PQ/citizenship faster each year.
- **Corporate citizenship** = min(20, round((charitable + green + energy + cafeteria + safety + conduct points) × citizen_year_mult)) with citizen_year_mult = Y6 1.10 · Y7 1.08 · Y8 1.06 · Y9 1.04 · Y10 1.02 · Y11 1.00 · Y12 .99 · Y13 .98 · Y14 .97 · Y15 .96:
  - charitable donations: $0/5k/10k/15k/20k/25k/30k/35k/40k/45k/50k → 0/.5/1/1.75/2.5/3.25/4/4.75/5.5/6.25/7
  - green initiatives: 0–5 → 0/1.2/2.5/3.5/4.5/5.5
  - energy efficiency: $0/500/…/5000 → 0/.4/1/1.6/2.2/2.8/3.4/4/4.6/5.2/5.8
  - cafeteria: 0–5 → 0/1.5/1.8/2.1/2.4/2.7
  - safety: 0–5 → 0/1.7/1.95/2.2/2.45/2.7
  - code of conduct: 0–5 → 0/.25/.5/.75/1/1.25

## 8. Uncertain / server-side items

1. **Stock price formula — server-side.** The bundle never computes next year's stock price; it arrives from the server (AA1895). Official docs describe it only as a function of revenue growth, EPS growth, average ROE, credit rating, dividend growth, and management's consistency in hitting the five targets. **No weights published.** Max share repurchase in a year is capped at 25% of shares × `share_repurchases` table, and only when stock ≥ $12.
2. **Citizenship input decay** — AB1615–AB1644 accumulate citizenship spending with 5-year decay; exact per-component decay semantics not fully traced (only the lookup tables above are confirmed).
3. **Credit third input** — the code's `credit_currentratio` is named like a current ratio but official docs call the third determinant a default-risk ratio; the formula is client-side exact regardless of the label.
4. **GTD image target wording** — Page 1 says "image rating target of 70" while Page 3 says "average of the annual investorexpected image ratings"; use the latter.
5. **Instructor weights** — points per measure and the I.E./B-I-I blend live in scenario data on the CDJ; verify on pages 2–3 gray narrative for Industry 18 before simulating.

## 9. Strategic implications for maximizing shareholder value

- The 20%-bonus cap means **EPS/ROE/stock/image beyond 140% of target earn zero additional I.E. points** — redirect surplus into B-I-I-competitive spending or credit.
- **Credit is the cheapest I.E. insurance**: A+ scores max I.E. every year regardless of target, and the bundle's credit tables show A−/A are reachable with debt ratio ≈ 0.4–0.5, coverage ≥ 5, default-risk ratio ≥ 4. Dropping from B+ to C+ costs 8–12 I.E. points.
- **Bull's Eye ≈ 1 free point per year** if the Competitive Assumptions inputs are kept honest — worth ~0.8% of the GTD score annually.
- **Leap Frog** rewards the biggest year-over-year weighted-score gain — front-load investments early when gains vs. prior year are largest.

Tables machine-readable: `scoring_tables.json` (same folder).
