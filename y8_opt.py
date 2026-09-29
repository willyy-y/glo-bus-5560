#!/usr/bin/env python3
"""
Y8 package optimizer (OFFLINE ONLY — never touches the live game).

Evaluates candidate decision sets with:
  - box demand (reverse-engineered, Y8 scales), dynamic 9-firm price avg,
    empirical promo response (+0.65%/wk, live-measured Y7 box),
  - realistic adjustments from the Y7 backtest: camera units x1.09,
    drone units x0.90, AP/LA revenue FX fix (/1.049), residual x0.99,
    marketing deltas expensed vs the A2 calibration level,
  - image via reverse-engineered image_rating (year_mult=8).
"""
import json, os, sys, copy, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import DemandEngine
from score import image_rating
from pnl import pnl

HERE = os.path.dirname(os.path.abspath(__file__))
REGIONS = ["NA", "EA", "AP", "LA"]

case = json.load(open(os.path.join(HERE, "cases", "y8_calibrated.json")))
cir = json.load(open(os.path.join(HERE, "cases", "y7_cir_actuals.json")))
y7 = json.load(open(os.path.join(HERE, "cases", "y7_calibrated.json")))

FIXED8 = case["fixed"]
UC = case["unit_cost"]
SHARES = case["shares"]
TAX = case["tax_rate"]
G = case["growth_g"]

# A2 marketing total ($k) — the level embedded in FIXED8
def mkt_total(own):
    t = 0.0
    for r in REGIONS:
        c, d = own["camera"][r], own["drone"][r]
        t += c["support_budget"] + c["ad"] + c["web"]
        t += d["support_budget"] + d["ad"] + d["web"]
    return t
MKT_A2 = mkt_total(case["own"])
print(f"A2 marketing total: ${MKT_A2/1000:.2f}M ; FIXED8 ${FIXED8/1e6:.2f}M ; g={G:.4f}")

# Y7 industry units (all 9 firms, actual) grown to Y8
IND8 = {}
for p in ("camera", "drone"):
    IND8[p] = {}
    for r in REGIONS:
        IND8[p][r] = sum(cir[p][r][c]["units_k"] for c in "ABCDEFGHI") * 1000.0 * G

ENG = DemandEngine(scales=case["engine"]["scales"], cal=case["engine"]["cal"],
                   regional_cal=case["engine"]["regional_cal"])

def regional_revenue(units, own):
    """Per-region revenue, same formulas as pnl.revenue (for the AP/LA FX fix)."""
    out = {}
    for p in ("camera", "drone"):
        for r in REGIONS:
            o = own[p][r]
            u = units[p][r]
            if p == "camera":
                w = o.get("prom_weeks", 0); d = o.get("prom_disc", 0) / 100.0
                eff = o["price"] * (1 - w / 52.0 * d)
                out[(p, r)] = eff * u
            else:
                share = o.get("third_party_share", 0.0)
                tp_disc = o.get("third_party_disc", 0) / 100.0
                uv_disc = o.get("uav_disc", 0) / 100.0
                bl = o["price"] * (1 - uv_disc)
                out[(p, r)] = bl * u * (1 - share) + bl * (1 - tp_disc) * u * share
    return out

CIT_BASE = {"charitable": 25000, "energy": 500}
CIT_CSR = {"charitable": 50000, "energy": 5000}


