"""
P/Q rating model — faithful replica of the GLO-BUS client-side computation.

Reverse-engineered from the GLO-BUS Student Decisions & Reports Program
(v6.22.1) JavaScript bundle. P/Q is computed from design choices on the
Product Design page as:

    camera: P/Q(0-100) = clamp(5, 100, round(sum(9 component scores) * rd_mult))
    drone:  P/Q(0-100) = clamp(5, 100, round(sum(11 component scores) * rd_mult))

where each component score is a VLOOKUP of the design decision into the
game's pq_* tables (same approximate-match semantics as the demand engine),
rd_mult is a VLOOKUP of cumulative R&D ($000s) into pq_acc_rd / pq_uav_rd,
and the displayed 1-10 rating is round(pq_100 / 10, 1).

The drone's built-in-camera component is NOT a direct design choice: it is
a VLOOKUP of (own camera P/Q display rating - industry-average camera P/Q
display rating) into pq_uav_camerapq. Improving camera P/Q therefore also
lifts drone P/Q.

Validated 2026-09-24 against 8 live read-only experiments:
  camera 11mm->10mm sensor: 4.7 -> 4.6  |  11mm->9mm: 4.7 -> 4.5
  drone stabilization enh->adv: 4.1 -> 4.2
  drone features 5->6, battery 12->15, rotor enh->adv, gps enh->adv:
    each 4.1 -> 4.3
All 8 predictions match exactly.

Design-choice -> table-input encodings (the game's dropdown `id` values):
  CAMERA
    sensor:        8mm->1 ... 14mm->7            (use sensor_id())
    lcd:          230k->1 ... 2360k->7            (use lcd_id())
    resolution:  1920x1080->1 ... 4096x2160->7   (use resolution_id())
    photo_modes: "4 / 3"->1 ... "16 / 4"->7      (use photo_modes_id())
    housing_dollars:   4..16  (id = dollars)
    editing_dollars:   4..16  (id = dollars)
    accessories_dollars: 6..20 (id = dollars)
    extra_features:    2..10  (id = count)
    models:            1..7   (id = count)
    rd_cumulative_000s: total camera R&D incl. current year, in $000s
  DRONE
    builtin_camera_id: 1=No, 2=Minor, 3=Significant, 4=Major upgrade
    gps_id:            1=Basic, 2=Enhanced, 3=Advanced, 4=Best
    battery_min:       8,10,12,15,18,21,25,30
    rotors:            4, 6, 8
    rotor_perf_id:     1=Basic, 2=Enhanced, 3=Advanced, 4=Best
    frame_id:          1=Plastic, 2=g10/FR4 Fiberglass, 3=Carbon Fiber
    flight_controller_id: 1..6
    stabilization_id:  1=Basic, 2=Enhanced, 3=Advanced, 4=Best
    extra_features:    2..15  (id = count)
    models:            1..7   (id = count)
    rd_cumulative_000s: total drone R&D incl. current year, in $000s

NOTE: design choices also change unit production costs (and R&D spend hits
the P&L directly). Those cost effects are NOT in this module -- the bundle
computes them outside the extracted P/Q path. From live tests, the
empirical marginal costs are ~$3.01/unit per 0.1 camera P/Q and
~$20.70/unit per 0.1 drone P/Q. Treat P&L results of design sweeps as
structural, not decision-grade, until costs are modeled.
"""

import json
import math
import os

TABLES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "pq_tables.json")

with open(TABLES_PATH) as f:
    _TABLES = json.load(f)


# ----------------------------------------------------------------------------
# VLOOKUP — same approximate-match semantics as the demand engine
# (truncates the key toward zero to 9 decimals).
# ----------------------------------------------------------------------------
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


def excel_round(x, ndigits=0):
    """Excel ROUND: half away from zero (Python round() is banker's)."""
    m = 10 ** ndigits
    return math.floor(x * m + 0.5) / m if x >= 0 else -math.floor(-x * m + 0.5) / m


# ----------------------------------------------------------------------------
# Human-friendly option maps (dropdown label -> id)
# ----------------------------------------------------------------------------
SENSOR_MM = {8: 1, 9: 2, 10: 3, 11: 4, 12: 5, 13: 6, 14: 7}
LCD_KB = {"230k": 1, "460k": 2, "610k": 3, "920k": 4, "1040k": 5,
          "1230k": 6, "2360k": 7}
RESOLUTION = {"1920x1080": 1, "1920x1440": 2, "2704x1520": 3,
              "2704x2028": 4, "3840x2160": 5, "3840x2400": 6,
              "4096x2160": 7}
PHOTO_MODES = {"4/3": 1, "6/3": 2, "7/3": 3, "8/3": 4, "10/4": 5,
               "12/4": 6, "16/4": 7}
UPGRADE = {"none": 1, "minor": 2, "significant": 3, "major": 4}
LEVEL4 = {"basic": 1, "enhanced": 2, "advanced": 3, "best": 4}
FRAME = {"plastic": 1, "fiberglass": 2, "carbon": 3}
BATTERY_MIN = [8, 10, 12, 15, 18, 21, 25, 30]


