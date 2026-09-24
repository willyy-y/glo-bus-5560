"""
GLO-BUS scoring model — exact client-side replica.

Reverse-engineered 2026-09-24 from the GLO-BUS 6.22.1 bundle plus the
official CDJ scoring help PDFs. See research/scoring_report.md.

Covers: EPS, ROE, credit rating (3 VLOOKUP inputs -> points -> grade),
image rating (share/PQ/citizenship with year deflators), Investor
Expectation (I.E.) annual + game-to-date, Best-In-Industry (B-I-I) annual
+ game-to-date, weighted-average and overall scores, Bull's Eye and
Leap Frog bonus points.

Stock price is server-side: the bundle never computes it. Treat it via
`stock` inputs you supply (e.g. last observed / heuristic) — the I.E.
and B-I-I math around it is exact.

Weights are instructor-set; Industry 18 Y6 scores (IE 116, BII 98)
prove five 20-point measures with a 50/50 I.E./B-I-I blend. Pass your
own `weights` dict and `blend` to override.
"""

import json
import math
import os

TABLES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "research", "scoring_tables.json")

with open(TABLES_PATH) as f:
    _T = json.load(f)

from engine import DemandEngine  # for the exact VLOOKUP semantics

_vlookup = DemandEngine.vlookup


# ----------------------------------------------------------------------------
# Annual performance targets (exact, from official scoring docs)
# ----------------------------------------------------------------------------
YEARS = list(range(6, 16))

EPS_TARGETS = {6: 1.25, 7: 2.00, 8: 3.00, 9: 4.25, 10: 5.50,
               11: 7.00, 12: 8.50, 13: 10.50, 14: 12.50, 15: 14.50}
ROE_TARGETS = {6: 17.5, 7: 20.0, 8: 25.0, 9: 30.0, 10: 35.0,
               11: 40.0, 12: 42.5, 13: 45.0, 14: 47.5, 15: 50.0}  # percent
STOCK_TARGETS = {6: 20, 7: 35, 8: 60, 9: 100, 10: 150,
                 11: 200, 12: 250, 13: 300, 14: 330, 15: 350}
CREDIT_TARGET_MIN = {6: "B+", 7: "B+", 8: "A-", 9: "A-", 10: "A-",
                     11: "A", 12: "A", 13: "A", 14: "A", 15: "A"}
IMAGE_TARGETS = {6: 70, 7: 72, 8: 72, 9: 75, 10: 75,
                 11: 77, 12: 77, 13: 80, 14: 80, 15: 80}

CREDIT_GRADES = ["C-", "C", "C+", "B-", "B", "B+", "A-", "A", "A+"]
GRADE_ORDER = {g: i for i, g in enumerate(CREDIT_GRADES)}

# I.E. credit points for a 20-point credit weight (grade x year-band table)
_IE_CREDIT_20 = {
    (6, 7):   {"A+": 24, "A": 23, "A-": 22, "B+": 20, "B": 16,
               "B-": 12, "C+": 8, "C": 4, "C-": 0},
    (8, 10):  {"A+": 24, "A": 22, "A-": 20, "B+": 18, "B": 15,
               "B-": 12, "C+": 8, "C": 4, "C-": 0},
    (11, 15): {"A+": 24, "A": 20, "A-": 18, "B+": 16, "B": 14,
               "B-": 11, "C+": 8, "C": 4, "C-": 0},
}
# B-I-I credit points for a 20-point credit weight (anchored to A+)
_BII_CREDIT_20 = {"A+": 20, "A": 19, "A-": 18, "B+": 16, "B": 14,
                  "B-": 11, "C+": 8, "C": 5, "C-": 1}

DEFAULT_WEIGHTS = {"eps": 20, "roe": 20, "stock": 20, "credit": 20, "image": 20}
DEFAULT_BLEND = {"ie": 0.5, "bii": 0.5}


# ----------------------------------------------------------------------------
# EPS / ROE
# ----------------------------------------------------------------------------
def eps(net_profit, shares_outstanding_m):
    """EPS = round(net / ending shares, 2). net in $, shares in millions."""
    return round(net_profit / (shares_outstanding_m * 1e6), 2)


