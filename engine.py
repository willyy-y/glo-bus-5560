"""
GLO-BUS demand engine — faithful replica of the client-side projection model.

Reverse-engineered from the GLO-BUS Student Decisions & Reports Program
(v6.22.1) JavaScript bundle. The projection engine computes, per company
column, per region, per product:

    units = max(0, round( (sum of additive terms) * price_mult * models_mult * image_mult ))

Additive terms are VLOOKUPs into the game's demand_* tables, each scaled by
regional factors:  table_value * AP_factor * AN_weight * Q_factor.

Known game constants (AN_* weights) are baked in below, extracted verbatim
from the bundle. Unknown scenario constants (AP_* regional factors and
Costs.Q* factors, which arrive with the server scenario payload) default to
1.0 and can be overridden via the `scales` argument; the per-product
`cal` multiplier absorbs any residual level mismatch. See README.md.

VLOOKUP semantics replicate the game's e.VLookup exactly: lookup key is
truncated toward zero to 9 decimals, tables are ascending approximate-match
(first row's value returned below the first key, last row's value above the
last key, exact match on equality after truncation).

Units returned are raw formula units. The caller applies capacity caps and
converts to the box's display scale.
"""

import json
import math
import os

SPEC_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model_spec.json")

REGIONS = ["NA", "EA", "AP", "LA"]

# ----------------------------------------------------------------------------
# Segment specifications.
# Each additive term: (table_name, input_kind, ap_name, an_weight, q_name)
#   input_kind: "pq" | "warranty" | "ratio:<field>" | "diff:<field>" | "uavdisc"
# The AN weights below are the game's own constants (AN4xx/AN5xx), extracted
# verbatim from the bundle. AP_* and Q* default to 1.0 (unknown scenario
# payload values) unless overridden in `scales`.
# ----------------------------------------------------------------------------

def _cam_terms(r):
    ap = {
        "pq":      ["AP276", "AP292", "AP308", "AP324"][r],
        "support": ["AP278", "AP294", "AP310", "AP326"][r],
        "ad":      ["AP279", "AP295", "AP311", "AP327"][r],
        "web":     ["AP280", "AP296", "AP312", "AP328"][r],
        "warranty":["AP283", "AP299", "AP315", "AP331"][r],
        "chains":  ["AP284", "AP300", "AP316", "AP332"][r],
        "online":  ["AP285", "AP301", "AP317", "AP333"][r],
        "local":   ["AP286", "AP302", "AP318", "AP334"][r],
        "promw":   ["AP281", "AP297", "AP313", "AP329"][r],
    }
    q = {
        "pq":      ["Q4", "Q15", "Q26", "Q37"][r],
        "support": ["Q7", "Q18", "Q29", "Q40"][r],
        "ad":      ["Q8", "Q19", "Q30", "Q41"][r],
        "web":     ["Q9", "Q20", "Q31", "Q42"][r],
        "warranty":["Q11", "Q22", "Q33", "Q44"][r],
        "outlets": ["Q12", "Q23", "Q34", "Q45"][r],
        "promo":   "Q10",
    }
    an = {
        "pq":       [1.6, 1.6, 1.4, 1.4][r],
        "support":  0.5,
        "ad":       0.85,
        "web":      0.5,
        "warranty": 1.3,
        "chains":   1.0,
        "online":   0.6,
        "local":    0.4,
        "promw":    1.0,   # AN417/AN441/AN465/AN489
    }
    return [
        ("demand_pq",         "pq",              ap["pq"],      an["pq"],       q["pq"]),
        ("demand_support",    "ratio:support",   ap["support"], an["support"],  q["support"]),
        ("demand_advertising","ratio:ad",        ap["ad"],      an["ad"],       q["ad"]),
        ("demand_website",    "ratio:web",       ap["web"],     an["web"],      q["web"]),
        ("demand_warranty",   "warranty",        ap["warranty"],an["warranty"],  q["warranty"]),
        ("demand_chains",     "diff:chains",     ap["chains"],  an["chains"],   q["outlets"]),
        ("demand_online",     "diff:online",     ap["online"],  an["online"],   q["outlets"]),
        ("demand_local",      "diff:local",      ap["local"],   an["local"],    q["outlets"]),
    ], ("demand_promweeks", "promw", ap["promw"], an["promw"], q["promo"]), {
        "price_adj":  (["AP275", "AP291", "AP307", "AP323"][r],  # =1.0 in bundle
                       [1.05, 1.05, 1.10, 1.10][r],
                       ["Q3", "Q14", "Q25", "Q36"][r]),
        "models_adj": ([1.0, 1.0, 1.0, 1.0][r],                 # AN420/AN444/AN468/AN492
                       ["Q6", "Q17", "Q28", "Q39"][r]),
        "image_w":    1.0,  # AN421/AN445/AN469/AN493
    }

