"""
GLO-BUS unit-cost model — exact client-side replica.

Reverse-engineered 2026-09-24 from the GLO-BUS 6.22.1 bundle.
See research/unit_cost_report.md for the full derivation.

Covers:
  - Component costs: 16 costs_* tables keyed on design dropdown ids
    (exact, in cost_tables.json), with the experience-curve ("reduce")
    multipliers keyed on cumulative R&D — including the two known bundle
    quirks: utility-features cost gets reduce SQUARED, and housing /
    editing / accessories $ have NO reduce.
  - Drone embeds a whole camera unit cost (AB513 = upgrade $ x reduce +
    camera $/unit).
  - Warranty claim rates per region: base rate by warranty-days id +
    P/Q adder, x training multiplier x incentive multiplier, clamped
    (exact tables embedded below). Repair $/unit is a server constant
    (G18/G19) — calibratable.
  - Delivery: flat shipping $/unit (G26/G27, design-independent) +
    ad-valorem import duty % on regional revenue (G30-G37).
  - Labor chain implemented; PAT-productivity tables were not in the
    bundle extract, so productivity effects (#models etc.) run through a
    calibratable multiplier (default 1.0).
  - Maintenance / depreciation / plant expansion are treated as fixed
    allocs (calibrated), not per-design.

Server constants (Costs.G<n>) are NOT in the bundle. They live in the
`constants` dict with defaults estimated from Y6 actuals, each flagged
for live read-only calibration. MARGINAL design costs (the $/unit delta
of changing a component) are exact regardless of the constants.
"""

import json
import math
import os

TABLES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "cost_tables.json")

with open(TABLES_PATH) as f:
    _T = json.load(f)

from engine import DemandEngine

_vlookup = DemandEngine.vlookup


# ----------------------------------------------------------------------------
# Warranty tables (verbatim from bundle; see research/unit_cost_report.md §5)
# ----------------------------------------------------------------------------
WARRANTY_DAYS = [[0, 0], [1, 60], [2, 90], [3, 120], [4, 180], [5, 360]]
WARRANTY_ACC_PERIOD = [[0, 0], [1, .03], [2, .065], [3, .105], [4, .16], [5, .38]]
WARRANTY_UAV_PERIOD = [[0, 0], [1, .035], [2, .075], [3, .12], [4, .2], [5, .455]]
WARRANTY_PQ = [[0, .27], [3, .24], [7, .215], [10, .19], [13, .165], [16, .14],
               [19, .12], [22, .1], [25, .085], [28, .07], [31, .06], [34, .05],
               [37, .045], [40, .04], [45, .0375], [50, .0345], [55, .0315],
               [60, .028], [65, .0245], [70, .021], [75, .0185], [80, .016],
               [85, .014], [90, .0125], [95, .011], [100, .01]]
WARRANTY_INCENTIVE_ACC = [[0, 1.5], [1.2, 1.32], [1.6, 1.18], [2, 1.07],
                          [2.4, 1], [3, .98], [3.6, .96], [4.2, .94],
                          [4.8, .92], [5.4, .9], [6, .88], [7, .86], [8, .84],
                          [9, .82], [10, .8], [12, .78], [14, .76], [16, .74],
                          [18, .72], [20, .7], [22.5, .68], [25, .66],
                          [27.5, .64], [30, .62], [32.5, .61], [35, .6]]
WARRANTY_INCENTIVE_UAV = [[0, 1.5], [1.2, 1.32], [2.4, 1.18], [3.6, 1.07],
                          [4.8, 1], [6, .985], [8, .97], [10, .95],
                          [12.5, .93], [15, .91], [17.5, .89], [20, .87],
                          [22.5, .85], [25, .83], [30, .8], [35, .77],
                          [40, .74], [45, .71], [50, .69], [60, .67],
                          [70, .655], [80, .64], [90, .625], [100, .61],
                          [125, .595], [150, .58]]
WARRANTY_BESTPRACTICES = [[0, 1.5], [250, 1.32], [500, 1.18], [750, 1.07],
                          [1000, 1], [1250, .995], [1500, .99], [1750, .985],
                          [2000, .978], [2500, .97], [3000, .962], [3500, .954],
                          [4000, .946], [4500, .939], [5000, .932],
                          [5500, .925], [6000, .919], [6500, .913],
                          [7000, .907], [7500, .902], [8000, .897],
                          [8500, .893], [9000, .89], [9500, .888]]

