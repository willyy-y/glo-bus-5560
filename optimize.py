#!/usr/bin/env python3
"""
GLO-BUS Y7 full optimizer (OFFLINE ONLY — never touches the live game).

Extends the price optimizer with:
  - Per-region marketing spend (retailer support, advertising/search ads,
    website) via constant-elasticity demand multipliers fitted from NA tests.
  - Camera promo weeks (0/1) as a demand multiplier + revenue factor.
  - Drone third-party discount (continuous) affecting total demand and
    channel mix (direct vs 3rd-party).
  - Image rating prediction (structural, from score.py) tracked alongside
    profit.

Model summary:
  Demand (unconstrained):
    D_cam[r] = price_curve[r](p[r]) * Prod_c (S[r][c]/S0[r][c])^b_c * promo_mult
    D_drn[r] = price_curve[r](p[r]) * (search[r]/s0[r])^b_s * (web[r]/w0[r])^b_w
               * total_disc(d)/221.2
  Sales = proportional cap at capacity (1355k cam, 217k drn).
  Production = sales (produce to demand).
  Revenue = k_rev * sum(sales * eff_price); drone eff includes 3p discount.
  Cost = prod_cost + adder + marketing_spend.
  Profit = 0.7 * (Revenue - Cost - Fixed_calibrated - (Mkt - Mkt_base)).

Run: python3 optimize.py
"""

import json
import math
import os
import sys

import numpy as np
from scipy.optimize import minimize, minimize_scalar

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from score import image_rating as _image_rating
from engine import DemandEngine

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "calibration_data.json")) as f:
    DATA = json.load(f)

REGIONS = DATA["regions"]
TAX = DATA["pnl"]["tax_rate"]
SHARES_M = DATA["pnl"]["shares_m"]
CAP = DATA["capacity_k"]
BASE_P = {p: DATA[p]["baseline_prices"] for p in ("camera", "drone")}

# ---------------------------------------------------------------- constants
CAM_PROMO_WEEKS_BASE = 1
CAM_PROMO_DISC = 10
# promo demand multiplier (1 wk vs 0 wk), from measured 1372.9/1364.0
PROMO_DEM_MULT = 1372.9 / 1364.0
# promo revenue factor
PROMO_REV = {1: 1 - (1 / 52.0) * (CAM_PROMO_DISC / 100.0), 0: 1.0}

DRONE_3P_BASE = 0.10
# total drone demand vs discount: linear fit 210.8 + 104*d
def _drone_total_disc(d):
    return 210.8 + 104.0 * d
# 3p units vs discount: quadratic fit 21.8 - 164*d + 3520*d^2 (at base total)
def _drone_3p_units_base(d):
    return 21.8 - 164.0 * d + 3520.0 * d * d
def drone_3p_share(d):
    tot = _drone_total_disc(d)
    return max(0.0, min(1.0, _drone_3p_units_base(d) / tot))

# Marketing elasticities (constant-elasticity, fitted from NA tests)
MKT_B = {
    ("camera", "retailer_support"): 0.0632,
    ("camera", "advertising"): 0.1285,
    ("camera", "website"): 0.0465,
    ("drone", "search_ads"): 0.0766,
    ("drone", "website"): 0.0465,  # no drone website test; use camera website b
}
MKT_CHANNELS = {
    "camera": ["retailer_support", "advertising", "website"],
    "drone": ["search_ads", "website"],
}
MKT_BASE = DATA["marketing"]["baseline_spend"]
MKT_BASE_TOTAL = sum(
    v for p in MKT_BASE for r in MKT_BASE[p] for v in MKT_BASE[p][r].values()
)

