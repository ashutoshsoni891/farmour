# Vision

Last updated: 2026-10-05. Scope and numbers live in `docs/spec/`; this page is the "why" and the direction. Where it differs from the spec, `docs/decisions.md` records the change.

## The problem
"I have land, but I don't know what to grow where and when, my caretaker or family doesn't know
what to do each day, and I can't tell whether it's making money." (spec §1)

Most farmers grow one crop (monocropping) with bought fertiliser. Land owners who want more
(organic, natural, multilayer, horticulture, integrated) lack the knowledge, the execution
routine and the numbers.

## The product
One system that takes a land owner or farmer from "here is my land and what I want" to a plan,
weekly work, records and profit, farmed organically and naturally to its full potential.
AI helps explain and adapt, but the rule engine and the cited crop library decide.

## Who it is for
- **Owner + caretaker:** owns 1 bigha to a few acres, does not farm full time; a local worker or
  farmer does the work and gets Hindi tasks on Telegram.
- **Owner-farmer:** the same person plans and works. The caretaker is optional.
- Not in scope any more: terrace and kitchen gardens (the map and satellite data suit 1 bigha+).
- First beta: the project owner's own land, then 5-10 others (spec §15, M8).

## Users in more detail
| User | What they want | What we give them |
|---|---|---|
| Owner (not on the land) | Know what to grow, see that work is done, know if it earns | Plan, weekly status, logs, profit |
| Owner-farmer | A plan and a routine; no separate caretaker | The same plan and tasks addressed to themselves |
| Caretaker (local worker or farmer) | Clear Hindi tasks, no money details | Weekly and daily tasks on Telegram, done / not done replies |
| Agronomist (reviewer) | Review and approve crop and scheme data | Review screens (not shown to farmers) |

Farmers never see crop, manure or recipe catalogues; the system chooses and explains.
The owner's own answer always overrides what the system found or suggested.

## The goal
The goal is the main input to the plan, asked once and editable later. Examples of goals the
owner may have (the final list is config, not code): earn the most income, earn steadily with
little labour and risk, grow the family's own food and build the soil, or a mix.
- The plan engine produces five plan options for the same land (Most income, Balanced, Low work,
  Family food and soil, Water saver) with the trade-offs shown (harvest, water, work; money once
  cost data exists). The owner picks one, can change land use, bed size or a crop, and can switch
  later. (Built 2026-10-06.)
- The goal also steers which schemes are shown and which structures (drip, polyhouse, orchard)
  are suggested.

## The pillars
1. **Farming methods:** multilayer, horticulture, organic, natural, integrated; polyhouse and
   other structures later (spec §16 lists polyhouse as a future zone template).
2. **Goal / business model:** the owner's goal drives the plan. The engine should offer 2-3
   competing plans for the same land (income-first, low-labour and low-risk, self-sufficient and
   soil-building) with the trade-offs shown, and the owner picks.
3. **Location intelligence:** soil, climate, water, terrain, markets and mandi prices, road
   distance (built or partly built); electricity, wind, groundwater, water source (missing).
4. **Crop intelligence:** the cited crop library. Shells exist, values are empty: the biggest gap.
5. **Combination intelligence:** which crop goes with which, where and when (layers, companions,
   rotation). Core of the design engine (M3).
6. **Schemes and benefits:** government schemes, subsidies, loans and rebates matched to the
   owner's goal and plan, shown with documents needed and where to apply.
   - Same pattern as the crop library: cited source, `last_verified` date, status
     `draft` / `ai_verified` / `approved`; eligibility stored as structured rules the engine
     matches; AI only explains.
   - Always "may be eligible", never "you qualify"; confirm at the district office.
   - Subsidy is shown beside the setup cost, never subtracted automatically (spec §17).
   - Apply-by tasks appear in the weekly plan (M4). We do not apply on the owner's behalf.
   - Each entry holds: name (en, hi), level (central / state / district), benefit type
     (subsidy, loan, interest rebate, insurance, direct benefit, training), what it gives,
     eligibility rules, documents needed, where to apply, source link, last-verified date, status.
   - Examples to research and cite first (not yet verified): PM-KISAN, PMKSY micro-irrigation,
     MIDH / National Horticulture Mission, PM-KUSUM solar pumps, Agriculture Infrastructure
     Fund, Kisan Credit Card, PMFBY crop insurance, organic and natural farming missions, plus
     Madhya Pradesh schemes.
   - Eligibility can depend on the person (for example farmer status or land records), so an
     owner who is not a farmer may see different results from an owner-farmer.

## The loop
Plan -> weekly tasks -> logs -> profit -> better next plan. The map makes it real (the owner sees
their own field); the loop makes it a habit.

## Map and land data (decided 2026-10-05)
- MapLibre with a replaceable satellite provider (Google Map Tiles chosen; Esri dev-only).
- Possible parcel import from MP land records (Bhulekh/Bhunaksha); access and terms unverified.
- Not planned: buying commercial satellite imagery per farm.

## Principles
- Estimates are labelled estimates; agronomy facts come only from the crop library.
- Owner stays in control: engine proposes, owner chooses, owner's answer always wins.
- Ask the owner for as little as possible; discover the rest.
- Widen scope only after M3 works end to end on the first farm (own land).

## Open questions
- A sixth path item was cut off in the discussion ("5. mar..."): possibly marketing/market
  linkage. To confirm.
- Home screen pitch: "make your land earn" or "run your farm remotely".
- Map provider: test Google, Mapbox, MapTiler on the real plots (needs keys).
