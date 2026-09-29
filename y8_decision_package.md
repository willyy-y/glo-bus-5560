# GLO-BUS Year 8 Decision Package — Company E ("Evading Taxes LLC"), Industry 18

**Status:** OFFLINE MODELING ONLY — approved 2026-09-29. Nothing has been entered, saved, or submitted in the live game. Do not touch GLO-BUS until the user approves this package.

**Objective:** Defend industry-leading profit (EPS/ROE/stock/credit at or above caps) while recovering image from 75 toward 80+ to answer Insider Trading Inc. and chase the global Overall Game-To-Date leaderboard (top-board cutoff ~108; our Y6 annual was 107).

---

## 1. What the Y7 Competitive Intelligence Report taught us

Y7 was **not** a price war. Insider Trading Inc. priced **at or above** us (cameras $300–310, drones $1,400–1,800, P/Q 5.1/4.6) and won on **premium positioning + extreme marketing**: 16 promo weeks at 22–23% in NA/EA/AP, up to $8M/region camera ads, $4.5M website + $8M search for drones in NA. Result: Insider $683.8M revenue / $63.9M profit / image **86** vs. our $489.0M / $77.3M / image **75**. We kept the profit crown; they took image and volume.

Our Y7 actuals vs. the saved A2 projection: revenue missed by −7.8%, profit by −14.4%. **All game/engine projections are treated as ceilings in this package.**

## 2. Calibration (grounded in Y7 CIR actuals)

`cases/y7_cir_actuals.json` now holds all 9 firms' Y7 actuals (repaired and validated: 9-firm averages reproduce the Y8 assumption cells exactly — cameras 255/263/250/247, drones 1572/1596/1633/1518).

**Y7 backtest** — our A2 decisions run against TRUE Y7 rival averages:

| | Model | Actual | Bias |
|---|---|---|---|
| Camera units | 1,122.6k | 1,224.7k | −8.3% |
| Drone units | 153.5k | 138.5k | +10.8% |
| Revenue | $500.7M | $489.0M | +2.4% |
| Net profit | $89.3M | $77.3M | +15.5% |

Findings applied to every Y8 projection below ("realistic" case):
- Camera units ×1.09, drone units ×0.90 (product-specific, from backtest)
- AP/LA revenue ÷1.049 (known exchange-rate overstatement in the model), then ×0.99 residual
- Box unit costs ($177 camera / $902 drone) validated **exact** vs. Y7 actuals — no adjustment
- Box fixed block validated **exact** vs. Y7 actuals ($36.0M) — Y8 fixed ($29.2M) calibrated to the game's $107.8M carried-forward projection, trusted
- Marketing deltas expensed vs. the A2 calibration level ($40.68M)
- The box's promo demand response is ~0 (does not reproduce the live-measured +0.65%/week); we add the empirical response: camera units ×(1 + 0.0065 × weeks × disc-factor)
- "Box" figures are shown alongside as the optimistic ceiling