# ------------------------------------------------------------ demand curves
def _fit_best(p, r):
    pts = DATA[p]["points"]
    pr = np.array([pt["prices"][r] for pt in pts], float)
    u = np.array([pt["units"][r] for pt in pts], float)
    best = (1e18, None)
    # CE
    X = np.vstack([np.ones_like(pr), np.log(pr)]).T
    coef, *_ = np.linalg.lstsq(X, np.log(u), rcond=None)
    A0, e = math.exp(coef[0]), -coef[1]
    err = float(np.max(np.abs(A0 * pr ** (-e) - u)))
    if err < best[0]:
        best = (err, ("CE", A0, e))
    # linear
    X = np.vstack([np.ones_like(pr), pr]).T
    coef, *_ = np.linalg.lstsq(X, u, rcond=None)
    err = float(np.max(np.abs(coef[0] + coef[1] * pr - u)))
    if err < best[0]:
        best = (err, ("lin", float(coef[0]), float(coef[1])))
    # loglin
    X = np.vstack([np.ones_like(pr), np.log(pr)]).T
    coef, *_ = np.linalg.lstsq(X, u, rcond=None)
    err = float(np.max(np.abs(coef[0] + coef[1] * np.log(pr) - u)))
    if err < best[0]:
        best = (err, ("loglin", float(coef[0]), float(coef[1])))
    return best[1], best[0]

PRICE_FITS = {}
PRICE_FIT_ERR = {}
for _p in ("camera", "drone"):
    for _r in REGIONS:
        _params, _err = _fit_best(_p, _r)
        PRICE_FITS[(_p, _r)] = _params
        PRICE_FIT_ERR[(_p, _r)] = _err

def price_demand(p, r, price):
    t = PRICE_FITS[(p, r)]
    if t[0] == "CE":
        return t[1] * price ** (-t[2])
    if t[0] == "lin":
        return max(0.0, t[1] + t[2] * price)
    return max(0.0, t[1] + t[2] * math.log(price))

# ------------------------------------------------------- camera cost curve
_pts_c = DATA["camera"]["points"]
_U = np.array([min(sum(_pt["units"].values()), CAP["camera"]) for _pt in _pts_c])
_c = np.array([_pt["unit_cost"] for _pt in _pts_c])
_X = np.vstack([np.ones_like(_U), 1.0 / _U]).T
_cc, *_ = np.linalg.lstsq(_X, _c, rcond=None)
def cam_unit_cost(U):
    return _cc[0] + _cc[1] / max(U, 1.0)
DRONE_UNIT_COST = 748.70

# ------------------------------------------------------- profit calibration
# k_rev, A_cam, A_dr, Fixed fitted by least squares on all profit points
# (with sales cap). Values from 2026-09-24 analysis.
K_REV = 0.9643
A_CAM = 5.71
A_DR = -22.79
FIXED = 89255.0

# ------------------------------------------------------- image rating model
# Structural, calibrated: baseline image 85, 0%-discount image 84.
# share_ratio = R_SHARE * (sales / sales_base), R_SHARE=1.35
R_SHARE = 1.35
CIT_PTS = 4.0
CAM_PQ100 = 47
DRN_PQ100 = 41
# baseline sales (capped) by region, for ratio normalization
def _base_sales():
    out = {}
    for p in ("camera", "drone"):
        base = DATA[p]["points"][0]["units"]
        D = sum(base.values())
        f = min(1.0, CAP[p] / D)
        out[p] = {r: base[r] * f for r in REGIONS}
    return out
BASE_SALES = _base_sales()

_vlookup = DemandEngine.vlookup
with open(os.path.join(HERE, "research", "scoring_tables.json")) as f:
    _T = json.load(f)
_SHARE_TBL = np.array(_T["image_share"])
def _share_pts_smooth(ratio):
    return float(np.interp(ratio, _SHARE_TBL[:, 0], _SHARE_TBL[:, 1]))

