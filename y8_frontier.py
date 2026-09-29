#!/usr/bin/env python3
"""Y8 efficient frontier: structural variants + marginal $/image-point.

OFFLINE ONLY. Reuses evaluate() from y8_opt.py.
"""
import json, os, sys, copy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from y8_opt import evaluate, case, REGIONS, CIT_BASE, CIT_CSR

base = case["own"]

def variant(name, fn, cit=CIT_BASE, aggressive=False):
    own = copy.deepcopy(base)
    fn(own)
    ev = evaluate(own, cit=cit, aggressive=aggressive)
    return name, own, ev

def show(name, own, ev):
    print(f"{name:34s} net=${ev['net_real']/1e6:6.1f}M box=${ev['net_box']/1e6:6.1f}M "
          f"EPS=${ev['eps_real']:.2f} img={ev['image']:3d} rev=${ev['rev_real']/1e6:.0f}M "
          f"mkt=${ev['mkt']/1000:.1f}M cam={ev['units_cam']:.0f}k drn={ev['units_drn']:.0f}k")

results = []
# V0 base
results.append(variant("V0 base(A2 carried)", lambda o: None))
# V1 profit-max operating (from coordinate descent P1)
p1 = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "cases", "y8_packages_raw.json")))["p1"]["own"]
results.append(("V1 profit-max operating", p1, evaluate(p1)))
# V1 + CSR
results.append(("V1 + CSR max", p1, evaluate(p1, cit=CIT_CSR)))

# V2 aggressive share push: price cuts + marketing to field avg
def aggr(o):
    for r in REGIONS:
        o["camera"][r]["price"] -= 8
        o["camera"][r]["support_budget"] = 4200 if r in ("NA", "EA") else 3000
        o["camera"][r]["ad"] = 7000 if r in ("NA", "EA") else o["camera"][r]["ad"]
        o["camera"][r]["prom_weeks"] = 4
        o["camera"][r]["prom_disc"] = 18
        o["drone"][r]["price"] -= 100
        o["drone"][r]["ad"] = 4000 if r in ("NA", "EA") else 2000
        o["drone"][r]["web"] = 3000 if r in ("NA", "EA") else 1500
        o["drone"][r]["support_budget"] = 2500 if r in ("NA", "EA") else 1500
results.append(variant("V2 aggressive share", aggr))
results.append(variant("V2 aggressive + CSR", aggr, cit=CIT_CSR))

# V3: V1 operating + P/Q upgrades (cam 47->51, drn 41->46).
# Image gain from tables: +0.625 +1.125 = +1.75 -> +2 pts (verified below).
# Profit cost: ~$17.7M cam + $18.4M drn pre-tax (Y7 evidence) -> x0.7 net.
n, o, e = variant("V3 V1+P/Qup (no CSR)", lambda o: None)
e = dict(e)
e["net_real"] -= 0.7 * (17.7 + 18.4) * 1e6
e["eps_real"] = e["net_real"] / 1e6 / 19.8
e["image"] += 2
results.append((n, o, e))
n, o, e = variant("V3b V1+P/Qup + CSR", lambda o: None, cit=CIT_CSR)
e = dict(e)
e["net_real"] -= 0.7 * (17.7 + 18.4) * 1e6
e["eps_real"] = e["net_real"] / 1e6 / 19.8
e["image"] += 2
results.append((n, o, e))

for name, own, ev in results:
    show(name, own, ev)

# marginal $/image-point between key pairs
print("\n--- marginal tradeoffs ---")
def mp(a, b):
    na, nb = a[2], b[2]
    dimg = nb["image"] - na["image"]
    dnet = nb["net_real"] - na["net_real"]
    per = abs(dnet / 1e6 / dimg) if dimg else float("nan")
    print(f"{a[0]} -> {b[0]}: {dimg:+d} img pts, ${dnet/1e6:+.1f}M net "
          f"=> ${per:.2f}M per image point")
pairs = [(results[1], results[5]),  # V1 -> V2+CSR
         (results[1], results[2]),  # V1 -> V1+CSR
         (results[5], results[4]),  # V2 -> V2+CSR (same operating)
         ]
for a, b in pairs:
    mp(a, b)