def roe(net_profit, equity_begin, equity_end):
    """ROE = round(net / avg(beg,end) equity, 3), as a FRACTION (0.419)."""
    avg_eq = (equity_begin + equity_end) / 2.0
    if avg_eq <= 0:
        return -100.0
    return round(net_profit / avg_eq, 3)


# ----------------------------------------------------------------------------
# Credit rating — fully client-side, deterministic
# ----------------------------------------------------------------------------
def credit_rating(debt_ratio, coverage, default_risk):
    """
    debt_ratio: total debt / (total debt + total equity), rounded to 3 dp
    coverage:   operating profit / interest expense, rounded to 2 dp
                (if interest <= 0 the game forces 1000)
    default_risk: the bundle's credit_currentratio (AB1819/AB1835), rounded 2dp
    Returns (grade, total_points, interest_adder).
    Grade thresholds on total: A+>=345, A>=225, A->=165, B+>=125,
    B>=110, B->=95, C+>=80, C>=65, C->=1.
    """
    dr = round(debt_ratio, 3)
    cov = round(coverage, 2)
    dfr = round(default_risk, 2)
    pts = (_vlookup(dr, _T["credit_debtpercent"])
           + _vlookup(cov, _T["credit_coverage"])
           + _vlookup(dfr, _T["credit_currentratio"]))
    total = max(1, pts)
    grade_num = int(_vlookup(total, _T["credit_rating"]))
    letter_map = {int(k): v for k, v in _T["credit_letter"] if k >= 1}
    grade = letter_map.get(grade_num, "C-")
    adder_map = {int(k): v for k, v in _T["credit_interestadder"] if k >= 1}
    adder = adder_map.get(grade_num, 0.06)
    return grade, total, adder


# ----------------------------------------------------------------------------
# Image rating — fully client-side, deterministic
# ----------------------------------------------------------------------------
def image_rating(year, camera_pq100, drone_pq100, share_ratios,
                 citizenship, sells_cameras=True, sells_drones=True):
    """
    year: current game year (6..15)
    camera_pq100 / drone_pq100: P/Q on the 0-100 scale (0 if product not sold)
    share_ratios: dict {"camera": [r1..r4], "drone": [r1..r4]} of
                  own-share/baseline-share per region actually sold
    citizenship: dict with charitable (dollars), green (0-5), energy (dollars),
                 cafeteria (0-5), safety (0-5), conduct (0-5)
    Returns the integer image rating (0-100).
    """
    share_pts = 0.0
    for prod, ratios in share_ratios.items():
        if not ratios:
            continue
        share_pts += sum(_vlookup(r, _T["image_share"])
                         for r in ratios) * (4.0 / len(ratios))
    n_prod = (1 if sells_cameras else 0) + (1 if sells_drones else 0)
    pq_pts = 0.0
    if sells_cameras and camera_pq100:
        pq_pts += _vlookup(camera_pq100, _T["image_pq"])
    if sells_drones and drone_pq100:
        pq_pts += _vlookup(drone_pq100, _T["image_pq"])
    if n_prod == 1:
        pq_pts *= 2.0

    c = citizenship
    raw_cit = (_vlookup(c.get("charitable", 0), _T["citizen_charitable"])
               + _vlookup(c.get("green", 0), _T["citizen_green"])
               + _vlookup(c.get("energy", 0), _T["citizen_energy"])
               + _vlookup(c.get("cafeteria", 0), _T["citizen_cafeteria"])
               + _vlookup(c.get("safety", 0), _T["citizen_safety"])
               + _vlookup(c.get("conduct", 0), _T["citizen_conduct"]))
    cit_pts = min(20.0, round(raw_cit * _vlookup(year, _T["citizen_year"]), 0))
    year_mult = _vlookup(year, _T["image_year"])
    img = min(100, round((share_pts + pq_pts) * year_mult + cit_pts, 0))
    return int(img)


# ----------------------------------------------------------------------------
# Investor Expectation — annual
# ----------------------------------------------------------------------------
def _ie_ratio_score(w, p, t):
    if p < 0:
        return 0
    if p < t:
        return round(w * (p / t), 0)
    if p == t:
        return w
    return min(round(w * (1 + 0.5 * (p / t - 1)), 0), round(1.20 * w, 0))