def predict_image(cam_sales, drn_sales):
    """cam/drn_sales: dicts region->k units sold. Returns int image.
    Uses smooth (interpolated) share table for optimizer stability."""
    share_pts = 0.0
    for p, sales in (("camera", cam_sales), ("drone", drn_sales)):
        for r in REGIONS:
            base = BASE_SALES[p][r]
            ratio = R_SHARE * (sales[r] / base) if base > 0 else 0
            share_pts += _share_pts_smooth(ratio)
    pq_pts = _vlookup(CAM_PQ100, _T["image_pq"]) + _vlookup(DRN_PQ100, _T["image_pq"])
    year_mult = _vlookup(7, _T["image_year"])
    return int(min(100, round((share_pts + pq_pts) * year_mult + CIT_PTS, 0)))

# ------------------------------------------------------------------ model
class Model:
    def __init__(self):
        pass

    def demand(self, cam_p, drn_p, mkt, promo_weeks, disc):
        """Unconstrained demand by region. mkt[p][r][c] = spend $000s."""
        Dc, Dd = {}, {}
        pm = PROMO_DEM_MULT if promo_weeks == 1 else 1.0
        for r in REGIONS:
            m = price_demand("camera", r, cam_p[r])
            for c in MKT_CHANNELS["camera"]:
                s0 = MKT_BASE["camera"][r][c]
                s = max(mkt["camera"][r][c], 1.0)
                m *= (s / s0) ** MKT_B[("camera", c)]
            Dc[r] = m * pm
        disc_mult = _drone_total_disc(disc) / 221.2
        for r in REGIONS:
            m = price_demand("drone", r, drn_p[r])
            for c in MKT_CHANNELS["drone"]:
                s0 = MKT_BASE["drone"][r][c]
                s = max(mkt["drone"][r][c], 1.0)
                m *= (s / s0) ** MKT_B[("drone", c)]
            Dd[r] = m * disc_mult
        return Dc, Dd

    def sales(self, Dc, Dd):
        Sc, Sd = {}, {}
        fc = min(1.0, CAP["camera"] / max(sum(Dc.values()), 1e-9))
        fd = min(1.0, CAP["drone"] / max(sum(Dd.values()), 1e-9))
        for r in REGIONS:
            Sc[r] = Dc[r] * fc
            Sd[r] = Dd[r] * fd
        return Sc, Sd

    def profit(self, cam_p, drn_p, mkt, promo_weeks, disc):
        """Net profit in $000s. mkt nested dict; promo 0/1; disc fraction."""
        Dc, Dd = self.demand(cam_p, drn_p, mkt, promo_weeks, disc)
        Sc, Sd = self.sales(Dc, Dd)
        Pc, Pd = sum(Sc.values()), sum(Sd.values())
        # revenue
        rev_c = sum(Sc[r] * cam_p[r] * PROMO_REV[promo_weeks] for r in REGIONS)
        s3 = drone_3p_share(disc)
        rev_d = sum(Sd[r] * drn_p[r] * (1 - s3 * disc) for r in REGIONS)
        rev = K_REV * (rev_c + rev_d)
        # costs
        prod = Pc * cam_unit_cost(Pc) + Pd * DRONE_UNIT_COST
        adder = Pc * A_CAM + Pd * A_DR
        mkt_tot = sum(mkt[p][r][c] for p in mkt for r in mkt[p] for c in mkt[p][r])
        fixed_adj = FIXED + (mkt_tot - MKT_BASE_TOTAL)
        return (rev - prod - adder - fixed_adj) * (1 - TAX), Sc, Sd

    def image(self, Sc, Sd):
        return predict_image(Sc, Sd)

# ------------------------------------------------------------- validation
def _base_mkt():
    return {p: {r: dict(MKT_BASE[p][r]) for r in REGIONS}
            for p in ("camera", "drone")}