def _drone_terms(r):
    ap = {
        "pq":      ["AP344", "AP357", "AP370", "AP383"][r],
        "web":     ["AP346", "AP359", "AP372", "AP385"][r],
        "ad":      ["AP347", "AP360", "AP373", "AP386"][r],
        "support": ["AP348", "AP361", "AP374", "AP387"][r],
        "warranty":["AP349", "AP362", "AP375", "AP388"][r],
        "online":  ["AP350", "AP363", "AP376", "AP389"][r],
    }
    q = {
        "uavdisc": ["Q53", "Q64", "Q75", "Q86"][r],
        "pq":      ["Q54", "Q65", "Q76", "Q87"][r],
        "web":     ["Q57", "Q68", "Q79", "Q90"][r],
        "ad":      ["Q58", "Q69", "Q80", "Q91"][r],
        "support": ["Q59", "Q70", "Q81", "Q92"][r],
        "warranty":["Q60", "Q71", "Q82", "Q93"][r],
        "online":  ["Q61", "Q72", "Q83", "Q94"][r],
    }
    an = {
        "uavdisc": 0.4081634,  # AN508/AN527/AN546/AN565
        "pq":      [1.65, 1.65, 1.45, 1.45][r],
        "web":     0.5,
        "ad":      0.85,
        "support": 0.5,
        "warranty":1.3,
        "online":  1.0,
    }
    return [
        ("demand_uavdiscount","uavdisc",         None,          an["uavdisc"],  q["uavdisc"]),
        ("demand_pq",         "pq",              ap["pq"],      an["pq"],       q["pq"]),
        ("demand_website",    "ratio:web",       ap["web"],     an["web"],       q["web"]),
        ("demand_advertising","ratio:ad",        ap["ad"],      an["ad"],       q["ad"]),
        ("demand_support",    "ratio:support",   ap["support"], an["support"],  q["support"]),
        ("demand_warranty",   "warranty",        ap["warranty"],an["warranty"],  q["warranty"]),
        ("demand_online",     "diff:online",     ap["online"],  an["online"],   q["online"]),
    ], None, {
        "price_adj":  (["AP342", "AP355", "AP368", "AP381"][r],  # =1.0 in bundle
                       [1.05, 1.05, 1.10, 1.10][r],
                       ["Q52", "Q63", "Q74", "Q85"][r]),
        "models_adj": ([1.0, 1.0, 1.0, 1.0][r],
                       ["Q56", "Q67", "Q78", "Q89"][r]),
        "image_w":    1.0,
    }