# Server constants: (default, basis). Defaults estimated from Y6 actuals;
# replace with live read-only calibration values when available.
DEFAULT_CONSTANTS = {
    # repair $/unit: Y6 camera warranty ~$9/unit at ~19.8% claim rate
    "G18": (45.0, "est: 9/0.1975 from Y6 actuals"),
    # Y6 drone warranty ~$66/unit at ~24% claim rate
    "G19": (275.0, "est: 66/0.24 from Y6 actuals"),
    # shipping $/unit (flat, design-independent)
    "G26": (8.0, "est: camera delivery ~$13 = ship + duty"),
    "G27": (40.0, "est: drone delivery ~$60 = ship + duty"),
    # import duty % by region (ad valorem on revenue)
    "G30": (2.0, "est"), "G31": (2.0, "est"),
    "G32": (2.0, "est"), "G33": (2.0, "est"),
    "G34": (2.0, "est"), "G35": (2.0, "est"),
    "G36": (2.0, "est"), "G37": (2.0, "est"),
    # labor/productivity calibration (PAT productivity tables not extracted)
    "productivity_mult": (1.0, "calibrate: #models effect on labor"),
    # fixed per-unit allocs (labor + R&D spread + maintenance + depreciation),
    # solved so baseline production $/unit hits Y6 actuals:
    # camera 155 - 77.45 components = 77.55; drone 776 - 529 = 247
    "camera_fixed_per_unit": (77.55, "solved from Y6 actuals; refine live"),
    "drone_fixed_per_unit": (247.0, "solved from Y6 actuals; refine live"),
}


