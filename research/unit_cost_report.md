# GLO-BUS Unit-Cost Model — Reverse-Engineered from the Client Bundle

Source: `/tmp/glo-main.js` — GLO-BUS Student Decisions & Reports Program v6.22.1
(4,354,189 chars, 158 very long lines). Analysis is read-only; no live game
state was touched.

Raw extracted tables: `research/cost_tables.json` (this directory).

## How the model is organized

All per-unit production cost logic lives in one giant model function in the
bundle (the "CoData" computation, current-year column = `AB`, prior-year
column = `AA`). Conventions used below:

- Money cells are in **$000s** unless noted; unit counts are in **000s of units**.
- `VLookup(key, table)` = the bundle's approximate-match lookup (same
  semantics as the P/Q engine: key truncated toward zero to 9 decimals,
  largest table key ≤ lookup key wins). Bundle anchor:
  `VLookup(n,e){let t=0,i=0,s=0;...}` (~byte offset 453,000 region for tables).
- `excelRound(n, e)` = Excel-style ROUND(n, e), half away from zero.
  Bundle anchor: `excelRound(n,e){let t=function(s,d,m){...`.
- `Decisions.G<n>` = decision-page entry cells. `Costs.G<n>` = server-provided
  cost constants **not present in the bundle** — their values cannot be read
  from this file (listed as unresolved in §10).
- The 16 component-cost tables live in one JS object at byte offsets
  **439,591 – 440,990** (keys `costs_acc_*`, `costs_uav_*`).

---

## 1. Component cost tables (verbatim from the bundle)

Lookup key = the design decision's dropdown `id` (same ids as the P/Q model).
Values are **$/unit**.

### Camera

`costs_acc_imagesensor` — key = sensor id (8mm→1 … 14mm→7):
```
[[0,0],[1,2],[2,4],[3,7],[4,10],[5,15],[6,21.5],[7,30]]
```
i.e. 8mm $2, 9mm $4, 10mm $7, **11mm $10**, 12mm $15, 13mm $21.50, 14mm $30.

`costs_acc_lcddisplay` — key = LCD id (230k→1 … 2360k→7):
```
[[0,0],[1,2],[2,4],[3,7],[4,10],[5,15],[6,21.5],[7,30]]
```
i.e. 230k $2, 460k $4, 610k $7, **920k $10**, 1040k $15, 1230k $21.50, 2360k $30.

`costs_acc_imagequality` — key = resolution id (1920×1080→1 … 4096×2160→7):
```
[[0,0],[1,1],[2,3],[3,5],[4,8],[5,13],[6,21],[7,33]]
```
i.e. 1920×1080 $1, 1920×1440 $3, 2704×1520 $5, **2704×2028 $8**,
3840×2160 $13, 3840×2400 $21, 4096×2160 $33.

`costs_acc_photomodes` — key = photo-modes id ("4 / 3"→1 … "16 / 4"→7):
```
[[0,0],[1,2],[2,4],[3,6.5],[4,9],[5,14],[6,23],[7,35]]
```
i.e. 4/3 $2, 6/3 $4, 7/3 $6.50, **8/3 $9**, 10/4 $14, 12/4 $23, 16/4 $35.

`costs_acc_utilityfeatures` — key = extra-features count (2…10):
```
[[0,0],[1,2],[2,5],[3,9],[4,14],[5,25],[6,40],[7,62],[8,100],[9,150],[10,220]]
```
i.e. **3 features $9**, 4 → $14, 5 → $25, 6 → $40, 7 → $62, 8 → $100,
9 → $150, 10 → $220.

Camera housing (Decisions.G9), editing/sharing (G10), accessories (G11) have
**no table — their $/unit cost equals the dollar amount entered**
($4–$16 for housing/editing, $6–$20 for accessories). Baseline: $10/$10/$12.

### Drone

`costs_uav_camera` — key = built-in-camera upgrade id (1=No … 4=Major):
```
[[0,0],[1,0],[2,19.34],[3,44],[4,75]]
```
No $0, Minor $19.34, **Significant $44**, Major $75. (This is *on top of* a
whole camera unit cost — see AB513 below.)

