#!/usr/bin/env python3
"""
Y8 calibration workbench (OFFLINE ONLY — never touches the live game).

Stage 1: Y7 backtest — run our Y7 A2 decisions against TRUE Y7 CIR rival
         averages; quantify residual model bias vs Y7 actuals.
Stage 2: Build cases/y8_calibrated.json — Y8 base case:
         own = Y7 A2 decisions (carried forward),
         avg = Y8 competitive-assumption cells (Y7-actual-based),
         rival_avg = Y7 true 8-rival price means,
         scales grown to reproduce the game's Y8 carried-forward projection
         (revenue $561.768M), fixed block calibrated to its $107.807M profit.
"""
import json, os, sys, copy, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import DemandEngine
from pnl import pnl, calibrate_fixed

HERE = os.path.dirname(os.path.abspath(__file__))
REGIONS = ["NA", "EA", "AP", "LA"]
COS = list("ABCDEFGHI")

cir = json.load(open(os.path.join(HERE, "cases", "y7_cir_actuals.json")))
y7 = json.load(open(os.path.join(HERE, "cases", "y7_calibrated.json")))

# ------------------------------------------------------------------ helpers
def avg9(product, region, field):
    return sum(cir[product][region][c][field] for c in COS) / 9.0

def rival8(product, region, field):
    return sum(cir[product][region][c][field] for c in COS if c != "E") / 8.0

# Our Y7 A2 decisions (entered live 2026-09-27)
A2 = {
    "camera": {
        "NA": {"price": 261, "support_budget": 2899, "ad": 5988, "web": 1700,
               "prom_weeks": 0, "prom_disc": 10},
        "EA": {"price": 277, "support_budget": 2359, "ad": 3400, "web": 1400,
               "prom_weeks": 0, "prom_disc": 10},
        "AP": {"price": 223, "support_budget": 2169, "ad": 2500, "web": 1050,
               "prom_weeks": 0, "prom_disc": 10},
        "LA": {"price": 218, "support_budget": 1597, "ad": 1800, "web": 700,
               "prom_weeks": 0, "prom_disc": 10},
    },
    "drone": {
        "NA": {"price": 1490, "ad": 1700, "web": 1662,
               "third_party_disc": 7, "uav_disc": 7},
        "EA": {"price": 1490, "ad": 1400, "web": 1365,
               "third_party_disc": 7, "uav_disc": 7},
        "AP": {"price": 1445, "ad": 700, "web": 985,
               "third_party_disc": 7, "uav_disc": 7},
        "LA": {"price": 1445, "ad": 400, "web": 698,
               "third_party_disc": 7, "uav_disc": 7},
    },
}
# Infer drone retailer-recruitment budgets from Y7 actual $/unit.
# budget($k) = $/u x units_k x 3p_share ; 3p share ~12.6% at 7% discount
TP_SHARE = 0.126
for r in REGIONS:
    rec = cir["drone"][r]["E"]["recruit"]
    units_k = cir["drone"][r]["E"]["units_k"]
    A2["drone"][r]["support_budget"] = round(rec * units_k * TP_SHARE, 1)
    A2["drone"][r]["third_party_share"] = TP_SHARE

def make_own(a2):
    own = {"camera": {}, "drone": {}}
    for r in REGIONS:
        c = dict(a2["camera"][r])
        c.update({"pq": 47, "warranty_days": 180, "models": 2,
                  "chains": 0, "online": 0, "local": 0})
        own["camera"][r] = c
        d = dict(a2["drone"][r])
        d.update({"pq": 41, "warranty_days": 180, "models": 2,
                  "online": 0, "support": 0.0})
        own["drone"][r] = d
    return own

def run(own, avg, rival_avg, scales, cal, regional_cal, image, unit_cost,
        fixed, shares, tax=0.30):
    # dynamic 9-firm price avg: (own + 8*rival)/9
    avg = copy.deepcopy(avg)
    for p in ("camera", "drone"):
        for r in REGIONS:
            rv = rival_avg[p][r]
            avg[p][r]["price"] = (own[p][r]["price"] + 8.0 * rv) / 9.0
    eng = DemandEngine(scales=scales, cal=cal, regional_cal=regional_cal)
    units = eng.demand(own, avg, image)
    res = pnl(units, own, unit_cost, fixed, shares, tax_rate=tax)
    res["units"] = units
    return res

# ================================================================ STAGE 1
print("=" * 64)
print("STAGE 1: Y7 backtest — A2 decisions vs TRUE Y7 rival averages")
print("=" * 64)
own7 = make_own(A2)
avg7 = {"camera": {}, "drone": {}}
rival7 = {"camera": {}, "drone": {}}
for r in REGIONS:
    avg7["camera"][r] = {"price": 0, "ad": avg9("camera", r, "ad"),
        "support": avg9("camera", r, "support"), "web": avg9("camera", r, "web"),
        "chains": 0, "online": 0, "local": 0, "models": 2.8}
    avg7["drone"][r] = {"price": 0, "ad": avg9("drone", r, "search"),
        "support": avg9("drone", r, "recruit"), "web": avg9("drone", r, "web"),
        "chains": 0, "online": 0, "local": 0, "models": 2.1}
    rival7["camera"][r] = rival8("camera", r, "price")
    rival7["drone"][r] = rival8("drone", r, "price")

