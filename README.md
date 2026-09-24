# GLO-BUS Offline Engine

Reverse-engineered demand model from the GLO-BUS 6.22.1 client bundle.
Strictly read-only testbed for Y7 decisions. Never writes to the live game.

## What it does

Reproduces the Year 7 Market Segment Statistics projection box for
Company E (Evading Taxes LLC), Industry 18, including:

- All 15 VLOOKUP demand tables with approximate-match semantics.
- Additive (Σ VLOOKUP×scenario-constants) × multiplicative (price/model/image) structure.
- Dynamic 9-firm average for price: avg = (own + 8×rival)/9. We are 1 of 9.
- Retailer support $/unit fixed-point iteration (budget ÷ units).
- Drone 3rd-party support $/unit (budget ÷ 3rd-party units).
- Per-region market-size multipliers (regional_cal).
- P&L with calibrated fixed block.

## Validation (vs live browser experiments, 2026-09-23)

| Test | Demand err | Net err |
|------|-----------|---------|
| Base | 0.00% | $0.0M |
| Cam P/Q 4.6 (B1) | +0.51% | — (cost not modeled) |
| Cam price $253 (B3) | −0.04% | +$0.2M |
| Cam warranty 90d (B4) | −0.14% | −$1.2M |
| Drone price $1290 (B5) | −0.03% | −$0.2M |
| Drone P/Q 4.2 (B6) | −0.27% | — (cost not modeled) |

Demand is within 0.5% on all 8 points. P&L is within $0.2M for price
changes. Design cost changes (sensor, stabilization) are NOT modeled;
use empirical profit impacts from live tests for P/Q decisions.

## Usage

```bash
# base case with calibrated competitive assumptions
python3 sweep.py

# price sweep (NA camera $243-$263)
python3 sweep.py --vary camera.NA.price 243 263 5

# rival scenarios: assumptions (default), flat, escalate, aggressive, mixed
python3 sweep.py --scenario escalate --vary drone.NA.price 1190 1390 50
```

## Files

- `engine.py` — demand model.
- `pq.py` — P/Q rating model (design choices -> 0-100 score -> 1-10 display).
- `pq_tables.json` — 22 P/Q lookup tables extracted from the client bundle.
- `score.py` — scoring model: EPS, ROE, credit rating (3 VLOOKUP inputs ->
  points -> grade, exact), image rating (share/PQ/citizenship, exact), I.E.
  and B-I-I annual + game-to-date, weighted-average + overall score,
  Bull's Eye and Leap Frog bonuses. Annual I.E. validated exact (116)
  against Y6 Company E live CDJ. Stock price is server-side (unpublished
  weights) — supplied as an input, not computed.
- `research/scoring_report.md` — full scoring reverse-engineering report.
- `research/scoring_tables.json` — credit/image/citizenship lookup tables.
- `sweep.py` — CLI for test runs.
- `pnl.py` — P&L layer.
- `calibrate.py` — group scale solver (historical).
- `cases/y7_calibrated.json` — master case (decisions, avgs, scales, costs).
- `cases/y7_base.json` — backup of decisions.
- `cases/y7_observations.json` — live experiment data.

## P/Q model (`pq.py`)

Computes camera and drone P/Q ratings from design choices, exactly as the
game's Product Design page does:

    camera: clamp(5,100, round(sum(9 component scores) x R&D multiplier))
    drone:  clamp(5,100, round(sum(11 component scores) x R&D multiplier))

The drone's built-in-camera score comes from (own camera P/Q - industry
average camera P/Q), so camera upgrades also lift drone P/Q. Validated
against all 8 live design experiments (9/9 exact, 2026-09-24).

```python
from pq import camera_pq, drone_pq, baseline_camera_design
pq100, display = camera_pq(baseline_camera_design())  # (47, 4.7)
```

Caveat: design choices also change unit production costs, which the bundle
computes outside the P/Q path and which are NOT modeled here. Empirical
marginals from live tests: ~$3.01/unit per 0.1 camera P/Q,
~$20.70/unit per 0.1 drone P/Q.

## Limitations

- Design unit costs (sensor mm, stabilization level, etc.) are not modeled.
  The unit_cost is fixed; P/Q changes affect demand but not cost. See the
  P/Q model section for empirical marginal costs from live tests.
- Exchange rates for AP/LA revenue are approximated (4.9% high).
- Competitive assumptions are static; rival reactions not modeled
  (use --scenario for synthetic rival behaviors).
- Image rating effects are simplified.