`costs_uav_gps` — key = GPS id (1=Basic … 4=Best):
```
[[0,0],[1,40],[2,50],[3,75],[4,105]]
```
**Enhanced $50**, Advanced $75, Best $105.

`costs_uav_battery` — key = battery minutes (8…30):
```
[[0,0],[8,20],[10,45],[12,70],[15,100],[18,125],[21,150],[25,185],[30,230]]
```
**12-min $70**, 15-min $100, 18-min $125, 21-min $150, 25-min $185, 30-min $230.

`costs_uav_rotors` — key = rotor count:
```
[[0,0],[4,8],[6,23],[8,49]]
```
**6 rotors $23**, 8 rotors $49.

`costs_uav_prop` — key = rotor-performance id (1=Basic … 4=Best):
```
[[0,0],[1,7],[2,17],[3,47],[4,74]]
```
**Enhanced $17**, Advanced $47, Best $74.

`costs_uav_bodyframe` — key = frame id (1=Plastic, 2=Fiberglass, 3=Carbon):
```
[[0,0],[1,8],[2,17],[3,45]]
```
**Fiberglass $17**, Carbon Fiber $45.

`costs_uav_controller` — key = flight-controller id (1…6):
```
[[0,0],[1,30],[2,45],[3,67],[4,92],[5,122],[6,150]]
```
**#2 $45**, #3 $67, #4 $92, #5 $122, #6 $150.

`costs_uav_stabilization` — key = stabilization id (1=Basic … 4=Best):
```
[[0,0],[1,7],[2,18],[3,38],[4,63]]
```
**Enhanced $18**, Advanced $38, Best $63.

`costs_uav_utilityfeatures` — key = extra-features count (2…15):
```
[[0,0],[2,18],[3,36],[4,60],[5,90],[6,123],[7,162],[8,204],[9,234],[10,265],[11,292],[12,324],[13,355],[14,416],[15,480]]
```
**5 features $90**, 6 → $123, 7 → $162, 8 → $204, 10 → $265, 15 → $480.

### Experience-curve ("reduce") multipliers — keyed on cumulative R&D ($000s)

`costs_acc_reduce` (camera), key = `AA135` = prior-year cumulative camera R&D:
```
[[0,1],[45e3,1],[55e3,.99],[65e3,.98],[75e3,.97],[85e3,.96],[1e5,.94],[115e3,.92],[135e3,.9],[155e3,.88],[175e3,.86],[2e5,.84],[225e3,.82],[25e4,.8],[28e4,.78],[325e3,.77],[375e3,.76],[43e4,.75]]
```
`costs_uav_reduce` (drone), key = `AA384` = prior-year cumulative drone R&D:
```
[[0,1],[3e4,1],[5e4,.99],[7e4,.98],[9e4,.97],[11e4,.96],[13e4,.94],[155e3,.92],[18e4,.9],[205e3,.88],[23e4,.85],[26e4,.82],[295e3,.79],[33e4,.76],[37e4,.74],[41e4,.72],[45e4,.71],[495e3,.7]]
```
More cumulative R&D → lower component costs (manufacturing learning curve).
Y7 baselines: camera $63M cumulative → 0.99; drone $42M cumulative → 1.00.

---

## 2. Camera production cost — formulas (verbatim, $000s)

Decision cells: G4 sensor, G5 LCD, G6 resolution, G7 photo modes,
G9 housing $, G10 editing $, G11 accessories $, G13 extra features,
G14 #models, G16 R&D ($000s this year).
`AB122` = total camera units assembled (000s) = reg-time `AB119` + overtime `AB120`.
`AA135` = prior-year cumulative camera R&D ($000s).