def validate(model):
    print("== Validation ==")
    # 1. price points (baseline mkt, promo=1, disc=10%)
    maxdev = 0
    for p in ("camera", "drone"):
        for pt in DATA[p]["points"]:
            cp = {r: pt["prices"][r] if p == "camera" else BASE_P["camera"][r]
                  for r in REGIONS}
            dp = {r: pt["prices"][r] if p == "drone" else BASE_P["drone"][r]
                  for r in REGIONS}
            pred, _, _ = model.profit(cp, dp, _base_mkt(), 1, 0.10)
            dev = pred - pt["profit_k"]
            maxdev = max(maxdev, abs(dev))
    print(f"price points: max|dev| = {maxdev:.0f}k")
    # 2. uniform optima
    for p, bnds in (("camera", (-40, 80)), ("drone", (0, 600))):
        def f(d, p=p):
            cp = {r: BASE_P["camera"][r] + (d if p == "camera" else 0)
                  for r in REGIONS}
            dp = {r: BASE_P["drone"][r] + (d if p == "drone" else 0)
                  for r in REGIONS}
            prof, _, _ = model.profit(cp, dp, _base_mkt(), 1, 0.10)
            return -prof
        res = minimize_scalar(f, bounds=bnds, method="bounded")
        print(f"{p} uniform optimum: +${res.x:.1f} (expect ~+17 / ~+360)")
    # 3. marketing tests
    print("\nmarketing tests (model profit delta vs measured):")
    tests = DATA["marketing"]["tests"]
    # website NA 1700->700
    t = tests[0]
    mkt = _base_mkt(); mkt["camera"]["NA"]["website"] = 700
    pred, _, _ = model.profit(
        {r: BASE_P["camera"][r] for r in REGIONS},
        {r: BASE_P["drone"][r] for r in REGIONS}, mkt, 1, 0.10)
    print(f"  website NA cut: pred {pred-74108:+.0f}k vs meas +509k")
    # promo 1->0
    pred, _, _ = model.profit(
        {r: BASE_P["camera"][r] for r in REGIONS},
        {r: BASE_P["drone"][r] for r in REGIONS}, _base_mkt(), 0, 0.10)
    print(f"  promo 1->0: pred {pred-74108:+.0f}k vs meas +432k")
    # discount 10%->5% and 10%->0%
    for disc, label in ((0.05, "5%"), (0.00, "0%")):
        pred, _, _ = model.profit(
            {r: BASE_P["camera"][r] for r in REGIONS},
            {r: BASE_P["drone"][r] for r in REGIONS}, _base_mkt(), 1, disc)
        meas = 75650 if disc == 0.05 else 75086
        print(f"  disc ->{label}: pred {pred-74108:+.0f}k vs meas {meas-74108:+.0f}k")
    # 4. image at baseline and 0% discount
    _, Sc, Sd = model.profit(
        {r: BASE_P["camera"][r] for r in REGIONS},
        {r: BASE_P["drone"][r] for r in REGIONS}, _base_mkt(), 1, 0.10)
    print(f"\nimage at baseline: {model.image(Sc, Sd)} (expect 85)")
    _, Sc, Sd = model.profit(
        {r: BASE_P["camera"][r] for r in REGIONS},
        {r: BASE_P["drone"][r] for r in REGIONS}, _base_mkt(), 1, 0.00)
    print(f"image at 0% disc: {model.image(Sc, Sd)} (expect 84)")