bt = run(own7, avg7, rival7, y7["engine"]["scales"], y7["engine"]["cal"],
         y7["engine"]["regional_cal"], image=75,
         unit_cost=y7["unit_cost"], fixed=y7["fixed"], shares=19.8)
cam_u = bt["units_cam"] / 1000.0
drn_u = bt["units_drone"] / 1000.0
print(f"predicted camera units: {cam_u:8.1f}k   actual 1224.7k")
print(f"predicted drone  units: {drn_u:8.1f}k   actual  138.5k")
print(f"predicted revenue:      ${bt['revenue']/1e6:8.1f}M   actual $489.0M")
print(f"predicted net profit:   ${bt['net_profit']/1e6:8.1f}M   actual  $77.3M")
print(f"predicted EPS:           {bt['eps']:8.2f}     actual   3.90")
bias_rev = bt["revenue"] / 489.007e6 - 1
bias_u = (cam_u + drn_u) / (1224.7 + 138.5) - 1
print(f"\nresidual bias: revenue {bias_rev:+.1%}, units {bias_u:+.1%}")
print("(positive = model still optimistic even with TRUE rival avgs)")

# ================================================================ STAGE 2
print("\n" + "=" * 64)
print("STAGE 2: build Y8 base case")
print("=" * 64)
# Y8 competitive-assumption cells (read live 2026-09-29; Y7-actual-based)
AM8 = {
    "camera": {
        "NA": {"price": 255, "ad": 4083, "support": 8.20, "web": 1839, "models": 3.0},
        "EA": {"price": 263, "ad": 2853, "support": 7.90, "web": 1622, "models": 3.0},
        "AP": {"price": 250, "ad": 1994, "support": 8.60, "web": 1308, "models": 3.0},
        "LA": {"price": 247, "ad": 1554, "support": 8.70, "web": 961,  "models": 3.0},
    },
    "drone": {
        "NA": {"price": 1572, "ad": 2986, "support": 167.10, "web": 2224, "models": 2.3},
        "EA": {"price": 1596, "ad": 2142, "support": 172.10, "web": 1838, "models": 2.3},
        "AP": {"price": 1633, "ad": 1438, "support": 207.20, "web": 1339, "models": 2.3},
        "LA": {"price": 1518, "ad": 756,  "support": 156.40, "web": 883,  "models": 2.3},
    },
}
avg8 = {"camera": {}, "drone": {}}
for r in REGIONS:
    for p in ("camera", "drone"):
        a = dict(AM8[p][r]); a["price"] = 0  # recomputed dynamically
        a.update({"chains": 0, "online": 0, "local": 0})
        avg8[p][r] = a

own8 = make_own(A2)
# growth-calibrate scales to the game's Y8 carried-forward projection
# (revenue $561.768M at image 77, the box's own assumptions)
scales = dict(y7["engine"]["scales"])
def rev_at(g):
    sc = {k: v * g for k, v in scales.items()}
    r = run(own8, avg8, rival7, sc, y7["engine"]["cal"],
            y7["engine"]["regional_cal"], image=77,
            unit_cost=y7["unit_cost"], fixed=0, shares=19.8)
    return r["revenue"], r["contribution"]
g = 561.768e6 / rev_at(1.0)[0]
for _ in range(4):
    r0, _ = rev_at(g)
    g *= 561.768e6 / r0
rev0, contrib0 = rev_at(g)
fixed8 = calibrate_fixed(contrib0, 107.807e6, 0.30)
print(f"growth factor g = {g:.4f}")
print(f"calibrated revenue: ${rev0/1e6:.1f}M (target $561.8M)")
print(f"calibrated fixed block: ${fixed8/1e6:.2f}M (Y7 was $36.0M)")

# working case: honest image=75
base = run(own8, avg8, rival7,
           {k: v * g for k, v in scales.items()}, y7["engine"]["cal"],
           y7["engine"]["regional_cal"], image=75,
           unit_cost=y7["unit_cost"], fixed=fixed8, shares=19.8)
print(f"\nY8 base (A2 carried, image 75):")
print(f"  camera {base['units_cam']/1000:.1f}k  drone {base['units_drone']/1000:.1f}k")
print(f"  revenue ${base['revenue']/1e6:.1f}M  net ${base['net_profit']/1e6:.1f}M  EPS ${base['eps']:.2f}")

case8 = {
    "_note": ("Y8 base case. own = Y7 A2 decisions carried forward; "
              "avg = Y8 AM cells (Y7-actual-based); rival_avg = Y7 true 8-rival "
              "price means; scales grown by g to match game Y8 carried projection; "
              "fixed calibrated to game $107.807M box profit. image=75 working level. "
              "OFFLINE ONLY."),
    "own": own8, "avg": avg8, "rival_avg": rival7,
    "engine": {"scales": {k: v * g for k, v in scales.items()},
               "cal": y7["engine"]["cal"],
               "regional_cal": y7["engine"]["regional_cal"]},
    "growth_g": g,
    "fixed": fixed8,
    "image": 75,
    "unit_cost": y7["unit_cost"],
    "shares": 19.8,
    "tax_rate": 0.30,
    "production": y7["production"],
    "y7_backtest_bias": {"revenue": bias_rev, "units": bias_u},
}
json.dump(case8, open(os.path.join(HERE, "cases", "y8_calibrated.json"), "w"))
print("\nwrote cases/y8_calibrated.json")