```
AB274 = round(VLookup(G4, costs_acc_imagesensor)  * AB122, 0) * VLookup(AA135, costs_acc_reduce)   // Image Sensor
AB275 = round(VLookup(G5, costs_acc_lcddisplay)   * AB122, 0) * VLookup(AA135, costs_acc_reduce)   // LCD
AB276 = round(VLookup(G6, costs_acc_imagequality) * AB122, 0) * VLookup(AA135, costs_acc_reduce)   // Image Quality
AB277 = round(VLookup(G7, costs_acc_photomodes)   * AB122, 0) * VLookup(AA135, costs_acc_reduce)   // Photo Modes
AB278 = round(G9  * AB122, 0)    // Housing $ — NO reduce multiplier
AB279 = round(G10 * AB122, 0)    // Editing/Sharing $ — NO reduce multiplier
AB280 = round(G11 * AB122, 0)    // Accessories $ — NO reduce multiplier
AB281 = round(VLookup(G13, costs_acc_utilityfeatures) * AB122, 0)
        * VLookup(AA135, costs_acc_reduce) * VLookup(AA135, costs_acc_reduce)   // Features — reduce applied TWICE
AB282 = AB274+AB275+AB276+AB277+AB278+AB279+AB280+AB281     // Total components/features ($000s)
```

Labor & assembly ($000s). Workforce cells: `AB29` = total comp per worker
($000s) = round(AA29×(1+G219/100)); `AB25`=G220 incentive bonus $/unit;
`AB26`=G221 attendance bonus $/worker; `AB27`=G222 fringe $/worker;
`AB199` = total camera workers = PATs × workers/PAT; `AB197` = #PATs =
ceil(AB119/AB187×1000); `AB198` = 4 (3 with robotics); `AB193`=G224 training
$/PAT; `AB119`/`AB120` = reg-time/overtime units (000s):

```
AB284 = round(AB29*AB199/1e3,0) + round(AB25*AB119,0) + round(AB26*AB199/1e3,0) + round(AB27*AB199/1e3,0)  // reg-time labor
AB285 = round( (AB29/(AB195/AB198))*AB120*1.5 + AB25*AB120, 0 )                                            // overtime labor (1.5x)
AB286 = round(AB193*AB197/1e3,0)                                                                          // training
AB287 = AB284+AB285+AB286                                                                                 // Total In-House Labor
AB291 = AB282+AB287   // Total Assembly and Labor Costs
```

Note: the report template has an "Outsourcing Costs" row, but **no formula
ever adds outsourcing cost for cameras** (cameras are only built reg-time +
overtime in-house). `AB528` (drone outsourcing row) likewise has no formula.

Roll-up ($000s):

```
AB293 = AB134                        // Product R&D Expenditures (= G16, $000s this year)
AB294 = AB242 * Costs.G18            // Allowance for Warranty Repairs (AB242 = claim units 000s)
AB295 = round((Costs.G21 + AB160*Costs.G22 + AB164*Costs.G23
               + (AB166==0 ? 0 : AB164*Costs.G24) + AB1590)
              * (AB122+AB127==0 ? .25 : 1), 0)   // Maintenance of Plant & Equipment
AB296 = AB155                        // Depreciation of Plant & Equipment = round(plant_value × .05)
AB298 = AB291 + (AB293+AB294+AB295+AB296)   // Total AC Camera Production Costs ($000s)
AB300 = round(AB122==0 ? 0 : AB298/AB122, 2)     // Total AC Camera Production Cost Per Unit ($)
```

`AB1590 = (G263==0) ? 0 : round(AB122 × Costs.G44, 0)` — the CSR "Green
Initiatives" yes/no (G263) adds $G44/unit into maintenance (see §8).

### Worked sanity check (my computation, not bundle output)
Baseline camera (11mm/920k/2704×2028/8-3/$10/$10/$12/3 feats, cum R&D $63M):
component $/unit = (10+10+8+9)×0.99 + (10+10+12) + 9×0.99²
= 36.63 + 32 + 8.82 = **$77.45/unit** before labor/R&D/warranty/maintenance/depreciation.

---

## 3. Drone production cost — formulas (verbatim, $000s)

Decision cells: G22 built-in camera, G23 GPS, G24 battery, G25 rotors,
G26 rotor perf, G27 frame, G28 flight controller, G29 stabilization,
G31 extra features, G32 #models, G34 R&D ($000s).
`AB375` = total drone units assembled (000s) = in-house `AB372` + outsourced `AB373`.
`AA384` = prior-year cumulative drone R&D ($000s).
`AB300` = camera production cost/unit from §2 (AA301 = industry avg fallback).

