#!/usr/bin/env python3
"""Y8 final candidates: clean evaluation, base + aggressive (Insider repeats).

OFFLINE ONLY. P/Q upgrade modeled properly: pq enters demand + image,
profit cost $17.7M cam + $18.4M drn pre-tax (Y7 evidence) applied net of tax.
"""
import json, os, sys, copy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from y8_opt import evaluate, case, REGIONS, CIT_BASE, CIT_CSR, ENG

HERE = os.path.dirname(os.path.abspath(__file__))
p1 = json.load(open(os.path.join(HERE, "cases", "y8_packages_raw.json")))["p1"]["own"]

def with_pq(own, cam_pq, drn_pq):
    o = copy.deepcopy(own)
    for r in REGIONS:
        o["camera"][r]["pq"] = cam_pq
        o["drone"][r]["pq"] = drn_pq
    return o

# P/Q upgrade cost (pre-tax $M) -> net
PQ_COST_NET = 0.7 * (17.7 + 18.4)

cands = []
# A: profit-max operating + CSR (recommended core)
cands.append(("A profit-op + CSR", p1, CIT_CSR, 47, 41, 0.0))
# B: profit-max operating, no CSR (fallback if CSR mechanics distrusted)
cands.append(("B profit-op, no CSR", p1, CIT_BASE, 47, 41, 0.0))
# C: profit-max operating + CSR + P/Q up
cands.append(("C profit-op + CSR + P/Q", p1, CIT_CSR, 51, 46, PQ_COST_NET))

for name, own0, cit, cpq, dpq, pqcost in cands:
    own = with_pq(own0, cpq, dpq)
    for scen, agg in (("base", False), ("aggr", True)):
        ev = evaluate(own, cit=cit, aggressive=agg)
        ev["net_real"] -= pqcost * 1e6
        ev["eps_real"] = ev["net_real"] / 1e6 / 19.8
        print(f"{name:26s} [{scen}] net=${ev['net_real']/1e6:6.1f}M "
              f"box=${ev['net_box']/1e6:6.1f}M EPS=${ev['eps_real']:.2f} "
              f"img={ev['image']:3d} rev=${ev['rev_real']/1e6:.0f}M "
              f"mkt=${ev['mkt']/1000:.1f}M cam_sh={sum(ev['cam_share'].values())/4*100:.1f}% "
              f"drn_sh={sum(ev['drn_share'].values())/4*100:.1f}%")

# P/Q image delta check on candidate A operating point
e1 = evaluate(with_pq(p1, 47, 41), cit=CIT_CSR)
e2 = evaluate(with_pq(p1, 51, 46), cit=CIT_CSR)
print(f"\nP/Q 47/41 -> 51/46 image: {e1['image']} -> {e2['image']} "
      f"(demand-effect included); net cost ${PQ_COST_NET:.1f}M")