def _ie_credit_score(w, grade, year):
    band = next(b for b in _IE_CREDIT_20 if b[0] <= year <= b[1])
    return round(_IE_CREDIT_20[band][grade] * w / 20.0, 0)


def ie_annual(year, perf, weights=None):
    """
    perf: dict eps, roe_pct, stock, credit_grade, image
    Returns (total_ie, {measure: points}). Max annual = 1.2 * sum(weights).
    """
    w = weights or DEFAULT_WEIGHTS
    pts = {
        "eps":    _ie_ratio_score(w["eps"], perf["eps"], EPS_TARGETS[year]),
        "roe":    _ie_ratio_score(w["roe"], perf["roe_pct"], ROE_TARGETS[year]),
        "stock":  _ie_ratio_score(w["stock"], perf["stock"], STOCK_TARGETS[year]),
        "credit": _ie_credit_score(w["credit"], perf["credit_grade"], year),
        "image":  _ie_ratio_score(w["image"], perf["image"], IMAGE_TARGETS[year]),
    }
    return int(sum(pts.values())), pts


# ----------------------------------------------------------------------------
# Best-In-Industry — annual
# ----------------------------------------------------------------------------
def _bii_credit_score(w, grade):
    return round(_BII_CREDIT_20[grade] * w / 20.0, 0)


def bii_annual(year, perf, leaders, weights=None):
    """
    perf: our dict eps, roe_pct, stock, credit_grade, image
    leaders: dict of industry-leader values for eps, roe_pct, stock, image
             (credit is anchored to A+, no leader needed)
    Returns (total_bii, {measure: points}). Max = sum(weights) = 100.
    """
    w = weights or DEFAULT_WEIGHTS
    targets = {"eps": EPS_TARGETS[year], "roe_pct": ROE_TARGETS[year],
               "stock": STOCK_TARGETS[year], "image": IMAGE_TARGETS[year]}
    pts = {}
    for m in ("eps", "roe_pct", "stock", "image"):
        k = "roe" if m == "roe_pct" else m
        p, l, t = perf[m], leaders[m], targets[m]
        if p < 0:
            pts[k] = 0
            continue
        leader_score = w[k] if l >= t else round(w[k] * l / t, 0)
        pts[k] = round(leader_score * p / l, 0) if l > 0 else 0
    pts["credit"] = _bii_credit_score(w["credit"], perf["credit_grade"])
    return int(sum(pts.values())), pts


def annual_weighted(year, perf, leaders, weights=None, blend=None):
    ie, ie_pts = ie_annual(year, perf, weights)
    bii, bii_pts = bii_annual(year, perf, leaders, weights)
    b = blend or DEFAULT_BLEND
    return (b["ie"] * ie + b["bii"] * bii, ie, bii, ie_pts, bii_pts)


# ----------------------------------------------------------------------------
# Game-to-date scoring
# ----------------------------------------------------------------------------
def gtd_eps(history):
    """history: list of dicts with net_profit ($) and shares (millions, EOY).
    Returns weighted-avg EPS = sum(net) / sum(shares)."""
    return (sum(h["net_profit"] for h in history)
            / sum(h["shares"] * 1e6 for h in history))


def gtd_roe(history):
    """Weighted-avg ROE = sum(net) / sum(yearly avg equity)."""
    return (sum(h["net_profit"] for h in history)
            / sum((h["equity_begin"] + h["equity_end"]) / 2.0 for h in history))