```
AB513 = round((VLookup(G22, costs_uav_camera)*VLookup(AA384, costs_uav_reduce)
               + (AB300==0 ? AA301 : AB300)) * AB375, 0)   // Built-in camera = upgrade $ + a WHOLE camera unit cost
AB514 = round(VLookup(G23, costs_uav_gps)   * AB375, 0) * VLookup(AA384, costs_uav_reduce)   // GPS
AB515 = round(VLookup(G24, costs_uav_battery)* AB375, 0) * VLookup(AA384, costs_uav_reduce)   // Battery
AB516 = round(VLookup(G25, costs_uav_rotors)*AB375*VLookup(AA384, costs_uav_reduce)
              + VLookup(G26, costs_uav_prop)*AB375*VLookup(AA384, costs_uav_reduce), 0)        // Rotors + rotor perf
AB517 = round(VLookup(G27, costs_uav_bodyframe)     * AB375, 0) * VLookup(AA384, costs_uav_reduce)  // Frame
AB518 = round(VLookup(G28, costs_uav_controller)    * AB375, 0) * VLookup(AA384, costs_uav_reduce)  // Flight controller
AB519 = round(VLookup(G29, costs_uav_stabilization) * AB375, 0) * VLookup(AA384, costs_uav_reduce)  // Stabilization
AB520 = round(VLookup(G31, costs_uav_utilityfeatures) * AB375, 0)
        * VLookup(AA384, costs_uav_reduce) * VLookup(AA384, costs_uav_reduce)   // Features — reduce applied TWICE
AB521 = AB513+AB514+AB515+AB516+AB517+AB518+AB519+AB520   // Total components/features ($000s)
```

Drone labor ($000s). **QUIRK — read carefully:** the drone labor block reuses
the *camera* workforce-comp cells (`AB29` total comp/worker, `AB25` camera
incentive $/unit, `AB26`/`AB27` camera bonus/fringe), NOT the drone workforce
cells (`AB60` comp, `AB56`=G238 uav incentive, `AB57`=G239, `AB58`=G240).
Drone-specific quantities are used (`AB448` = drone workers, `AB372` in-house
units, `AB373` outsourced units, `AB446` = ceil(AB372/AB436×1000) workers,
`AB442`=G242 drone training $/PAT):

```
AB523 = round(AB29*AB448/1e3,0) + round(AB25*AB372,0) + round(AB26*AB448/1e3,0) + round(AB27*AB448/1e3,0)
AB524 = round((AB29/(AB444/AB447))*AB373*1.5 + AB25*AB373, 0)   // "overtime" on outsourced units
AB525 = round(AB442*AB446/1e3,0)                                // training
AB526 = AB523+AB524+AB525                                       // Total In-House Labor
AB530 = AB521+AB526   // Total Assembly and Labor Costs
AB532 = AB383                        // Product R&D (= G34, $000s)
AB533 = AB487 * Costs.G19             // Allowance for Warranty Repairs (AB487 = drone claim units 000s)
AB534 = round((Costs.G21 + AB409*Costs.G22 + AB413*Costs.G23
               + (AB415==0 ? 0 : AB413*Costs.G24) + AB1592)
              * (AB375==0 ? .25 : 1), 0)   // Maintenance
AB535 = AB404                        // Depreciation = round(drone plant value × .05)
AB537 = AB530 + (AB532+AB533+AB534+AB535)  // Total UAV Drone Production Costs ($000s)
AB539 = round(AB375==0 ? 0 : AB537/AB375, 2)     // Total UAV Drone Production Cost Per Unit ($)
```

`AB1592 = (G263==0) ? 0 : round(AB375 × Costs.G46, 0)` — Green Initiatives add
$G46/unit into drone maintenance.

### Worked sanity check (my computation)
Baseline drone (Sig camera/Enh GPS/12-min/6 rotors/Enh perf/Fiberglass/#2 ctrl/
Enh stab/5 feats, cum R&D $42M → reduce 1.00, camera unit cost $155):
$/unit = (44×1.0 + 155) + 50 + 70 + (23+17) + 17 + 45 + 18 + 90×1.0²
= 199 + 50 + 70 + 40 + 17 + 45 + 18 + 90 = **$529/unit** before
labor/R&D/warranty/maintenance/depreciation.

