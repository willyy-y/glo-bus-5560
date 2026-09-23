# How GLO-BUS Works

An independent explainer for the GLO-BUS business simulation (v6.22.1),
reverse-engineered from the client bundle and validated against live
projection-box experiments. This is not official documentation; it is
what the code actually does.

---

## 1. The game in one paragraph

You run a company selling action-capture cameras and UAV drones in four
regions (North America, Europe-Africa, Asia-Pacific, Latin America),
competing against 8 rival companies over 7+ simulated years. Each year
you set product designs, prices, marketing budgets, production volumes,
and financing, then the simulator scores you on EPS, ROE, stock price,
credit rating, and image rating against investor expectations and the
best rival in each category.

---

## 2. The demand model (the core of everything)

Every region/product/year, your unit demand is computed as:

```
demand = ( Σ VLOOKUP(x_i) × scenario_constant_i ) × price_mult × model_mult × image_mult
```

### The additive part

Each demand driver (P/Q rating, warranty length, retailer support $/unit,
advertising, website spending, outlet count, promotions, etc.) goes
through its own VLOOKUP table with **approximate match** semantics
(largest key ≤ input wins). The looked-up value is multiplied by
scenario constants (AP/Q cells) that encode market size and scaling.
There are 15 such tables; the P/Q table and warranty table have their
own group scales, everything else shares a third.

Key subtlety: **retailer support is budget ÷ units**. You enter a total
support budget ($000s); the model divides by projected units to get
$/unit, which feeds the VLOOKUP. This creates a fixed-point loop: fewer
units → higher $/unit → slightly more demand. The projection box iterates
this to convergence. Drones use the same trick but divide by
**third-party units only** (not total units).

### The multiplicative part

Three multipliers stack on top of the additive sum:

- **Price**: `VLOOKUP(own_price / avg_price) × (own ≤ avg ? 1.05 : 1/1.05)`
  (1.10 for AP/LA). The VLOOKUP table is steep near 1.0: pricing 5% below
  average multiplies demand ~1.1×; 5% above multiplies ~0.94×.
- **Models**: more models than average helps, fewer hurts, via a similar
  ratio VLOOKUP with a 1.05/1.10-style adjustment.
- **Image**: your company image rating (0–100) maps through a VLOOKUP;
  higher image = more demand everywhere.

### The average that matters

**You are 1 of the 9 firms in every regional average.** The "industry
average" price your ratio is scored against is:

```
avg_price = (your_price + 8 × rival_avg) / 9
```

When you raise your price $9, the average you face rises $1. This dampens
the penalty for price increases and is the single most commonly
misunderstood mechanic. Competitive-assumption inputs are your *guess*
at rival behavior; the box shifts all rivals by (your assumed average −
their base average).

### What actually drives demand (empirical, Year 7)

From live experiments (baseline: 1,373k cameras, 221k drones):

| Change | Demand effect |
|---|---|
| Camera P/Q 4.7 → 4.6 | −19.8k units (−1.4%) |
| Camera P/Q 4.7 → 4.5 | −40.8k units (−3.0%) |
| NA camera price $243 → $253 | −13.9k NA units (−3.1%) |
| NA camera warranty 180 → 90 days | −26.1k NA units (−5.8%) |
| NA drone price $1,190 → $1,290 | −8.6k NA units (−10.7%) |
| Drone P/Q 4.1 → 4.2 | +5.7k units (+2.6%) |

Demand is **inelastic**: 4% price hikes cost ~3% of units. Margin gains
dominate volume losses for pricing decisions.

---

## 3. Product design and P/Q

P/Q (performance/quality) is a 1–10 rating computed from your design
choices: image sensor size, LCD pixels, photo modes, housing, software,
accessories, extra features, and cumulative R&D. Each choice has a cost;
better specs cost more per unit.

The profit math on P/Q is brutal and asymmetric:
- **Downgrading** camera P/Q 4.7→4.6 (11mm→10mm sensor) **gained**
  $3.2M net profit — the $4.1M component saving outweighed the demand loss.
- **Upgrading** drone P/Q 4.1→4.2 (better stabilization) **lost**
  $3.3M net profit — the unit cost increase swamped the +2.6% demand gain.