# ------------------------------------------------------------- optimization
def optimize(model):
    # JOINT optimization: all variables together (image depends on both).
    # Variables: cam_p[4], cam_mkt[12], drn_p[4], drn_mkt[8], disc[1] = 29.
    # Promo tried at 0 and 1.
    results = {}
    for promo in (0, 1):
        x0, bounds, idx = [], [], {}
        for r in REGIONS:
            idx[("cp", r)] = len(x0); x0.append(BASE_P["camera"][r])
            bounds.append((180, 400))
        for r in REGIONS:
            for c in MKT_CHANNELS["camera"]:
                idx[("cm", r, c)] = len(x0)
                x0.append(MKT_BASE["camera"][r][c])
                bounds.append((100, MKT_BASE["camera"][r][c]))
        for r in REGIONS:
            idx[("dp", r)] = len(x0); x0.append(BASE_P["drone"][r])
            bounds.append((1000, 1750))
        for r in REGIONS:
            for c in MKT_CHANNELS["drone"]:
                idx[("dm", r, c)] = len(x0)
                x0.append(MKT_BASE["drone"][r][c])
                bounds.append((100, MKT_BASE["drone"][r][c]))
        idx["disc"] = len(x0); x0.append(0.05); bounds.append((0.0, 0.15))

        def f(x, promo=promo, idx=idx):
            cp = {r: x[idx[("cp", r)]] for r in REGIONS}
            dp = {r: x[idx[("dp", r)]] for r in REGIONS}
            mkt = {
                "camera": {r: {c: x[idx[("cm", r, c)]]
                               for c in MKT_CHANNELS["camera"]}
                           for r in REGIONS},
                "drone": {r: {c: x[idx[("dm", r, c)]]
                              for c in MKT_CHANNELS["drone"]}
                          for r in REGIONS},
            }
            prof, Sc, Sd = model.profit(cp, dp, mkt, promo, x[idx["disc"]])
            img = model.image(Sc, Sd)
            penalty = 0.0 if img >= 80 else (80 - img) * 20000.0
            return -prof + penalty

        best = None
        for d0 in (0.03, 0.05, 0.08):
            xs = list(x0); xs[idx["disc"]] = d0
            res = minimize(f, xs, method="L-BFGS-B", bounds=bounds,
                           options={"maxiter": 500})
            if best is None or res.fun < best.fun:
                best = res
        results[promo] = (best, idx)
    return results

def main():
    model = Model()
    validate(model)
    print("\n== Optimizing ==")
    res = optimize(model)
    out = []
    w = out.append
    w("# Y7 full optimization (price + marketing + promo + discount)\n")
    for promo in (0, 1):
        best, _ = res[promo]
        w(f"Promo={promo}: objective {-best.fun:.0f}k")
    best_promo = min((0, 1), key=lambda p: res[p][0].fun)
    w(f"\nBest camera promo: {best_promo} week(s)\n")
    best, idx = res[best_promo]
    x = best.x
    cam_p = {r: x[idx[("cp", r)]] for r in REGIONS}
    drn_p = {r: x[idx[("dp", r)]] for r in REGIONS}
    cam_mkt = {r: {c: x[idx[("cm", r, c)]] for c in MKT_CHANNELS["camera"]}
               for r in REGIONS}
    drn_mkt = {r: {c: x[idx[("dm", r, c)]] for c in MKT_CHANNELS["drone"]}
               for r in REGIONS}
    disc = x[idx["disc"]]
    mkt = {"camera": cam_mkt, "drone": drn_mkt}
    prof, Sc, Sd = model.profit(cam_p, drn_p, mkt, best_promo, disc)
    img = model.image(Sc, Sd)
    w("## Optimal decisions\n")
    w("| region | cam price | cam support | cam adv | cam web | drn price | drn search | drn web |")
    w("|---|---|---|---|---|---|---|---|")
    for r in REGIONS:
        w(f"| {r} | ${cam_p[r]:.0f} | ${cam_mkt[r]['retailer_support']:.0f}k | "
          f"${cam_mkt[r]['advertising']:.0f}k | ${cam_mkt[r]['website']:.0f}k | "
          f"${drn_p[r]:.0f} | ${drn_mkt[r]['search_ads']:.0f}k | "
          f"${drn_mkt[r]['website']:.0f}k |")
    w(f"\n- Camera promo weeks: {best_promo}")
    w(f"- Drone 3rd-party discount: {disc*100:.2f}%")
    w(f"\n## Predicted outcomes\n")
    w(f"- Net profit: ${prof:.0f}k (baseline $74,108k)")
    w(f"- EPS: ${prof/19800:.2f}")
    w(f"- Image rating: {img} (baseline 85)")
    w(f"- Camera units: {sum(Sc.values()):.1f}k; Drone units: {sum(Sd.values()):.1f}k")
    md = "\n".join(out)
    print("\n" + md)
    with open(os.path.join(HERE, "optimization_results.md"), "w") as f:
        f.write(md)

if __name__ == "__main__":
    main()