---

## 4. Quantities, capacity, productivity

**Camera units (000s):**
- `AB90` = AB86+87+88+89 = total camera demand (regional Demand-sheet cells).
- `AB104` = round(AB164 × AB187/1e3, 0) = reg-time assembly capacity
  (workstations × PAT productivity).
- `AB105` = round(AB104×.2, 0) = overtime capacity (20% of reg-time).
- `AB119` = min(AB90, AB104) = reg-time units; `AB120` = max(0, min(AB105,
  AB90−AB104)) = overtime units; `AB122` = AB119+AB120 = units assembled.
- `AB187` = round(AB178×(1+clamp(−.01,.1, AB180+AB181+AB182+AB183+AB184+AB185)),0)
  = PAT productivity (units/PAT/year). Impacts:
  AB180=VLookup(AB25,productivity_incentive_acc),
  AB181=VLookup(AB26,productivity_bonus), AB182=VLookup(AB27,productivity_fringe),
  AB183=VLookup(AB33/AB39,productivity_totalcomp),
  AB184=VLookup(G14 #models,productivity_acc_models),
  AB185=VLookup(max(0,(AB64−AB33)/AB33),productivity_compdiff).
  → **more models reduce PAT productivity → more PATs → higher labor cost.**

**Drone units (000s):**
- `AB353` = AB349+350+351+352 = total drone demand (regional).
- `AB361` = round(AB413 × AB436/1e3, 0) = in-house capacity;
  `AB362` = round(AB361×.2, 0) = max outsourced (20% of in-house).
- `AB372` = min(AB353, AB361) = in-house units;
  `AB373` = max(0, min(AB362, AB353−AB361)) = outsourced units;
  `AB375` = AB372+AB373 = units assembled.
- `AB436` = round(AB427×(1+clamp(−.1,.1, AB429+AB430+AB431+AB432+AB433+AB434)),0)
  = drone PAT productivity. AB429=VLookup(AB56,productivity_incentive_uav)
  (AB56=G238 uav incentive), AB430=VLookup(AB57,productivity_bonus),
  AB431=VLookup(AB58,productivity_fringe), AB432=VLookup(AB64/AB70,
  productivity_totalcomp), **AB433=VLookup(G32 #models,productivity_uav_models)**,
  AB434=VLookup(max(0,(AB33−AB64)/AB64),productivity_compdiff).

**Outsourced drone assembly:** `AB373` units get components (AB513–520 use
`AB375` = all units) and the AB524 "overtime-style" labor term, but there is
**no separate outsourcing fee formula** — the template row exists but adds $0.

---

## 5. Warranty → repair cost mapping

Tables (verbatim):

`warranty_days` (decision id → days): `[[0,0],[1,60],[2,90],[3,120],[4,180],[5,360]]`

`warranty_acc_period` (camera, id → base claim rate):
`[[0,0],[1,.03],[2,.065],[3,.105],[4,.16],[5,.38]]`
→ 60d 3%, 90d 6.5%, 120d 10.5%, **180d 16%**, 360d 38%.

`warranty_uav_period` (drone, id → base claim rate):
`[[0,0],[1,.035],[2,.075],[3,.12],[4,.2],[5,.455]]`
→ 60d 3.5%, 90d 7.5%, 120d 12%, **180d 20%**, 360d 45.5%.

`warranty_pq` (P/Q on 0–100 scale → claim-rate adder):
`[[0,.27],[3,.24],[7,.215],[10,.19],[13,.165],[16,.14],[19,.12],[22,.1],[25,.085],[28,.07],[31,.06],[34,.05],[37,.045],[40,.04],[45,.0375],[50,.0345],[55,.0315],[60,.028],[65,.0245],[70,.021],[75,.0185],[80,.016],[85,.014],[90,.0125],[95,.011],[100,.01]]`
→ higher P/Q sharply lowers claims.

`warranty_incentive_acc` (camera incentive $/unit → multiplier):
`[[0,1.5],[1.2,1.32],[1.6,1.18],[2,1.07],[2.4,1],[3,.98],[3.6,.96],[4.2,.94],[4.8,.92],[5.4,.9],[6,.88],[7,.86],[8,.84],[9,.82],[10,.8],[12,.78],[14,.76],[16,.74],[18,.72],[20,.7],[22.5,.68],[25,.66],[27.5,.64],[30,.62],[32.5,.61],[35,.6]]`

`warranty_incentive_uav` (drone incentive $/unit → multiplier):
`[[0,1.5],[1.2,1.32],[2.4,1.18],[3.6,1.07],[4.8,1],[6,.985],[8,.97],[10,.95],[12.5,.93],[15,.91],[17.5,.89],[20,.87],[22.5,.85],[25,.83],[30,.8],[35,.77],[40,.74],[45,.71],[50,.69],[60,.67],[70,.655],[80,.64],[90,.625],[100,.61],[125,.595],[150,.58]]`

`warranty_bestpractices` (training $/PAT → multiplier):
`[[0,1.5],[250,1.32],[500,1.18],[750,1.07],[1e3,1],[1250,.995],[1500,.99],[1750,.985],[2e3,.978],[2500,.97],[3e3,.962],[3500,.954],[4e3,.946],[4500,.939],[5e3,.932],[5500,.925],[6e3,.919],[6500,.913],[7e3,.907],[7500,.902],[8e3,.897],[8500,.893],[9e3,.89],[9500,.888]]`

Formulas. Camera (G74–G77 = warranty-days decision per region N.A./E-A/A-P/L.A.;
AB221 = camera P/Q 0–100; AB679/780/881/982 = camera units sold per region, 000s):

```
AB230 = VLookup(G224 training $/PAT, warranty_bestpractices)
AB231 = VLookup(G220 incentive $/unit, warranty_incentive_acc)
AB232 = VLookup(AB221, warranty_pq)
AB233..AB236 (per region) = clamp(.045, .55, (VLookup(G74..G77, warranty_acc_period) + AB232) × AB230 × AB231)
AB238..AB241 = round(region_units_sold × AB233..AB236, 1)   // anticipated claims, 000s units
AB242 = AB238+AB239+AB240+AB241                             // total camera claims
AB294 = AB242 × Costs.G18    // Allowance for Warranty Repairs ($000s); G18 = repair $/unit (server constant)
```

Drone (G161–G164 = drone warranty-days per region; AB466 = drone P/Q 0–100;
AB349–352 = drone units per region, 000s):

```
AB475 = VLookup(G242 training $/PAT, warranty_bestpractices)
AB476 = VLookup(G238 uav incentive $/unit, warranty_incentive_uav)
AB477 = VLookup(AB466, warranty_pq)
AB478..AB481 (per region) = clamp(.055, .575, (VLookup(G161..G164, warranty_uav_period) + AB477) × AB475 × AB476)
AB483..AB486 = round(region_units × AB478..AB481, 1)
AB487 = AB483+AB484+AB485+AB486
AB533 = AB487 × Costs.G19    // drone warranty allowance ($000s); G19 = repair $/unit (server constant)
AB489 = max(.015, round(AB487/AB375, 3))   // reported weighted-average claim rate
```

So: longer warranty days → higher claim rate; higher P/Q, higher incentive
$/unit, and higher training $/PAT → lower claim rate. Repair cost per unit is
a flat server constant (Costs.G18 camera, G19 drone) — no design dependence.

---

## 6. Delivery: shipping + import duties per region

Camera, per region (N.A.: units AB679, revenue AB684; E-A: AB780/AB785;
A-P: AB881/AB886; L.A.: AB982/AB987):

```
AB705 = round(AB679 × (Costs.G26 + (AB1591>0 ? Costs.G45 : 0)), 0)   // N.A. shipping ($000s)
AB706 = round(AB684 × Costs.G30/100, 0)                              // N.A. import duties ($000s)
(E-A: AB806/AB807 with Costs.G31; A-P: AB907/AB908 with Costs.G32; L.A.: AB1008/AB1009 with Costs.G33)
Reported delivery $/unit (N.A.) = (AB705+AB706)/AB679
```

Drone, per region (N.A.: units AB1154, revenue AB1156; E-A: AB1249/AB1251;
A-P: AB1344/AB1346; L.A.: AB1439/AB1441):

```
AB1176 = round(AB1154 × (Costs.G27 + (AB1593>0 ? Costs.G47 : 0)), 0)  // N.A. shipping ($000s)
AB1177 = round(AB1156 × Costs.G34/100, 0)                             // N.A. import duties ($000s)
(E-A: AB1271/AB1272 with Costs.G35; A-P: AB1366/AB1367 with Costs.G36; L.A.: AB1461/AB1462 with Costs.G37)
Reported delivery $/unit (N.A.) = (AB1176+AB1177)/AB1154
```

- Shipping = flat $/unit server constant (Costs.G26 camera, G27 drone),
  **independent of design choices and region**.
- `AB1591 = (G263==0)?0:round(AB122×Costs.G45,0)` / `AB1593` (drone, G47):
  the CSR Green-Initiatives yes/no adds $G45/$G47 per unit to shipping.
- Import duties = **ad valorem on regional revenue** (duty % × revenue),
  so duties per unit rise/fall with price — not with design directly.
  (Duty rates Costs.G30–G37 are server constants.)

---

## 7. Plant / operations costs tied to volume & capacity

- **Maintenance** (in production cost, §2/§3):
  camera `AB295 = round((Costs.G21 + AB160×Costs.G22 + AB164×Costs.G23 +
  (robotics? AB164×Costs.G24 : 0) + AB1590) × (AB122+AB127==0 ? .25 : 1), 0)`
  where AB160 = workstation spaces (prior + G227 new), AB164 = workstations.
  Drone AB534 mirrors it with AB409/AB413/AB415/AB1592.
  → per-unit maintenance falls as volume rises (fixed-ish numerator).
- **Depreciation**: camera `AB155 = round(AB153×.05, 0)`, drone
  `AB404 = round(AB402×.05, 0)` — straight 5% of plant value.
- **Facility expansion** (capital outlay, feeds plant value):
  `facility_expansion` table: `[[0,0],[10,5e3],[20,9e3],[30,13e3],[40,17e3],[60,24e3],[80,31e3],[100,37500],[125,44e3],[150,5e4]]`
  (new spaces → $000s). Camera: `AB145 = VLookup(G227, facility_expansion) +
  round((AB1596+AB1599+AB1604)×.5, 0)`; `AB146 = G226 × Costs.G9`
  (new workstations × $/workstation). Drone: `AB394`/`AB395 = G244 × Costs.G10`
  mirror with G245 spaces.
- **Robotics upgrade**: camera G230 → AB166 = robotics year; workers/PAT
  AB198 = 3 (vs 4) once installed; `AB164×Costs.G24` added maintenance;
  `AB147 = (G230…workstations…)×Costs.G12` (robotics capital). Drone G248 →
  AB415 mirrors it (Costs.G13 capital).
- **Green initiatives (G263 = yes/no)**: adds `Costs.G44`/`G46` per camera/drone
  unit into maintenance (AB1590/AB1592), `Costs.G45`/`G47` per unit into
  shipping (AB1591/AB1593), and `Costs.G48`k into admin (AB1594).
  Identified from the CSR help text: *"Green Initiatives … Increases production
  cost of AC Cameras by $… and UAV Drones by $… per unit, shipping costs of AC
  Cameras by $… and UAV Drones by $… per unit, and annual administrative costs
  by $…k."*

---

## 8. Notable quirks / exact-behavior notes

1. **Drone assembly labor uses camera workforce-comp rates.** AB523–AB525
   reference AB29/AB25/AB26/AB27 (camera total comp, camera incentive,
   camera attendance bonus, camera fringe) — not the drone cells
   AB60/AB56(AB238 uav incentive)/AB57/AB58. Drone worker *counts* and
   productivity are drone-specific. Verbatim in bundle; likely a long-standing
   game bug. Consequence: changing drone workforce comp (G237–G240, G242)
   does **not** change reported drone production labor; changing camera comp
   does.
2. **Utility-features cost gets the experience-curve multiplier squared**
   (AB281 camera, AB520 drone) — almost certainly a bug, but it is what the
   bundle computes.
3. **Housing/editing/accessories $ are NOT experience-curved** (AB278–280
   have no reduce multiplier).
4. **Every drone carries a whole camera**: AB513 adds the full camera
   production cost/unit (AB300, incl. allocated R&D/warranty/maintenance/
   depreciation) plus the upgrade VLookup cost. Improving camera *cost*
   efficiency therefore lowers drone cost; raising camera P/Q via expensive
   components raises drone cost.
5. **#models has no direct component-cost effect**, but G14/G32 reduce PAT
   productivity (productivity_acc_models / productivity_uav_models), raising
   labor cost per unit.
6. **Outsourced assembly is free**: drone outsourced units (AB373, up to 20%
   of in-house capacity) incur component + AB524-style labor cost but no
   outsourcing fee; the "Outsourcing Costs" report rows have no formula.
7. Camera overtime is capped at 20% of reg-time capacity (AB105); drones
   outsource instead of overtime.
8. Warranty claim rates are clamped: camera [4.5%, 55%], drone [5.5%, 57.5%]
   per region.

---

## 9. Code anchors (byte offsets in /tmp/glo-main.js)

| What | Anchor |
|---|---|
| 16 cost tables | `costs_acc_imagesensor:[[` at **439,667** … `costs_uav_utilityfeatures:[[` at **440,899** (object spans ~439,591–440,990) |
| Camera components AB274–AB282 | `t.CoData.AB274=` at **1,059,593** |
| Camera labor AB284–AB287 | `t.CoData.AB284=` at **1,061,057** |
| Camera roll-up AB291–AB300 | `t.CoData.AB291=` at **1,061,830** |
| Drone components AB513–AB521 | `t.CoData.AB513=` at **1,063,601** |
| Drone labor AB523–AB526 | `t.CoData.AB523=` at **1,067,190** |
| Drone warranty AB475–AB487 | `t.CoData.AB475=` at **1,068,031** |
| Drone roll-up AB530–AB539 | `t.CoData.AB530=` at **1,171,983** |
| Camera delivery AB705–AB1009 | `t.CoData.AB705=` at **1,074,289** |
| Drone delivery AB1176–AB1462 | `t.CoData.AB1176=` at **1,081,826** |
| Warranty tables | `warranty_acc_period:[[` at **459,695**, `warranty_days` 460,056, `warranty_uav_period` 460,917, `warranty_pq` 460,651 |
| VLookup / excelRound helpers | `VLookup(n,e){` and `excelRound(n,e){` adjacent (~byte 452,xxx) |
| Green-initiatives help text | search `Green` + `Increases production cost of AC Cameras` |
| Report mappings | `"DecDesign"in t` (~1,230,364), `"DecAccMarketing"in t` (1,230,410), `"DecUavMarketing"in t` |

## 10. Unresolved (server-provided `Costs.G<n>` constants, not in bundle)

G9 (camera $/workstation), G10 (drone $/workstation), G12/G13 (robotics $/workstation),
G18 (camera warranty repair $/unit), G19 (drone warranty repair $/unit),
G21 (maintenance base $000s), G22 ($/workstation space), G23 ($/workstation),
G24 (robotics $/workstation), G26 (camera shipping $/unit), G27 (drone shipping $/unit),
G30–G33 (camera duty % by region), G34–G37 (drone duty % by region),
G44/G45 (green: camera production/shipping $/unit), G46/G47 (green: drone),
G48 (green admin $000s), G49/G52/G53/G56 (facility/robotics one-offs).
Values must come from live read-only report reads (e.g. benchmarking pages),
not from this bundle.

## 11. Suggested next step for the engine

`pq.py`'s table mechanism can be reused directly: add the 16 `costs_*` tables
plus `warranty_*` and `facility_expansion` to a `cost_tables.json`, implement
the AB274–AB300 / AB513–AB539 formula chains with the workforce/productivity
cells, and calibrate the §10 constants against live report reads. The two
known formula quirks (§8.1, §8.2) must be replicated exactly, not "fixed".