The industry averages ~4.3 (cameras) and ~4.7 (drones). Chasing the
average with expensive upgrades destroys profit; the demand gain per P/Q
point is small relative to the cost.

---

## 4. Marketing

Four spend categories per region per product:

- **Retailer support** (budget, converted to $/unit as described above).
  This is the highest-leverage marketing dollar because it enters the
  additive sum directly and scales with the fixed-point feedback.
- **Advertising** (local media spend, $000s).
- **Website / search advertising** (online presence).
- **Promotions** (weeks × discount %; a separate additive term).

There are no separate chain/online/local outlet spending decisions;
outlet counts are internally derived, partly from retailer support.

Warranty length (days) is a demand driver with real cost: cutting NA
camera warranty 180→90 days saved ~$2M in repairs but lost $0.7M net
profit after the demand hit. Keep long warranties unless the repair
cost is extreme.

---

## 5. Operations and finance

- **Production**: you set build volumes. Sales = min(demand, production).
  Underbuilding caps revenue; overbuilding wastes working capital.
- **Finance**: debt, equity issuance, buybacks, dividends. Interest hits
  the P&L; leverage boosts ROE when returns exceed the rate.
- **Cash**: ending cash matters for the credit rating.

Unit economics (Year 6 actuals, useful as Year 7 priors):
- Camera: ~$155 production + ~$13 delivery + ~$9 warranty ≈ **$177/unit**
- Drone: ~$776 production + $60 delivery + ~$66 warranty ≈ **$902/unit**

---

## 6. Scoring

50% Investor Expectation + 50% Best-In-Industry, plus bonuses:

- **Measures**: EPS, ROE, stock price, credit rating, image rating.
- **Investor Expectation**: beat your targets (set from prior-year
  performance). Overshooting by up to 40% earns bonus points (a 20-point
  measure can score 24).
- **Best-In-Industry**: rank vs the best rival on each measure.
  Credit maps: A+ = 20, A = 19, A− = 18, B+ = 16, B = 14, B− = 11,
  C+ = 8, C = 5, C− = 1.
- **Bull's Eye** (1 bonus point): forecast all three within tolerance —
  revenue ±5%, EPS ±$0.10 or ±5%, image ±4. Missing any one loses it.
- **Leap Frog** (starts Year 7): bonus for jumping rank positions.
- Game-to-date EPS/ROE use weighted averages (exact weights unpublished).

**Stock price** responds to revenue growth, EPS growth, average ROE,
credit rating, target consistency, and dividend growth rate.

**Image rating** responds to P/Q, CSR spending (sustained 4–5 years),
and competitive positioning. NA/EA customers are more price- and
P/Q-sensitive than AP/LA.

---

## 7. Strategic implications

1. **Price first.** Demand is inelastic; the 9-firm average dampens the
   penalty. Test higher prices before touching anything else.
2. **Size capacity to the resulting demand.** Build what you'll sell at
   the chosen prices, not the other way around.
3. **Don't chase P/Q with money.** Upgrades cost more profit than the
   demand they buy. Downgrades can *increase* profit.
4. **Keep long warranties** unless repair costs are extreme; the demand
   value exceeds the claim cost.
5. **Forecast conservatively for Bull's Eye.** Optimistic revenue
   forecasts miss the ±5% band (Year 6 missed by $1.4M on a $513M forecast).
6. **Leverage early, de-lever late.** Debt boosts ROE when you're
   growing; cut it before the final years when stability scores.
7. **Dividends: none early, growing later.** The stock rewards consistent
   dividend growth, not level payouts.

---

## 8. About this engine

`engine.py` reproduces the projection-box demand math above. Validated
within 0.5% on 8 live experiments (see `README.md`). It is a **read-only
testbed**: it never touches the live game. Use it to screen price and
marketing options before entering anything.

Known gaps: design unit-cost changes aren't modeled (use the empirical
$3.01/unit per 0.1 camera P/Q and ~$20.70/unit per 0.1 drone P/Q from
live tests); AP/LA revenue runs ~5% high (exchange rates approximated);
rival reactions aren't modeled (see `--scenario` flags for synthetic
rival behaviors).