def evaluate(own, cit=CIT_BASE, aggressive=False):
    # dynamic 9-firm price average
    avg = copy.deepcopy(case["avg"])
    for p in ("camera", "drone"):
        for r in REGIONS:
            avg[p][r]["price"] = (own[p][r]["price"] + 8.0 * case["rival_avg"][p][r]) / 9.0
    # iterate demand <-> image twice
    img = 75.0
    for _ in range(2):
        raw = ENG.demand(own, avg, img)
        units = {"camera": {}, "drone": {}}
        for p in ("camera", "drone"):
            for r in REGIONS:
                units[p][r] = raw[p][r]
        # empirical promo response (live Y7 box: +0.65%/wk at 10% disc)
        for r in REGIONS:
            w = own["camera"][r].get("prom_weeks", 0)
            pd = ENG.vlookup(own["camera"][r].get("prom_disc", 0),
                             ENG.tables["demand_promdisc"])
            units["camera"][r] *= 1 + 0.0065 * w * pd
        ind = copy.deepcopy(IND8)
        if aggressive:  # Insider repeats Y7 aggression, grows 15%
            for p in ("camera", "drone"):
                for r in REGIONS:
                    ind[p][r] += cir[p][r]["I"]["units_k"] * 1000.0 * G * 0.15
        cam_r = {r: units["camera"][r] * 9.0 / ind["camera"][r] for r in REGIONS}
        drn_r = {r: units["drone"][r] * 9.0 / ind["drone"][r] for r in REGIONS}
        img = image_rating(8, 47, 41,
                             {"camera": [cam_r[r] for r in REGIONS],
                              "drone": [drn_r[r] for r in REGIONS]}, cit)
    mkt = mkt_total(own)
    box = pnl({"camera": {r: units["camera"][r] for r in REGIONS},
               "drone": {r: units["drone"][r] for r in REGIONS},
               "totals": {}}, own, UC, FIXED8, SHARES, tax_rate=TAX)
    net_box = box["net_profit"] - 0.7 * (mkt - MKT_A2) * 1000.0
    # realistic: product-specific unit bias, FX fix, residual haircut
    ru = {"camera": {r: units["camera"][r] * 1.09 for r in REGIONS},
          "drone": {r: units["drone"][r] * 0.90 for r in REGIONS}}
    rr = regional_revenue(ru, own)
    rev_real = sum(v for (p, r), v in rr.items() if r in ("NA", "EA")) \
        + sum(v for (p, r), v in rr.items() if r in ("AP", "LA")) / 1.049
    rev_real *= 0.99
    cogs_real = sum(ru["camera"][r] * UC["camera"] + ru["drone"][r] * UC["drone"]
                    for r in REGIONS)
    net_real = 0.7 * (rev_real - cogs_real - FIXED8 - (mkt - MKT_A2) * 1000.0)
    rev_box = box["revenue"]
    # realistic shares / image (for reporting)
    ind = copy.deepcopy(IND8)
    if aggressive:
        for p in ("camera", "drone"):
            for r in REGIONS:
                ind[p][r] += cir[p][r]["I"]["units_k"] * 1000.0 * G * 0.15
    cam_r2 = {r: ru["camera"][r] * 9.0 / ind["camera"][r] for r in REGIONS}
    drn_r2 = {r: ru["drone"][r] * 9.0 / ind["drone"][r] for r in REGIONS}
    img_real = image_rating(8, 47, 41,
                      {"camera": [cam_r2[r] for r in REGIONS],
                       "drone": [drn_r2[r] for r in REGIONS]}, cit)
    return {
        "units_cam": sum(ru["camera"].values()) / 1000.0,
        "units_drn": sum(ru["drone"].values()) / 1000.0,
        "rev_box": rev_box, "rev_real": rev_real,
        "net_box": net_box, "net_real": net_real,
        "eps_real": net_real / 1e6 / SHARES,
        "image": img_real, "mkt": mkt,
        "cam_share": {r: ru["camera"][r] / ind["camera"][r] for r in REGIONS},
        "drn_share": {r: ru["drone"][r] / ind["drone"][r] for r in REGIONS},
    }

# ------------------------------------------------------- coordinate descent
VARS = []
for r in REGIONS:
    VARS += [(("camera", r, "price"), 205, 320, 2),
             (("camera", r, "support_budget"), 800, 6000, 100),
             (("camera", r, "ad"), 1000, 9000, 250),
             (("camera", r, "web"), 400, 3500, 100),
             (("drone", r, "price"), 1100, 1750, 10),
             (("drone", r, "ad"), 400, 6000, 200),
             (("drone", r, "web"), 400, 4500, 150),
             (("drone", r, "support_budget"), 400, 4000, 100),
             (("drone", r, "third_party_disc"), 5, 15, 1)]
