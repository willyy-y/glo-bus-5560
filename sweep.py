#!/usr/bin/env python3
"""
Test-run CLI for the GLO-BUS demand engine.

Usage:
  python sweep.py                                   # base case only
  python sweep.py --scenario escalate                # rival scenario
  python sweep.py --vary camera.NA.price 243 263 5   # sweep one lever
  python sweep.py --vary drone.NA.price 1190 1390 50 --scenario aggressive
  python sweep.py --dump                            # show base case

Vary target syntax:  <product>.<region>.<field>
  fields: price, pq (0-100 score), warranty_days, models, ad, support,
          web, chains, online, local, prom_weeks, prom_disc, uav_disc, image

Capacity: units sold = min(demand, production) per product.
"""

import argparse
import copy
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import DemandEngine
from rivals import make_rivals, industry_averages
from pnl import pnl, calibrate_fixed

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cases", "y7_calibrated.json")
REGIONS = ["NA", "EA", "AP", "LA"]


def load_base(path=None):
    with open(path or BASE) as f:
        return json.load(f)


def run_case(base, eng_cfg, rival_scenario, seed):
    eng = DemandEngine(scales=eng_cfg.get("scales"), cal=eng_cfg.get("cal"),
                       regional_cal=eng_cfg.get("regional_cal"))
    own = base["own"]
    if "avg" in base and rival_scenario == "assumptions":
        import copy as _copy
        avg = _copy.deepcopy(base["avg"])
        # dynamic 9-firm avg for price: (own + 8*rival)/9, we are 1 of 9
        ra = base.get("rival_avg", {})
        for p in ("camera", "drone"):
            for r in REGIONS:
                rv = ra.get(p, {}).get(r)
                if rv:
                    avg[p][r]["price"] = (own[p][r]["price"] + 8.0 * rv) / 9.0
    else:
        rivals = make_rivals(rival_scenario, seed=seed)
        avg = industry_averages(own, rivals)
    units = eng.demand(own, avg, base.get("image", 85))
    # capacity: sales = min(demand, production); both in real units
    sold = {"camera": {}, "drone": {}}
    for p in ("camera", "drone"):
        cap = base["production"][p]
        total_real = units["totals"][p]
        scale = min(1.0, cap / total_real) if total_real > 0 else 1.0
        for r in REGIONS:
            sold[p][r] = units[p][r] * scale
    res = pnl(sold, own, base["unit_cost"], base["fixed"], base["shares"],
              base.get("tax_rate", 0.30))
    res["demand_raw"] = units["totals"]
    res["rival_scenario"] = rival_scenario
    return res


def fmt_money(x):
    return f"${x/1e6:,.1f}M"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="assumptions",
                    choices=["assumptions", "flat", "escalate", "aggressive", "mixed"],
                    help="assumptions=use Y7 competitive-assumption avgs (calibrated); "
                         "others=synthetic 8-rival scenarios")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--vary", nargs=4, metavar=("TARGET", "START", "STOP", "STEP"))
    ap.add_argument("--dump", action="store_true")
    ap.add_argument("--case", default=None,
                    help="case JSON path (default: cases/y7_base.json)")
    args = ap.parse_args()

    base = load_base(args.case)
    if args.dump:
        print(json.dumps(base, indent=1))
        return

    eng_cfg = base.get("engine", {})

    def one(mod):
        b = copy.deepcopy(base)
        if mod:
            (product, region, field), val = mod
            if field == "image":
                b["image"] = val
            else:
                b["own"][product][region][field] = val
        return run_case(b, eng_cfg, args.scenario, args.seed)

    if args.vary:
        target, s0, s1, st = args.vary
        product, region, field = target.split(".")
        v, end, step = float(s0), float(s1), float(st)
        print(f"sweep {target}  rivals={args.scenario}")
        print(f"{'value':>8} {'cam_k':>8} {'drn_k':>8} {'revenue':>10} "
              f"{'contrib':>10} {'net':>10} {'eps':>7}")
        vcur = v
        while vcur <= end + 1e-9:
            r = one(((product, region, field), vcur))
            print(f"{vcur:>8.1f} {r['units_cam']/1000:>8.1f} "
                  f"{r['units_drone']/1000:>8.1f} {fmt_money(r['revenue']):>10} "
                  f"{fmt_money(r['contribution']):>10} {fmt_money(r['net_profit']):>10} "
                  f"{r['eps']:>7.2f}")
            vcur += step
    else:
        r = one(None)
        print(f"base case  rivals={args.scenario}")
        print(f"  demand raw: cam={r['demand_raw']['camera']:,.0f} "
              f"drone={r['demand_raw']['drone']:,.0f}")
        print(f"  sold: cam={r['units_cam']/1000:,.1f}k "
              f"drone={r['units_drone']/1000:,.1f}k")
        print(f"  revenue={fmt_money(r['revenue'])} "
              f"contrib={fmt_money(r['contribution'])} "
              f"net={fmt_money(r['net_profit'])} eps={r['eps']:.2f}")


if __name__ == "__main__":
    main()