class DemandEngine:
    """Client-side GLO-BUS demand replica."""

    def __init__(self, scales=None, cal=None, regional_cal=None):
        """
        scales: dict overriding unknown scenario constants, e.g.
                {"Q4": 12.4, "AP276": 1.0}. Defaults: every unknown = 1.0.
        cal:    dict {"camera": s, "drone": s} global per-product level
                multipliers. Default 1.0.
        regional_cal: dict {"camera": {"NA": c, ...}, "drone": {...}}
                per-region market-size multipliers. Default 1.0.
        """
        with open(SPEC_PATH) as f:
            spec = json.load(f)
        self.tables = spec["tables"]
        self.scales = scales or {}
        self.cal = {"camera": 1.0, "drone": 1.0}
        if cal:
            self.cal.update(cal)
        self.regional_cal = regional_cal or {}
        self._segments = {}
        for r in range(4):
            terms, promo, mults = _cam_terms(r)
            self._segments[("camera", REGIONS[r])] = (terms, promo, mults)
            terms, promo, mults = _drone_terms(r)
            self._segments[("drone", REGIONS[r])] = (terms, promo, mults)

    # -- VLOOKUP (exact replica of the game's e.VLookup) ---------------------
    @staticmethod
    def vlookup(x, table):
        if x is None:
            x = 0
        neg = x < 0
        x = math.floor(abs(x) * 1e9) / 1e9
        if neg:
            x = -x
        t = table[0][1] if table else 0
        for key, val in table:
            if x < key:
                return t
            if x == key:
                return val
            t = val
        return t

    def _s(self, name, default=1.0):
        return self.scales.get(name, default)

    def _term_input(self, kind, own, avg):
        if kind == "pq":
            return own["pq"]
        if kind == "warranty":
            return own["warranty_days"]
        if kind == "uavdisc":
            return own.get("uav_disc", 0)
        if kind.startswith("ratio:"):
            f = kind.split(":")[1]
            a = avg.get(f, 0)
            if a == 0:
                return 0
            return own.get(f, 0) / a
        if kind.startswith("diff:"):
            f = kind.split(":")[1]
            return own.get(f, 0) - avg.get(f, 0)
        raise ValueError(kind)

    def region_units(self, product, region, own, avg, image, doround=True):
        """
        own: dict with price, pq (0-100 score), warranty_days, models,
             ad, support, web, chains, online, local,
             prom_weeks, prom_disc, uav_disc (drones)
        avg: dict with price, ad, support, web, chains, online, local, models
        image: our image rating (0-100)
        Returns raw formula units (float, uncapped). doround=False skips the
        game's per-region integer rounding (for calibration math).
        """
        r = REGIONS.index(region)
        terms, promo, mults = self._segments[(product, region)]

        add = 0.0
        for table, kind, ap_name, an_w, q_name in terms:
            x = self._term_input(kind, own, avg)
            v = self.vlookup(x, self.tables[table])
            add += v * self._s(ap_name) * an_w * self._s(q_name)

        if promo is not None:
            ptable, pkind, pap, pan_w, pq_ = promo
            pw = self.vlookup(own.get("prom_weeks", 0), self.tables["demand_promweeks"])
            pd = self.vlookup(own.get("prom_disc", 0), self.tables["demand_promdisc"])
            add += pw * self._s(pap) * pd * pan_w * self._s(pq_)

        # price multiplier with below/above-average ternary
        avg_price = avg.get("price", 0)
        ratio = 1.0 if avg_price == 0 else own["price"] / avg_price
        pm = self.vlookup(ratio, self.tables["demand_price"])
        ap_p, an_p, q_p = mults["price_adj"]
        adj = self._s(ap_p) * an_p * self._s(q_p)
        pm *= adj if own["price"] <= avg_price or avg_price == 0 else 1.0 / adj

        # models multiplier with ternary
        mm = self.vlookup(own["models"], self.tables["demand_models"])
        an_m, q_m = mults["models_adj"]
        madj = an_m * self._s(q_m)
        avg_models = avg.get("models", own["models"])
        mm *= madj if own["models"] >= avg_models else 1.0 / madj

        # image multiplier
        im = self.vlookup(image, self.tables["demand_rep_image"]) * mults["image_w"]

        raw = add * pm * mm * im
        units = max(0.0, math.floor(raw + 0.5) if doround else raw)
        return units

    def demand(self, own, avg, image, doround=True):
        """
        own/avg: {"camera": {region: {...}}, "drone": {region: {...}}}
        Returns {"camera": {region: units}, "drone": {region: units},
                 "totals": {"camera": u, "drone": u}}.
        Camera retailer support is entered as a BUDGET but the formula uses
        $/unit = budget / units, so we iterate a few times to a fixed point.
        Pass "support_budget" ($000s) in own["camera"][region] to enable;
        otherwise "support" is used as-is.
        """
        out = {"camera": {}, "drone": {}}
        for product in ("camera", "drone"):
            wown = {r: dict(own[product][r]) for r in REGIONS}
            rc = self.regional_cal.get(product, {})
            for _ in range(4):
                for region in REGIONS:
                    u = self.region_units(
                        product, region, wown[region], avg[product][region],
                        image, doround=doround)
                    out[product][region] = u * rc.get(region, 1.0) * self.cal[product]
                moved = False
                for region in REGIONS:
                    b = wown[region].get("support_budget")
                    u = out[product][region]
                    if b and u > 0:
                        # cameras: $/unit on all units; drones: $/3rd-party unit
                        # via third_party_share (fraction of units sold 3rd-party)
                        share = wown[region].get("third_party_share", 1.0)
                        new = b * 1000.0 / (u * share)
                        if abs(new - wown[region].get("support", new)) > 1e-9:
                            moved = True
                        wown[region]["support"] = new
                if not moved:
                    break
        out["totals"] = {p: sum(out[p].values()) for p in ("camera", "drone")}
        return out