PROMO_WEEKS = [0, 1, 2, 3, 4, 5, 6]
PROMO_DISC = [10, 12, 15, 18, 20, 22, 25]

def objective(ev, kind):
    if kind == "profit":
        return ev["net_real"]
    if kind == "balanced":
        return ev["net_real"] - 8e6 * max(0, 80 - ev["image"]) ** 2 / 4
    if kind == "image":
        return ev["image"] * 1e6 - 3.0 * max(0, 80e6 - ev["net_real"])
    raise ValueError(kind)

def search(own0, kind, passes=3, verbose=True):
    own = copy.deepcopy(own0)
    best = evaluate(own)
    best_obj = objective(best, kind)
    for ps in range(passes):
        improved = False
        for (p, r, k), lo, hi, step in VARS:
            cur = own[p][r][k]
            for cand in (cur - step, cur + step):
                if cand < lo or cand > hi:
                    continue
                own[p][r][k] = cand
                ev = evaluate(own)
                ob = objective(ev, kind)
                if ob > best_obj + 1e3:
                    best_obj, best = ob, ev
                    cur = cand
                    improved = True
                else:
                    own[p][r][k] = cur
        # promo weeks/disc grid per region
        for r in REGIONS:
            cw, cd = own["camera"][r]["prom_weeks"], own["camera"][r]["prom_disc"]
            for w in PROMO_WEEKS:
                for d in PROMO_DISC:
                    if w == cw and d == cd:
                        continue
                    own["camera"][r]["prom_weeks"] = w
                    own["camera"][r]["prom_disc"] = d
                    ev = evaluate(own)
                    ob = objective(ev, kind)
                    if ob > best_obj + 1e3:
                        best_obj, best = ob, ev
                        cw, cd = w, d
                        improved = True
            own["camera"][r]["prom_weeks"], own["camera"][r]["prom_disc"] = cw, cd
        if verbose:
            print(f"  pass {ps+1}: obj={best_obj/1e6:.2f}M net=${best['net_real']/1e6:.1f}M "
                  f"img={best['image']} rev=${best['rev_real']/1e6:.0f}M")
        if not improved:
            break
    return own, best

def show(name, own, ev):
    print(f"\n### {name}")
    print(f"  net_real ${ev['net_real']/1e6:.1f}M (box ${ev['net_box']/1e6:.1f}M)  "
          f"EPS ${ev['eps_real']:.2f}  image {ev['image']}  rev ${ev['rev_real']/1e6:.0f}M  "
          f"mkt ${ev['mkt']/1000:.1f}M")
    print(f"  units cam {ev['units_cam']:.0f}k drn {ev['units_drn']:.0f}k")
    for r in REGIONS:
        c, d = own["camera"][r], own["drone"][r]
        print(f"  {r}: cam P{c['price']}/S{c['support_budget']:.0f}/A{c['ad']:.0f}/W{c['web']:.0f}/"
              f"{c['prom_weeks']}w@{c['prom_disc']}% | drn P{d['price']}/SA{d['ad']:.0f}/W{d['web']:.0f}/"
              f"R{d['support_budget']:.0f}/D{d['third_party_disc']}%")

if __name__ == "__main__":
    base = case["own"]
    ev0 = evaluate(base)
    show("BASE (A2 carried, cit=base)", base, ev0)

    o1, e1 = search(base, "profit")
    show("P1 PROFIT-MAX", o1, e1)

    o2, e2 = search(base, "balanced")
    show("P2 BALANCED (image>=80 soft)", o2, e2)

    o3, e3 = search(base, "image")
    show("P3 IMAGE-PUSH (net>=$80M soft)", o3, e3)

    json.dump({"p1": {"own": o1, "eval": e1}, "p2": {"own": o2, "eval": e2},
               "p3": {"own": o3, "eval": e3}},
              open(os.path.join(HERE, "cases", "y8_packages_raw.json"), "w"))
    print("\nwrote cases/y8_packages_raw.json")