def gtd_score(years, history, leaders_gtd, weights=None, blend=None):
    """
    years: list of game years completed, e.g. [6, 7]
    history: list of per-year dicts: net_profit, shares, equity_begin,
             equity_end, stock, credit_grade, image
    leaders_gtd: dict with leader weighted-avg eps, roe, 3-yr-avg image,
                 and most-recent stock
    Returns dict with gtd_ie, gtd_bii, gtd_weighted, overall (+bonuses).
    """
    w = weights or DEFAULT_WEIGHTS
    b = blend or DEFAULT_BLEND
    n = len(years)
    perf = {
        "eps": gtd_eps(history),
        "roe_pct": gtd_roe(history) * 100.0,
        "stock": history[-1]["stock"],
        "credit_grade": history[-1]["credit_grade"],
        "image": sum(h["image"] for h in history[-3:]) / min(3, n),
    }
    avg_targets = {
        "eps": sum(EPS_TARGETS[y] for y in years) / n,
        "roe": sum(ROE_TARGETS[y] for y in years) / n,
        "stock": STOCK_TARGETS[years[-1]],
        "credit_grade": perf["credit_grade"],
        "image": sum(IMAGE_TARGETS[y] for y in years[-3:]) / min(3, n),
    }
    ie_pts = {
        "eps": _ie_ratio_score(w["eps"], perf["eps"], avg_targets["eps"]),
        "roe": _ie_ratio_score(w["roe"], perf["roe_pct"], avg_targets["roe"]),
        "stock": _ie_ratio_score(w["stock"], perf["stock"], avg_targets["stock"]),
        "credit": _ie_credit_score(w["credit"], perf["credit_grade"], years[-1]),
        "image": _ie_ratio_score(w["image"], perf["image"], avg_targets["image"]),
    }
    gtd_ie = int(sum(ie_pts.values()))
    bii_pts = {}
    for m in ("eps", "roe_pct", "stock", "image"):
        k = "roe" if m == "roe_pct" else m
        p, l = perf[m], leaders_gtd[m]
        t = avg_targets[m]
        if p < 0:
            bii_pts[k] = 0
            continue
        leader_score = w[k] if l >= t else round(w[k] * l / t, 0)
        bii_pts[k] = round(leader_score * p / l, 0) if l > 0 else 0
    bii_pts["credit"] = _bii_credit_score(w["credit"], perf["credit_grade"])
    gtd_bii = int(sum(bii_pts.values()))
    gtd_weighted = b["ie"] * gtd_ie + b["bii"] * gtd_bii
    bonuses = sum(h.get("bullseye", 0) + h.get("leapfrog", 0) for h in history)
    return {
        "gtd_ie": gtd_ie, "gtd_bii": gtd_bii,
        "gtd_weighted": gtd_weighted,
        "bonuses": bonuses,
        "overall": gtd_weighted + bonuses,
        "ie_pts": ie_pts, "bii_pts": bii_pts,
    }


# ----------------------------------------------------------------------------
# Bonuses
# ----------------------------------------------------------------------------
def bullseye(proj_revenue, actual_revenue, proj_eps, actual_eps,
             proj_image, actual_image):
    """
    Uses the LAST SAVED decision entries' projected values vs actuals.
    Revenue/EPS variance = (actual - forecast) / actual.
    """
    rev_ok = abs((actual_revenue - proj_revenue) / actual_revenue) <= 0.05
    eps_ok = (abs(actual_eps - proj_eps) <= 0.10
              or abs((actual_eps - proj_eps) / actual_eps) <= 0.05)
    img_ok = abs(actual_image - proj_image) <= 4
    return 1 if (rev_ok and eps_ok and img_ok) else 0


def leapfrog(scores_by_company):
    """
    scores_by_company: {company: (prior_weighted, current_weighted)}.
    Returns the set of companies earning the point (ties all earn it).
    """
    gains = {c: cur - prior for c, (prior, cur) in scores_by_company.items()}
    best = max(gains.values())
    if best <= 0:
        return set()
    return {c for c, g in gains.items() if g == best}


if __name__ == "__main__":
    # Sanity check: Y6 Company E actuals (read from live CDJ 2026-09-23)
    perf6 = {"eps": 3.03, "roe_pct": 41.9, "stock": 99.86,
             "credit_grade": "A-", "image": 84}
    # Leader proxies: EPS leader ~3.5, ROE leader ~45, stock leader ~105, image ~86
    leaders6 = {"eps": 3.5, "roe_pct": 45.0, "stock": 105.0, "image": 86.0}
    wa, ie, bii, ie_pts, bii_pts = annual_weighted(6, perf6, leaders6)
    print("Y6 annual weighted:", wa, "| IE:", ie, "(expect 116) | BII:", bii,
          "(expect 98)")
    print("  IE pts:", ie_pts)
    print("  BII pts:", bii_pts)
    # Credit check: Y6 state — debt $104M, equity $172.112M
    dr = 104 / (104 + 172.112)
    print("Y6 debt ratio:", round(dr, 3))
    grade, total, adder = credit_rating(dr, 8.0, 5.0)
    print("credit @ cov 8, drisk 5:", grade, total, "adder", adder)
