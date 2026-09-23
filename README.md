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
- `sweep.py` — CLI for test runs.
- `pnl.py` — P&L layer.
- `calibrate.py` — group scale solver (historical).
- `cases/y7_calibrated.json` — master case (decisions, avgs, scales, costs).
- `cases/y7_base.json` — backup of decisions.
- `cases/y7_observations.json` — live experiment data.

## Limitations

- Design costs (sensor mm, stabilization level, etc.) are not modeled.
  The unit_cost is fixed; P/Q changes affect demand but not cost.
- Exchange rates for AP/LA revenue are approximated (4.9% high).
- Competitive assumptions are static; rival reactions not modeled
  (use --scenario for synthetic rival behaviors).
- Image rating effects are simplified.