# ----------------------------------------------------------------------------
# P/Q computation
# ----------------------------------------------------------------------------
def camera_pq(design):
    """
    design: dict with keys sensor_id, lcd_id, resolution_id, photo_modes_id,
            housing_dollars, editing_dollars, accessories_dollars,
            extra_features, models, rd_cumulative_000s.
    Returns (pq_100, pq_display). pq_100 is the 0-100 value the demand
    engine consumes; pq_display is the 1-decimal 1-10 rating shown in-game.
    """
    t = _TABLES
    if design["models"] == 0:
        return 0, 0.0
    s = (vlookup(design["sensor_id"], t["pq_acc_imagesensor"])
         + vlookup(design["lcd_id"], t["pq_acc_lcddisplay"])
         + vlookup(design["resolution_id"], t["pq_acc_imagequality"])
         + vlookup(design["photo_modes_id"], t["pq_acc_photomodes"])
         + vlookup(design["housing_dollars"], t["pq_acc_camerahousing"])
         + vlookup(design["editing_dollars"], t["pq_acc_editingsharing"])
         + vlookup(design["accessories_dollars"], t["pq_acc_accessories"])
         + vlookup(design["extra_features"], t["pq_acc_utilityfeatures"])
         + vlookup(design["models"], t["pq_acc_models"]))
    rd_mult = vlookup(design["rd_cumulative_000s"], t["pq_acc_rd"])
    pq100 = max(5, min(100, excel_round(s * rd_mult)))
    return int(pq100), round(pq100 / 10, 1)


def drone_pq(design, camera_pq_display, industry_camera_pq):
    """
    design: dict with keys builtin_camera_id, gps_id, battery_min, rotors,
            rotor_perf_id, frame_id, flight_controller_id, stabilization_id,
            extra_features, models, rd_cumulative_000s.
    camera_pq_display: own camera P/Q display rating (e.g. 4.7); 0 if no cameras.
    industry_camera_pq: industry-average camera P/Q display rating.
    Returns (pq_100, pq_display).
    """
    t = _TABLES
    if design["models"] == 0:
        return 0, 0.0
    cam_diff = (0 if camera_pq_display == 0
                else camera_pq_display - industry_camera_pq)
    s = (vlookup(design["builtin_camera_id"], t["pq_uav_builtincamera"])
         + vlookup(cam_diff, t["pq_uav_camerapq"])
         + vlookup(design["gps_id"], t["pq_uav_gpswifi"])
         + vlookup(design["battery_min"], t["pq_uav_batterypack"])
         + vlookup(design["rotors"], t["pq_uav_numrotors"])
         + vlookup(design["rotor_perf_id"], t["pq_uav_rotormotor"])
         + vlookup(design["frame_id"], t["pq_uav_bodyframe"])
         + vlookup(design["flight_controller_id"], t["pq_uav_flightcontrol"])
         + vlookup(design["stabilization_id"], t["pq_uav_camerastabilize"])
         + vlookup(design["extra_features"], t["pq_uav_utilityfeatures"])
         + vlookup(design["models"], t["pq_uav_models"]))
    rd_mult = vlookup(design["rd_cumulative_000s"], t["pq_uav_rd"])
    pq100 = max(5, min(100, excel_round(s * rd_mult)))
    return int(pq100), round(pq100 / 10, 1)


# ----------------------------------------------------------------------------
# Baseline designs (Company E, Y7 carry-forward, read 2026-09-23)
# ----------------------------------------------------------------------------
def baseline_camera_design():
    return {
        "sensor_id": SENSOR_MM[11],
        "lcd_id": LCD_KB["920k"],
        "resolution_id": RESOLUTION["2704x2028"],
        "photo_modes_id": PHOTO_MODES["8/3"],
        "housing_dollars": 10,
        "editing_dollars": 10,
        "accessories_dollars": 12,
        "extra_features": 3,
        "models": 2,
        "rd_cumulative_000s": 63000,  # $63M incl. current year
    }


def baseline_drone_design():
    return {
        "builtin_camera_id": UPGRADE["significant"],
        "gps_id": LEVEL4["enhanced"],
        "battery_min": 12,
        "rotors": 6,
        "rotor_perf_id": LEVEL4["enhanced"],
        "frame_id": FRAME["fiberglass"],
        "flight_controller_id": 2,  # inferred: validates against all 5 live tests
        "stabilization_id": LEVEL4["enhanced"],
        "extra_features": 5,
        "models": 2,
        "rd_cumulative_000s": 42000,  # $42M incl. current year
    }


if __name__ == "__main__":
    cam = baseline_camera_design()
    d = baseline_drone_design()
    c100, cdis = camera_pq(cam)
    print("camera baseline:", c100, cdis, "(expect 47, 4.7)")
    # industry avg camera P/Q inferred ~4.7 (AB455 ~= 0 at baseline)
    for ia in (4.5, 4.7, 5.0):
        d100, ddis = drone_pq(d, cdis, ia)
        print(f"drone baseline @ industry {ia}:", d100, ddis, "(expect 47/4.7 -> 41, 4.1)")