**Image model** (reverse-engineered, reproduced Y7's 75 exactly): image = (share pts + P/Q pts) × 0.97 + citizenship pts (cap 20). Carrying A2 into Y8 **loses** image (73 projected) via growth dilution + the lower 0.97 multiplier — standing still is not an option.

**The CSR lever (validated in the client tables):** citizenship = charitable contributions + energy efficiency spend, capped at $50k → 7 pts and $5k → 5.8 pts. Our current ~4 pts implies ~$25.5k spend. Raising to **$50k charitable + $5k energy (≈$55k/yr, +$30k marginal)** yields **+10 to +14 image points** — the tables cap inputs, so this holds under any decay semantics. Cost: ~$30k/yr. This is the cheapest image lever in the game by ~1000×.

---

## 3. Candidate packages

Common to all: camera P/Q 4.7, drone P/Q 4.1 (no design change), warranty 180 days, 2 models each. Production must be raised (see §6).

### Package A — RECOMMENDED: profit-optimal operating + CSR max

| Region | Cam price | Retailer support | Ads | Web | Promo | Drn price | Search | Web | Recruit | 3P disc |
|---|---|---|---|---|---|---|---|---|---|---|
| NA | $265 | $2,599k | $5,988k | $2,000k | 6 wks @ 18% | $1,490 | $1,700k | $1,812k | $1,831k | 5% |
| EA | $283 | $2,059k | $4,150k | $1,700k | 6 wks @ 22% | $1,510 | $2,000k | $1,665k | $1,572k | 5% |
| AP | $227 | $1,869k | $2,500k | $1,050k | none | $1,465 | $1,300k | $985k | $1,173k | 5% |
| LA | $224 | $1,297k | $1,800k | $800k | none | $1,475 | $1,000k | $548k | $829k | 5% |

Plus: Corporate Citizenship — charitable contributions **$50,000**, energy efficiency **$5,000** (verify field names on the Citizenship page at entry).

Logic: hold AP/LA price leadership ($227/$224 kept our best shares: 16.6%/15.8% projected), answer Insider where it hurt us (NA/EA promos 6 wks @ 18–22% + matched drone search/web), trim diminishing-returns support spend, keep drone prices firm (margin $588/unit).

### Package B — fallback: same operating, NO CSR change

Identical decisions to A except citizenship left as-is. Use only if the Citizenship page mechanics differ from the tables at entry time.

### Package C — image-max (frontier extreme, NOT recommended)

Aggressive share push (camera −$8, drone −$100, marketing $66.5M) + CSR. Demonstrates the cost of buying image through operations.

---

## 4. Projections

**Realistic case** (bias-adjusted). Box ceiling in parentheses.

| Package | Revenue | Net profit | EPS | ROE* | Image | Credit | Stock† |
|---|---|---|---|---|---|---|---|
| A (rec.) | $604M ($635M) | **$100.9M** ($126.5M) | **$5.09** ($6.39) | ~39% | **88** (90) | A | $140–165 |
| B (no CSR) | $577M ($608M) | $95.4M ($120.0M) | $4.82 ($6.06) | ~37% | 76 (78) | A | $135–160 |
| C (image-max) | $687M | $79.3M ($111.4M) | $4.00 | ~31% | 96 | A | $115–140 |
| Investor target | — | — | $3.00 | 25% | 72 | A− | $60 |

\* ROE assumes equity ≈ $261M avg (Y7 $210.6M + retained Y8 profit, no dividends/buybacks).
† Stock formula is unpublished/server-side; range is a heuristic from Y7's P/E (~31.5×).

**Downside / stress case** (Insider repeats Y7 aggression, +15% volume): A → net **$100.3M**, image **87**; B → $94.9M / 75. The package is robust — Insider's growth barely dents us because our margin is price-led, not share-led.

**Annual scoring (Y8):**

| Package | I.E. (exact, /120) | B-I-I (est., /100) | Weighted overall (est.) |
|---|---|---|---|
| A | **116** (capped: EPS 24, ROE 24, stock 24, credit 22, image 22) | 95–98 (likely leads EPS, image, stock) | **~106–107** |
| B | 115 | 93–96 | ~104–106 |
| C | 116 | 96–99 | ~106–108 |

I.E. detail: every ratio measure caps at 1.2× weight; credit A = 22/24 (A+ would give 24 — see §6); image 88 → 22/24 (24 needs image ≥101, impossible). B-I-I depends on unknown rival Y8 outcomes; ranges assume we lead EPS/image.

**GTD image** (3-yr rolling: 71, 75, 88) → **78.0**, up from 73.

---

## 5. The image-point price list (marginal tradeoffs)

| Lever | Image gain | Profit cost | $ per image point |
|---|---|---|---|
| **CSR max ($50k + $5k)** | **+10 to +14** | **~$0.03M** | **~$0.003M** |
| Share push via promos (NA/EA 6 wks) | +2 | −$0.6M net | ~$0.3M |
| Aggressive operations (Pkg C vs A) | +8 | −$21.6M | ~$2.7M |
| P/Q 4.7/4.1 → 5.1/4.6 | +2 | −$25.3M | ~$12.6M |

CSR dominates everything. P/Q upgrades are the worst image buy in the game — rejected.

---

## 6. Entry checklist (when the user approves)

1. **Marketing/price/promo** — enter Package A tables above (drone "ad" = search engine advertising).
2. **Corporate Citizenship** — charitable contributions $50,000; energy efficiency $5,000. If the page's fields or caps differ, stop and re-model (fallback: Package B).
3. **Production** — raise to **1,560k cameras / 195k drones** (current cap 1,355k cameras would stock out under CSR-lifted demand).
4. **Design** — no changes (P/Q stays 4.7/4.1).
5. **Finance (optional +2 I.E. points)** — A+ credit requires lower debt/higher coverage; check the Finance page for cheap debt paydown. Not modeled; do not force it.
6. **Verify before save** — projected box values should read ≈ $635M revenue / ≈ $126.5M profit / image ≈ 90; if materially different, stop.

## 7. Risks and caveats

- **CSR decay semantics** are the one unvalidated link: tables are literal and Y7 image reproduced exactly, but if the Citizenship page behaves differently, image lands at 76–78 (Package B) instead of 88. $30k at risk, not the year.
- **Rival price war** (not the base case — Y7 wasn't one): our camera margin ($88/unit at $265) and drone margin ($588/unit) absorb cuts; re-model if CIR shows aggression.
- **Box optimism**: realistic ≈ 80–85% of box profit. The $100.9M already includes this haircut; $126.5M is the ceiling.
- **Production unit-cost curve** not modeled; producing 1,560k vs 1,355k may shift $177/unit slightly.
- **Stock** is a heuristic range, not a forecast. **B-I-I** is estimated; only I.E. (116) is exact.
- P/Q upgrade evidence ($17.7M/$18.4M) is Y7-empirical; not needed for any package.

---

## 8. Recommendation

**Enter Package A.** It defends the profit crown (realistic $100.9M net, $5.09 EPS — both ~30% above Y7 actuals and far above investor targets), answers Insider with targeted NA/EA promos and matched drone marketing, and buys image from 75 to **88** for $30k/yr via the CSR lever instead of $20M+ via operations. Downside case barely moves ($100.3M / 87). The only decision the model says *not* to make: P/Q upgrades — $25M for 2 image points.

*Engine artifacts: `cases/y7_cir_actuals.json` (repaired/validated), `cases/y8_calibrated.json`, `y8_work.py` (backtest + calibration), `y8_opt.py` (optimizer), `y8_final.py`, `y8_frontier.py`. Pushed to github.com/willyy-y/glo-bus-5560.*
