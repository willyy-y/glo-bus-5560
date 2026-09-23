#!/usr/bin/env python3
"""
Calibrate the engine's unknown scenario scales from projection-box sensor
observations.

The game's additive demand terms are  table_value * AP * AN_weight * Q.
AN weights are known (extracted); AP and Q arrive with the server scenario
payload, so only their PRODUCT per term-group is identifiable. This script
solves for per-group scales via linear least squares:

    observed_units = sum_g s_g * X_g

where X_g is the engine's raw unit contribution of group g (computed by
finite difference with all scales = 1). Groups:

  camera: pq | war | rest   (rest = support/ad/web/outlets/promo)
  drone:  pq | war | rest

Observations come from read-only sensor experiments on the live projection
box (see README). Only BELOW-CAP observations are usable (the box caps
reported units at production).

Usage:
  python calibrate.py observations.json   # writes cases/y7_calibrated.json
"""

import copy
import json
import sys

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from engine import DemandEngine, REGIONS
from rivals import make_rivals, industry_averages

GROUPS_CAM = ["pq", "war", "rest"]
GROUPS_DRONE = ["pq", "war", "rest"]

TABLE_TO_GROUP = {
    "demand_pq": "pq",
    "demand_warranty": "war",
}


def group_of(table, groups=None):
    g = TABLE_TO_GROUP.get(table, "rest")
    if groups is not None and g not in groups:
        return "rest"
    return g


def region_bases(bcase, product, region, obs):
    """Return (B_pq, B_other) raw additive contributions with all scales=1,
    and the multiplicative P*M*I for one region."""
    from engine import DemandEngine, REGIONS
    eng0 = DemandEngine()
    terms, promo, mults = eng0._segments[(product, region)]
    own = bcase["own"][product][region]
    avg = bcase["avg"][product][region] if "avg" in bcase else {}
    image = bcase.get("image", 85)
    groups = obs["groups"][product]
    b_pq, b_other = 0.0, 0.0
    for table, kind, ap_name, an_w, q_name in terms:
        x = eng0._term_input(kind, own, avg)
        v = eng0.vlookup(x, eng0.tables[table])
        contrib = v * an_w  # AP=Q=1
        if group_of(table, groups) == "pq":
            b_pq += contrib
        else:
            b_other += contrib
    if promo is not None:
        ptable, pkind, pap, pan_w, pq_ = promo
        pw = eng0.vlookup(own.get("prom_weeks", 0), eng0.tables["demand_promweeks"])
        pd = eng0.vlookup(own.get("prom_disc", 0), eng0.tables["demand_promdisc"])
        b_other += pw * pd * pan_w
    # multiplicative part
    r = REGIONS.index(region)
    avg_price = avg.get("price", 0)
    ratio = 1.0 if avg_price == 0 else own["price"] / avg_price
    pm = eng0.vlookup(ratio, eng0.tables["demand_price"])
    ap_p, an_p, q_p = mults["price_adj"]
    adj = an_p  # AP=Q=1
    pm *= adj if own["price"] <= avg_price or avg_price == 0 else 1.0 / adj
    mm = eng0.vlookup(own["models"], eng0.tables["demand_models"])
    an_m, q_m = mults["models_adj"]
    madj = an_m
    avg_models = avg.get("models", own["models"])
    mm *= madj if own["models"] >= avg_models else 1.0 / madj
    im = eng0.vlookup(image, eng0.tables["demand_rep_image"]) * mults["image_w"]
    return b_pq, b_other, pm * mm * im


def solve(obs):
    """obs: {"base": case_dict, "runs": [ {"product":, "changes": {...},
           "units": observed}, ... ], "groups": {"camera": [...], "drone": [...]}}"""
    base = obs["base"]
    groups = obs["groups"]
    results = {}
    for product in ("camera", "drone"):
        glist = groups[product]
        if not glist:
            continue
        # Build A (n_obs x n_groups), b via finite differences.
        A, b = [], []
        runs = [r for r in obs["runs"] if r["product"] == product]
        # start from all-ones scales
        s0 = {p: {g: 1.0 for g in groups[p]} for p in groups}
        # Linearize around s0 = 1: U(s) ~= u0 + sum_g (s_g - 1) * X_g.
        # Solve A * delta = (U_obs - u0), then s = 1 + delta.
        for run in runs:
            bcase = copy.deepcopy(base)
            for target, val in run["changes"].items():
                if target == "image":
                    bcase["image"] = val
                    continue
                prod2, region, field = target.split(".")
                bcase["own"][prod2][region][field] = val
            u0 = demand_with_scales_for(bcase, s0, product, obs)
            row = []
            for g in glist:
                s1 = copy.deepcopy(s0)
                s1[product][g] = 1.0 + 1e-4
                u1 = demand_with_scales_for(bcase, s1, product, obs)
                row.append((u1 - u0) / 1e-4)
            A.append(row)
            b.append(run["units"] - u0)
        # least squares via normal equations
        n = len(glist)
        import math
        # A^T A x = A^T b
        ATA = [[sum(A[k][i] * A[k][j] for k in range(len(A))) for j in range(n)] for i in range(n)]
        ATb = [sum(A[k][i] * b[k] for k in range(len(A))) for i in range(n)]
        x = _solve_linear(ATA, ATb)
        results[product] = {g: 1.0 + x[i] for i, g in enumerate(glist)}
    return results


def demand_with_scales_for(bcase, group_scales, product, obs):
    scales = {}
    eng0 = DemandEngine()
    glist_all = obs["groups"]
    for prod in ("camera", "drone"):
        for r in range(4):
            terms, _promo, _ = eng0._segments[(prod, REGIONS[r])]
            for table, _kind, _ap, _an, q_name in terms:
                scales[q_name] = group_scales[prod][group_of(table, glist_all[prod])]
    eng = DemandEngine(scales=scales)
    own = bcase["own"]
    if "avg" in bcase:
        avg = bcase["avg"]
    else:
        scen = bcase.get("rival_scenario", obs.get("rival_scenario", "flat"))
        avg = industry_averages(own, make_rivals(scen))
    d = eng.demand(own, avg, bcase.get("image", 85), doround=False)
    return d["totals"][product]


def _solve_linear(A, b):
    n = len(A)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(M[r][col]))
        M[col], M[piv] = M[piv], M[col]
        pv = M[col][col]
        if abs(pv) < 1e-12:
            continue
        for r in range(n):
            if r != col and M[r][col] != 0:
                f = M[r][col] / pv
                for c in range(col, n + 1):
                    M[r][c] -= f * M[col][c]
    return [M[i][n] / M[i][i] if abs(M[i][i]) > 1e-12 else 0.0 for i in range(n)]


def main():
    obs = json.load(open(sys.argv[1]))
    sol = solve(obs)
    print(json.dumps(sol, indent=1))
    # write calibrated case
    base = copy.deepcopy(obs["base"])
    eng0 = DemandEngine()
    scales = {}
    for product, gs in sol.items():
        for r in range(4):
            terms, _promo, _ = eng0._segments[(product, REGIONS[r])]
            for table, _k, _ap, _an, q_name in terms:
                scales[q_name] = gs[group_of(table, obs["groups"][product])]
    base.setdefault("engine", {})["scales"] = scales
    base["unit_scale"] = 1.0
    out = sys.argv[2] if len(sys.argv) > 2 else "cases/y7_calibrated.json"
    json.dump(base, open(out, "w"), indent=1)
    print("wrote", out)


if __name__ == "__main__":
    main()
