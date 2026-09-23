"""
Dummy competitors for GLO-BUS test runs.

Builds 8 rival companies from last year's scored actuals, then applies a
scenario. industry_averages() returns the 9-firm averages (8 rivals + us)
that fill the game's competitive-assumption (AM) cells:

    avg9 = (sum of 8 rivals + our value) / 9

Fields averaged: price, ad, support, web, chains, online, local, models.
P/Q, warranty, image are absolute in the model (not averaged).
"""

import copy
import random

REGIONS = ["NA", "EA", "AP", "LA"]

# Scored Y6 actuals (Industry 18, read 2026-09-23). These are the industry
# averages including us (Company E).
Y6 = {
    "camera": {
        "NA": {"price": 259, "pq": 45, "warranty": 180, "models": 2},
        "EA": {"price": 266, "pq": 45, "warranty": 180, "models": 2},
        "AP": {"price": 257, "pq": 45, "warranty": 180, "models": 2},
        "LA": {"price": 254, "pq": 45, "warranty": 180, "models": 2},
    },
    "drone": {
        "NA": {"price": 1530, "pq": 47, "warranty": 180, "models": 2},
        "EA": {"price": 1485, "pq": 47, "warranty": 180, "models": 2},
        "AP": {"price": 1560, "pq": 47, "warranty": 180, "models": 2},
        "LA": {"price": 1497, "pq": 47, "warranty": 180, "models": 2},
    },
}

# Our scored Y6 decisions (needed to back out the 8-rival sum from the
# 9-firm average: sum8 = avg9*9 - own).
OUR_Y6 = {
    "camera": {
        "NA": {"price": 243, "pq": 47, "warranty": 180, "models": 2},
        "EA": {"price": 248, "pq": 47, "warranty": 180, "models": 2},
        "AP": {"price": 235, "pq": 47, "warranty": 180, "models": 2},
        "LA": {"price": 235, "pq": 47, "warranty": 180, "models": 2},
    },
    "drone": {
        "NA": {"price": 1190, "pq": 42, "warranty": 180, "models": 2},
        "EA": {"price": 1190, "pq": 42, "warranty": 180, "models": 2},
        "AP": {"price": 1145, "pq": 42, "warranty": 180, "models": 2},
        "LA": {"price": 1145, "pq": 42, "warranty": 180, "models": 2},
    },
}

AVG_FIELDS = ["price", "ad", "support", "web", "chains", "online", "local", "models"]


def _base_rival():
    """One rival at the implied Y6 8-rival average (before scenario)."""
    rival = {"camera": {}, "drone": {}}
    for product in ("camera", "drone"):
        for region in REGIONS:
            cell = {}
            for f in AVG_FIELDS:
                if f in Y6[product][region]:
                    cell[f] = Y6[product][region][f] * 9 - OUR_Y6[product][region].get(f, 0)
                    cell[f] /= 8.0
                else:
                    cell[f] = 0.0  # marketing spends: unknown -> set via scenario
            # absolute fields
            for f in ("pq", "warranty"):
                cell[f] = (Y6[product][region][f] * 9 - OUR_Y6[product][region][f]) / 8.0
            rival[product][region] = cell
    return rival


def make_rivals(scenario="escalate", seed=7, n=8):
    """
    scenario:
      flat      - rivals repeat Y6 (marketing ratios stay 1.0 vs ours)
      escalate  - prices +7.6%/yr (camera), +7.6% (drone); pq +1.5 pts;
                  marketing spends +7%  (the default: field keeps escalating)
      aggressive- prices -3%, pq +2 pts, marketing +12%
      mixed     - half escalate, half aggressive
    Returns list of n rival dicts: {"camera": {region: {...}}, "drone": {...}}.
    Marketing fields (ad/support/web/chains/online/local) are expressed as
    RATIOS to our spend (1.0 = matches us). uav_disc in percent points.
    """
    rng = random.Random(seed)
    rivals = []
    for i in range(n):
        r = _base_rival()
        mode = scenario
        if scenario == "mixed":
            mode = "escalate" if i % 2 == 0 else "aggressive"
        for product in ("camera", "drone"):
            for region in REGIONS:
                c = r[product][region]
                jitter = lambda s: 1 + rng.uniform(-s, s)
                if mode == "flat":
                    pass
                elif mode == "escalate":
                    c["price"] *= 1.076 * jitter(0.01)
                    c["pq"] += 1.5 * jitter(0.3)
                    for f in ("ad", "support", "web", "chains", "online", "local"):
                        c[f] = 1.07 * jitter(0.05)
                elif mode == "aggressive":
                    c["price"] *= 0.97 * jitter(0.01)
                    c["pq"] += 2.0 * jitter(0.3)
                    for f in ("ad", "support", "web", "chains", "online", "local"):
                        c[f] = 1.12 * jitter(0.05)
                c["warranty"] = 180
                c["models"] = round(c["models"])
                c["uav_disc"] = 0.0
        rivals.append(r)
    return rivals


def industry_averages(own, rivals):
    """
    own: {"camera": {region: {...}}, "drone": {region: {...}}} with ABSOLUTE
         spends. Rival marketing fields are ratios to our spend.
    Returns avg dicts with the same shape, 9-firm averages for AVG_FIELDS.
    """
    avg = {"camera": {}, "drone": {}}
    for product in ("camera", "drone"):
        for region in REGIONS:
            cell = {}
            for f in AVG_FIELDS:
                if f in ("ad", "support", "web", "chains", "online", "local"):
                    # rivals hold ratios to OUR spend
                    total = own[product][region].get(f, 0)
                    total += sum(r[product][region][f] * own[product][region].get(f, 0)
                                 for r in rivals)
                    cell[f] = total / 9.0
                else:
                    total = own[product][region].get(f, 0) + sum(r[product][region][f] for r in rivals)
                    cell[f] = total / 9.0
            avg[product][region] = cell
    return avg
