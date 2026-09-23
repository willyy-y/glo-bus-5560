"""
Thin P&L layer on top of the demand engine.

The game's full cost model (component/labor/warranty/delivery/duty by
region, depreciation, interest, taxes) is NOT replicated here. Instead:

  contribution = sum over regions of units * (effective_price - unit_cost)

then a calibrated fixed block (R&D, marketing, admin, depreciation,
interest, citizenship, other) and a flat tax rate produce net profit / EPS.

Calibrate once: run the base case, read the projection box's net profit,
call calibrate_fixed() to solve for the fixed block, and reuse it across
sweeps. Interest-sensitive finance sweeps (debt/buyback) should adjust the
fixed block by hand (interest delta = debt_delta * rate).

Units passed in are RAW engine units; set unit_scale so that
units_display_k = raw_units * unit_scale / 1000 matches the box.
"""

REGIONS = ["NA", "EA", "AP", "LA"]


def revenue(units, own, unit_scale=1.0):
    """units: engine output. own: decisions with price/prom_weeks/prom_disc."""
    rev = 0.0
    for product in ("camera", "drone"):
        for region in REGIONS:
            u = units[product][region] * unit_scale
            price = own[product][region]["price"]
            if product == "camera":
                w = own[product][region].get("prom_weeks", 0)
                d = own[product][region].get("prom_disc", 0)
                # approx: prom_weeks/52 of volume sells at (1 - disc) price
                eff = price * (1 - (w / 52.0) * (d / 100.0))
            else:
                # 3rd-party share sells at (1 - discount)
                share = own[product][region].get("third_party_share", 0.0)
                disc = own[product][region].get("third_party_disc", 0.0)
                eff = price * (1.0 - share * disc / 100.0)
            rev += u * eff
    return rev


def contribution(units, own, unit_cost, unit_scale=1.0):
    """unit_cost: {product: $/unit} variable cost (component+labor+warranty+
    delivery+duty, observable on the decision pages)."""
    rev = revenue(units, own, unit_scale)
    cogs = 0.0
    for product in ("camera", "drone"):
        u = sum(units[product][r] for r in REGIONS) * unit_scale
        cogs += u * unit_cost[product]
    return rev - cogs, rev


def calibrate_fixed(contrib, net_profit, tax_rate=0.30):
    """Solve fixed block F from: net = (contrib - F) * (1 - t)."""
    return contrib - net_profit / (1 - tax_rate)


def pnl(units, own, unit_cost, fixed, shares, tax_rate=0.30, unit_scale=1.0):
    contrib, rev = contribution(units, own, unit_cost, unit_scale)
    pbt = contrib - fixed
    net = pbt - tax_rate * max(pbt, 0)
    eps = net / shares / 1e6  # net in $, shares in millions
    return {
        "units_cam": sum(units["camera"][r] for r in REGIONS) * unit_scale,
        "units_drone": sum(units["drone"][r] for r in REGIONS) * unit_scale,
        "revenue": rev,
        "contribution": contrib,
        "pbt": pbt,
        "net_profit": net,
        "eps": eps,
    }
