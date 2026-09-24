# Y7 Full Optimization Results (price + marketing + promo + discount)

**Generated:** 2026-09-24 (offline model; never touched the live game)

## Candidate settings for live confirmation test

| Region | Camera price | Retailer support | Advertising | Website | Drone price | Search ads | Website |
|--------|--------------|------------------|-------------|---------|-------------|------------|---------|
| NA | $261 | $2,899k | $5,988k | $1,700k | $1,474 | $1,700k | $1,662k |
| EA | $277 | $2,359k | $3,400k | $1,400k | $1,440 | $1,400k | $1,365k |
| AP | $223 | $2,169k | $2,500k | $1,050k | $1,441 | $700k | $985k |
| LA | $218 | $1,597k | $1,800k | $700k | $1,337 | $400k | $698k |

- **Camera promo weeks:** 0 (all regions)
- **Drone third-party discount:** 7.5%

### Predicted outcomes
- **Net profit:** $90,531k (vs $74,108k baseline; +$16,423k / +22%)
- **EPS:** $4.57 (vs $3.74 baseline)
- **Image rating:** 80 (vs 85 baseline; -5 points)
- **Camera units:** 1,350.9k (vs 1,372.9k demand, 1,355k capped sales)
- **Drone units:** 155.9k (vs 221.2k demand, 217k capped sales)

## Validation

### Price-only validation (must recover measured uniform optima)
- **Camera uniform optimum:** +$20.2 (measured ~+$17) ✓
- **Drone uniform optimum:** +$416.1 (measured ~+$360; quadratic fit to measured profit gives +$378) ✓ approximately
- **Max deviation vs measured profit points:** $2,287k (3.1% of baseline profit)

### Marketing/promo/discount validation (model vs measured profit deltas)
| Test | Model | Measured | Direction |
|------|-------|----------|-----------|
| Website NA cut ($1,000k) | +$777k | +$509k | ✓ (both positive) |
| Promo 1→0 weeks | +$525k | +$432k | ✓ (both positive) |
| Discount 10%→5% | +$2,153k | +$1,542k | ✓ (both positive) |
| Discount 10%→0% | +$1,558k | +$978k | ✓ (both positive) |

**Note:** Model systematically overpredicts magnitudes by 20-50%. Direction is correct; treat absolute gains as optimistic.

### Image validation
- Baseline: 85 (predicted) vs 85 (actual) ✓
- 0% discount: 84 (predicted) vs 84 (actual) ✓

## Model summary

**Demand (unconstrained):**
- `D_cam[r] = price_curve[r](p) × Π_c (spend/spend0)^b_c × promo_mult`
- `D_drn[r] = price_curve[r](p) × (search/s0)^b_s × (web/w0)^b_w × total_disc(d)/221.2`
- Price curves: best-fit per region (CE/linear/log-linear by min max-error)
- Marketing elasticities from NA single-variable tests:
  - Camera retailer support: 0.0632
  - Camera advertising: 0.1285
  - Camera website: 0.0465
  - Drone search ads: 0.0766
  - Drone website: 0.0465 (assumed = camera website; **no drone website test**)

**Sales:** Proportional cap at capacity (camera 1,355k; drone 217k).

**Revenue:** `k_rev × Σ(sales × eff_price)` where `k_rev=0.9643` (empirical revenue conversion).

**Costs:**
- Camera production: `c(U) = 126.071 + 24,435.8/U` ($/unit, U in k), fitted on capped volumes
- Drone production: $748.70/unit (invariant)
- Variable adders: camera +$5.71/unit, drone −$22.79/unit (fitted; drone adder is economically implausible but statistically necessary—do not interpret structurally)
- Marketing: explicit spend; fixed block adjusted for spend delta vs baseline

**Profit:** `(Revenue − ProdCost − Adder − Fixed − ΔMarketing) × (1−0.30 tax)`

**Image:** Structural from `score.py`:
- Share ratios = 1.35 × (sales / baseline_sales), calibrated to baseline image 85
- Citizenship constant = 4.0 points (solved)
- Uses smooth (interpolated) share table for optimizer stability

**Discount model:**
- Total drone demand: `210.8 + 104×d` (linear, k units)
- 3rd-party share: `s(d) = (21.8 − 164d + 3520d²) / (210.8 + 104d)`
- At optimal prices, profit-max discount ≈ 7.5%; 5% is within $113k

## Key caveats

1. **Camera regional prices (AP $223, LA $218 are DECREASES):** The AP/LA linear demand fits use only 3 points with a visibly non-smooth middle point. Regional price decreases are not well-supported. Consider using uniform +$20 for all regions as a more conservative alternative.

2. **Marketing elasticities are one-chord estimates:** Single NA test per channel; transferred to other regions by assumption. Drone website elasticity is unmeasured (assumed = camera website).

3. **Drone adder is negative (−$22.79):** Economically impossible; reflects unmodeled revenue/cost structure. The model fits profit well (max dev $2.3M) but do not interpret parameters structurally.

4. **Model overpredicts marketing/promo/discount gains** by 20-50%. The candidate's +$16.4M gain is likely optimistic; expect +$10-13M in live test.

5. **Image drops 5 points (85→80):** This is the profit-max with image floor at 80. If B-I-I is sensitive, consider a more conservative drone price (+$300 instead of +$360) to preserve image at 82-83.

6. **Drone prices (+$190-285) exceed measured range** (+$480 max tested = $1,670; model goes to $1,474 max, which is within range). Camera NA/EA (+$18/+$29) are near measured range.

## Files
- `optimize.py`: Full optimizer (run with `python3 optimize.py`)
- `calibration_data.json`: All measured test data
- `optimization_results.md`: This file