class CostModel:
    def __init__(self, constants=None):
        self.c = {k: v[0] for k, v in DEFAULT_CONSTANTS.items()}
        if constants:
            self.c.update(constants)

    # -- experience-curve multipliers (keyed on PRIOR-year cumulative R&D) --
    @staticmethod
    def reduce_camera(cum_rd_000s):
        return _vlookup(cum_rd_000s, _T["costs_acc_reduce"])

    @staticmethod
    def reduce_drone(cum_rd_000s):
        return _vlookup(cum_rd_000s, _T["costs_uav_reduce"])

    # -- component $/unit ----------------------------------------------------
    def camera_components(self, design, cum_rd_000s):
        """design: pq-style dict (sensor_id, lcd_id, resolution_id,
        photo_modes_id, housing_dollars, editing_dollars,
        accessories_dollars, extra_features). Returns $/unit."""
        r = self.reduce_camera(cum_rd_000s)
        t = _T
        parts = {
            "sensor":      _vlookup(design["sensor_id"], t["costs_acc_imagesensor"]) * r,
            "lcd":         _vlookup(design["lcd_id"], t["costs_acc_lcddisplay"]) * r,
            "resolution":  _vlookup(design["resolution_id"], t["costs_acc_imagequality"]) * r,
            "photo_modes": _vlookup(design["photo_modes_id"], t["costs_acc_photomodes"]) * r,
            # housing/editing/accessories: NO reduce (AB278-280)
            "housing":     float(design["housing_dollars"]),
            "editing":     float(design["editing_dollars"]),
            "accessories": float(design["accessories_dollars"]),
            # features: reduce applied TWICE (bundle quirk, AB281)
            "features":    _vlookup(design["extra_features"], t["costs_acc_utilityfeatures"]) * r * r,
        }
        return parts, sum(parts.values())

    def drone_components(self, design, camera_unit_cost, cum_rd_000s):
        """design: pq-style drone dict. camera_unit_cost = AB300 ($/unit).
        Returns (parts dict, $/unit)."""
        r = self.reduce_drone(cum_rd_000s)
        t = _T
        parts = {
            # built-in camera: upgrade $ x reduce + WHOLE camera unit cost (AB513)
            "builtin_camera": _vlookup(design["builtin_camera_id"], t["costs_uav_camera"]) * r
                              + camera_unit_cost,
            "gps":           _vlookup(design["gps_id"], t["costs_uav_gps"]) * r,
            "battery":       _vlookup(design["battery_min"], t["costs_uav_battery"]) * r,
            "rotors":        (_vlookup(design["rotors"], t["costs_uav_rotors"])
                              + _vlookup(design["rotor_perf_id"], t["costs_uav_prop"])) * r,
            "frame":         _vlookup(design["frame_id"], t["costs_uav_bodyframe"]) * r,
            "controller":    _vlookup(design["flight_controller_id"], t["costs_uav_controller"]) * r,
            "stabilization": _vlookup(design["stabilization_id"], t["costs_uav_stabilization"]) * r,
            # features: reduce applied TWICE (bundle quirk, AB520)
            "features":      _vlookup(design["extra_features"], t["costs_uav_utilityfeatures"]) * r * r,
        }
        return parts, sum(parts.values())

    # -- full production $/unit (AB300 / AB539) -------------------------------
    def camera_unit_cost(self, design, cum_rd_000s):
        _, comp = self.camera_components(design, cum_rd_000s)
        return comp + self.c["camera_fixed_per_unit"]

    def drone_unit_cost(self, design, camera_unit_cost, cum_rd_000s):
        _, comp = self.drone_components(design, camera_unit_cost, cum_rd_000s)
        return comp + self.c["drone_fixed_per_unit"]

    # -- warranty ------------------------------------------------------------
    @staticmethod
    def warranty_claim_rate(product, warranty_days_id, pq100,
                            incentive_per_unit, training_per_pat):
        """Exact claim-rate formula (§5). product: 'camera'|'drone'."""
        if product == "camera":
            base = _vlookup(warranty_days_id, WARRANTY_ACC_PERIOD)
            inc = _vlookup(incentive_per_unit, WARRANTY_INCENTIVE_ACC)
            lo, hi = 0.045, 0.55
        else:
            base = _vlookup(warranty_days_id, WARRANTY_UAV_PERIOD)
            inc = _vlookup(incentive_per_unit, WARRANTY_INCENTIVE_UAV)
            lo, hi = 0.055, 0.575
        pq_add = _vlookup(pq100, WARRANTY_PQ)
        bp = _vlookup(training_per_pat, WARRANTY_BESTPRACTICES)
        return max(lo, min(hi, (base + pq_add) * bp * inc))

    def warranty_cost_per_unit(self, product, warranty_days_id, pq100,
                               incentive_per_unit, training_per_pat):
        rate = self.warranty_claim_rate(product, warranty_days_id, pq100,
                                        incentive_per_unit, training_per_pat)
        g = "G18" if product == "camera" else "G19"
        return rate * self.c[g], rate

    # -- delivery ------------------------------------------------------------
    def delivery_per_unit(self, product, region, price):
        """shipping $/unit (flat) + duty % x price (ad valorem)."""
        if product == "camera":
            ship = self.c["G26"]
            duty = self.c[{"NA": "G30", "EA": "G31",
                           "AP": "G32", "LA": "G33"}[region]]
        else:
            ship = self.c["G27"]
            duty = self.c[{"NA": "G34", "EA": "G35",
                           "AP": "G36", "LA": "G37"}[region]]
        return ship + duty / 100.0 * price

    def full_unit_cost(self, product, region, price, design,
                       camera_unit_cost, cum_rd_000s,
                       warranty_days_id, pq100, incentive, training):
        """Production + warranty + delivery $/unit for one region."""
        if product == "camera":
            prod = self.camera_unit_cost(design, cum_rd_000s)
        else:
            prod = self.drone_unit_cost(design, camera_unit_cost, cum_rd_000s)
        wcost, _ = self.warranty_cost_per_unit(product, warranty_days_id,
                                               pq100, incentive, training)
        return prod + wcost + self.delivery_per_unit(product, region, price)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from pq import baseline_camera_design, baseline_drone_design
    cm = CostModel()
    cam = baseline_camera_design()
    dr = baseline_drone_design()
    parts, comp = cm.camera_components(cam, 63000)
    print("camera components $/unit:", round(comp, 2), parts)
    cam_unit = cm.camera_unit_cost(cam, 63000)
    print("camera production $/unit:", round(cam_unit, 2), "(Y6 actual ~155)")
    dparts, dcomp = cm.drone_components(dr, 155.0, 42000)
    print("drone components $/unit:", round(dcomp, 2))
    print("drone production $/unit:", round(cm.drone_unit_cost(dr, 155.0, 42000), 2),
          "(Y6 actual ~776)")
    for prod, wid, pq in (("camera", 4, 47), ("drone", 4, 41)):
        wcost, rate = cm.warranty_cost_per_unit(prod, wid, pq, 2.4, 1000)
        print(f"{prod} warranty: rate {rate:.3f} -> ${wcost:.2f}/unit")
    # marginal checks vs live empiricals
    cam2 = dict(cam, sensor_id=3)  # 11mm -> 10mm
    _, comp2 = cm.camera_components(cam2, 63000)
    print("sensor 11->10mm saves $/unit:", round(comp - comp2, 2),
          "(live: $4.1M/1.355M units = $3.03)")
    dr2 = dict(dr, stabilization_id=3)  # enh -> adv
    _, dcomp2 = cm.drone_components(dr2, 155.0, 42000)
    print("stab enh->adv adds $/unit:", round(dcomp2 - dcomp, 2),
          "(live net -$3.3M ≈ +$20/unit x 221k = $4.4M cost)")
