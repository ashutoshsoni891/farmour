# Integrated Farming Venture — Platform + Own Land Design

Sep 28, 2026 · @Aashutosh

## Summary

Run the two ideas as one loop: the land is the lab, the software is the product, and each makes the other credible. Keep consulting as the main income, test for six months on the 800 sq ft plot and a leased patch, then buy land only if the tests pass.

- **Track 1 — Platform:** a lean MVP where the owner pins and draws the land, the platform fills in soil, climate, water stress and local mandi prices by itself, and returns a zoned multilayer plan, weekly Hindi tasks for the caretaker, a shopping list and a profit view.
- **Track 2 — Own land:** about 2 acres, 50–70 km from Indore, Rs 60 lakh total budget, horticulture-first (dragon fruit, guava or sitaphal, lemon) with a small multilayer vegetable patch, so it becomes semi-passive once trees bear.
- **Money, honestly:** crops alone give roughly Rs 4–7 lakh a year from 2 acres by year 3–4 after a caretaker; farm visits, adopt-a-bed, nursery and a small brand can add Rs 3–5 lakh. The farm alone won't match a tech salary; farm plus platform can, over 3–5 years.
- **Why together:** the farm is the platform's first user, showroom and data source; the platform turns that know-how into income that doesn't depend on one monsoon.

## Reference models

Borrow the bed design from Chaurasia and the farm-level zoning and input discipline from Tyagi; the others fill in soil and orchard practice.

| Model | Core idea | Reported results | What to borrow |
| --- | --- | --- | --- |
| [Akash Chaurasia](https://www.downtoearth.org.in/agriculture/akash-chaurasia-a-millionaire-farmer-from-bundelkhand-64365), Sagar MP | Multilayer: 4–5 crops on one bed at different heights — root crop underground (ginger/turmeric), leafy greens on the surface, vine vegetables on a bamboo-and-wire pavilion, fruit or shade trees above | About Rs 15 lakh a year from 2.5 acres including vermicompost, bio-pesticide and milk; claims up to Rs 8 lakh/acre from the multilayer beds ([Bharat Express](https://english.bharatexpress.com/india/youth-abandoning-farming-progressive-farmer-akash-chaurasia-shows-the-way-with-multi-layer-farming-161631)); leafy surface layer controls about 80% of weeds ([Better India](https://thebetterindia.com/289209/national-award-winning-farmer-akash-chaurasia-uses-multilayer-farming-to-earn-lakhs/)) | Bed geometry, pavilion structure (about Rs 25,000/year, lasts 5 years), indigenous seeds, on-farm vermicompost; free training on the 27th–28th of each month in Sagar |
| [Bharat Bhushan Tyagi](https://en.wikipedia.org/wiki/Bharat_Bhushan_Tyagi), Bulandshahr UP (Padma Shri 2019) | SAMAK — co-existence based cyclical farming: "one field, many crops", zones for perennials, border and rotation, crop diversity instead of purchased inputs | Co-cropping roughly halved his water use ([Bharat Express](https://english.bharatexpress.com/india/padma-shri-bharat-bhushan-tyagi-revolutionizes-farming-with-organic-methods-169778)); 80,000+ farmers trained | Farm-level zoning, rotation logic, and his four pillars: production, certification, processing, marketing |
| Subhash Palekar (approximate, from general knowledge) | Zero-budget natural farming: jeevamrut, beejamrut, mulching, 5-layer orchard (tall, mid, shrub, creeper, ground) | Widely adopted in AP and Maharashtra; yields debated | Liquid inputs recipes, mulching, 5-layer fruit block |
| Natueco / Deepak Suchde (approximate) | Soil-life first, "amrut mitti" beds, light harvesting | Small-plot demonstrations | Soil-building for your clayey plot and terraces |

A caution on numbers: the income figures above are self-reported in media stories, cover allied income (dairy, compost, training), and come from farmers with a decade of practice. Plan on 30–40% of them in your first two years.

## Unified farm design framework

Both tracks use the same model: a parcel is split into zones, each zone is split into vertical layers, and all waste returns as compost. The platform encodes this model; your land runs it.

&#91;embedded content: integrated farm zone model · 6 zones inside a live border\]

Zone shares scale with plot size. A starting split for 1 acre:

| Zone | Share of area | Main income role | Time to first income |
| --- | --- | --- | --- |
| Multilayer vegetable beds | 35% | Weekly cash from greens and vegetables | 45–90 days |
| Orchard, 5 layers | 25% | Long-term, low-labour income | 12–36 months (papaya, banana first) |
| Rotation field | 20% | Grains and pulses for home and value-added sale | One season |
| Border | 8% | Moringa, lemongrass, bamboo; protection | 6–12 months |
| Water | 7% | Enables everything; fish later if the pond holds | — |
| Utility and livestock | 5% | Vermicompost and inputs for sale to other growers | 60–90 days |

For rooftops and small plots such as your 800 sq ft, the same model shrinks: border becomes containers of lemongrass and herbs, the orchard becomes 2–3 dwarf fruit trees, and the beds carry most of the design.

**Rules the model enforces** (these become platform logic):

1. Every bed carries at least three layers: root, surface, climber or canopy.
2. No zone uses a purchased input that the utility zone can make.
3. Tall layers go on the north side so they never shade beds in winter; west-side cover is added only to shield heat-sensitive crops from May afternoons.
4. Water is sized to the driest month, not the average.

## Track 1 — Software platform

Build a planner first, not a sensor product: the defensible value is turning a real parcel into a zoned, layered, costed plan, then tracking whether it earns.

The full MVP build spec (architecture, data model, rules, APIs) is in MVP technical spec. The MVP excludes IoT and hardware.

&#91;embedded content: platform modules · 4 stages + shared knowledge base\]

### Who it serves

| Segment | Land size | What they need | Willingness to pay |
| --- | --- | --- | --- |
| Urban terrace and backyard growers | 100–2,000 sq ft | A layout, what to plant this month, simple logs | Low; freemium |
| Weekend / NRI farm owners | 0.5–5 acres | Full design, caretaker task list, profit visibility from afar | High; best first paying segment |
| Small farmers moving to organic | 1–5 acres | Multilayer plan, input recipes, buyer links | Low direct; reach via FPOs and NGOs |
| FPOs, agri-NGOs, CSR programs | Many plots | Plan and monitor hundreds of farms, reports | High; B2B licences |

### What the user gives, and what the platform finds by itself

| Asked from the user | Found automatically from the location, then confirmed by the user |
| --- | --- |
| Location pin and land boundary (draw on the map or type measurements) | Soil type, texture and pH (likely), slope and low side |
| Water source and roughly how much is available in summer | Rainfall and temperature by month, hottest and coldest months, monsoon onset |
| Goal: home food, income, or both | Groundwater stress of the block (safe to over-exploited) |
| Setup budget and who will do the work | Nearest mandis, their recent prices per crop, distance and transport cost |
| Start date; crops wanted or not wanted (optional) | Nearby nurseries, input shops, gaushalas, KVK; possible subsidies |

### What the user gets

- A to-scale layout: border, orchard, multilayer beds, water, nursery and utility zones, numbered beds
- Crops for each bed's four layers, per season, with plant counts and spacing
- Water check against summer availability, setup cost, and expected income at local prices after transport (clearly marked as estimates)
- Weekly and daily tasks for the caretaker in Hindi on Telegram, with one-tap replies
- A seasonal shopping list: what to buy, how much, rough cost and where nearby
- Harvest, cost and sale logs, profit per zone, plan versus actual
- Answers to questions from the AI helper, grounded in a crop library reviewed by an agronomist

### How it works

- **Design engine:** rules first, AI second. A constraint solver places zones and beds on the polygon using the crop library and the rules above; an LLM explains the plan and handles edge cases.
- **Data sources:** PostGIS for parcels, Sentinel-2 NDVI for crop health, IMD or Open-Meteo for weather, Soil Health Card data where available.
- **Stack:** matches your core — FastAPI with open-source Postgres + PostGIS and S3-compatible storage, self-hosted on a free or low-cost server, a React PWA with offline logging plus WhatsApp for caretakers, LangGraph agent over a RAG crop library.

### MVP scope (lean, about 13–15 weeks of evenings)

- [ ] Plan: location + boundary → site intelligence → confirmed site profile → zoned multilayer plan
- [ ] Tasks to the caretaker on Telegram in Hindi (WhatsApp later)
- [ ] Logs: harvest, cost, sale, photo
- [ ] Money: profit per zone, plan versus actual
- [ ] AI helper: text questions and answers
- [ ] Shopping list per season
- [ ] Legal basics: terms, privacy, estimates disclaimer, data export and delete
- [ ] Pilot on the 800 sq ft plot, then 5–10 beta users

After the MVP: weather alerts, photo diagnosis, plan PDF, WhatsApp, selling helper, how-to guides, season report, then IoT, FPO dashboards and a marketplace.

### Monetisation

| Plan | Price (monthly) | For |
| --- | --- | --- |
| Free | Rs 0 | One plot under 2,000 sq ft, basic plan |
| Grower | Rs 299 | One farm, full design, calendar, logs |
| Farm owner | Rs 999 | Up to 5 acres, caretaker app, profit reports |
| Organisation | Rs 25,000+ | FPOs and NGOs, many farms, reports |

Add-ons: paid on-site design visits (Rs 5,000–15,000), a course built from your own farm, and a commission on input kits and produce sales.

### Existing platforms and where this fits

| Type | Examples | What they do | Gap this platform fills |
| --- | --- | --- | --- |
| Indian crop advisory and inputs | Gramophone (Indore; acquired by Unnati in Jan 2026), BharatAgri, AgroStar, DeHaat, Plantix | Single-crop advice, disease photos, input sales | No layout design, no multilayer or organic-first plan |
| Precision farming | Fasal, Fyllo | Sensors and irrigation data | Hardware-first, no planning |
| Garden planners | GrowVeg, VegPlotter, Old Farmer's Almanac planner | Draw beds, planting calendar | Western climates, English only, no caretaker or money flow |
| Open-source farm records | farmOS, LiteFarm | Logs, maps, records | Record-keeping, not design; worth reusing ideas |

Position it as "design and run a multilayer organic farm on your land", not "AI farming advice" ([Decentro](https://decentro.tech/blog/agritech-startups/), [Khetiyaar](https://www.khetiyaar.com/en/blog/best-ai-farming-apps-india)).

## Track 2 — Own land

Target about 2 acres, 50–70 km from Indore, with a working bore or canal and a road to the gate, within a total budget of Rs 60 lakh. Run the six-month test below before buying.

### Where and what to buy

Prices near Indore split sharply by distance. Peri-urban land is priced for plotting, not farming: one listing asks Rs 4 crore for 3 bigha at Kampel, while rural listings run far lower, such as 3.5 acres near Khandwa for Rs 12.5 lakh ([99acres](https://www.99acres.com/agricultural-land-in-indore-ffid), [RealEstateIndia](https://www.realestateindia.com/indore-property/farm-land-for-sale-price-1-lakh-to-5-lakhs.htm)). Rough bands from listings, to be confirmed on the ground:

| Distance from Indore | Example areas | Approx. price per acre | Fit |
| --- | --- | --- | --- |
| Under 25 km | Kampel, Sulakhedi, Baigram | Rs 1 crore and up | Poor: you pay for plotting value |
| 25–50 km | Sanwer, Depalpur, Mhow–Manpur belt | Rs 25–60 lakh | Good: weekend reach, city buyers |
| 50–90 km | Dewas, Dhar, Khargone side villages | Rs 8–25 lakh | Best cost; needs a resident caretaker |

**Must-haves:** bore yield checked in May, not after monsoon; black soil with drainage or a slope (Malwa black cotton soil waterlogs); three-phase power nearby; all-weather road; no tribal-land (Section 165(6)) or government-land issues.

**Title checks:** Khasra, B-1 and naksha from [MP Bhulekh](https://mpbhulekh.gov.in), 30-year title chain, demarcation by the Patwari, encumbrance search, and a local lawyer's opinion. Farming needs no diversion; a farmhouse or processing shed may.

### Budget split for Rs 60 lakh (approximate)

| Use | Amount | Why |
| --- | --- | --- |
| Land, about 2 acres | Rs 38–42 lakh | Roughly Rs 18–22 lakh an acre at this distance; confirm locally |
| Registry, stamp duty, lawyer, demarcation | Rs 3–4 lakh | Real cost often forgotten |
| Setup: bore, pond, drip, fencing, dragon fruit poles, saplings, shed, caretaker room | Rs 12–14 lakh | Can drop 20–30% with horticulture and drip subsidies |
| Running-cost reserve for years 1–2 | Rs 4–5 lakh | Caretaker and inputs before income starts |

In MP one bigha is roughly 0.6 acre but varies by area; write deals in acres or hectares with khasra numbers.

### Horticulture-first layout for 2 acres

| Part | Area | Mature profit (approx.) |
| --- | --- | --- |
| Dragon fruit | 0.75 acre | Rs 3–4.5 lakh a year |
| Guava, sitaphal and lemon orchard, with papaya and marigold between young trees in years 1–2 | 0.75 acre | Rs 1.5–2.5 lakh |
| Multilayer vegetable beds and nursery | 0.25 acre | Rs 1–1.5 lakh |
| Pond, border (moringa, lemongrass), shed, caretaker room | 0.25 acre | Small |
| Caretaker family | — | −Rs 1.8 lakh |
| **Crops total from year 3–4** |  | **about Rs 4–7 lakh** |

Trees mean less daily labour and a longer life than vegetables, which is what makes the farm semi-passive later.

### Crop calendar (Malwa)

| Season | Beds (root / surface / climber) | Orchard | Rotation field |
| --- | --- | --- | --- |
| Kharif (Jun–Oct) | Ginger or turmeric / amaranth, okra / bottle gourd, ridge gourd | Plant saplings in July | Soybean or moong |
| Rabi (Nov–Mar) | Carrot, radish, beet / spinach, methi, coriander / peas, beans | Mulch, intercrop greens | Chana or wheat |
| Zaid (Mar–Jun) | Onion, garlic harvest / cucumber / bitter gourd under net | Papaya, banana harvest | Green manure (dhaincha) |

### Passive versus active

In years 1–2 this is a job: plan on 10–15 hours a week from you plus one resident caretaker family (about Rs 12,000–18,000 a month, approximate). It becomes semi-passive once three things exist: perennials bearing, a fixed buyer list (weekly vegetable boxes to Indore households, a restaurant or two), and the caretaker running the platform's task list without you.

### Earning more from the same land

| Add-on | Rough extra profit a year | Note |
| --- | --- | --- |
| Farm visits and workshops | Rs 2–2.5 lakh | Schools and families from Indore; the orchard makes it attractive |
| Adopt-a-bed for city families | Rs 2–2.5 lakh | About 30 families paying monthly for a bed you tend |
| Microgreens for cafes and homes | Rs 1.5–2 lakh | Racks inside the shed |
| Oyster mushrooms | Rs 1–1.5 lakh | A 300 sq ft room |
| Nursery (dragon fruit cuttings, saplings, seedlings) | Rs 1 lakh | Also feeds platform users |

These are small businesses, not passive income: each needs customers and your time, so add them one at a time.

### Six-month test before buying (Oct 2026 – Mar 2027)

| Test | Cost | Pass if |
| --- | --- | --- |
| Sell 2–3 organic products from partner farmers | Rs 2–3 lakh | 40+ repeat customers |
| Run the 800 sq ft plot as a full multilayer demo | Small | You still enjoy it after a full season |
| Build the platform MVP and use it on your plot | Your evenings | 5–10 people use it and give feedback |
| Visit 8–10 plots and test water in April–May | Travel | 1–2 plots with good water and clean title |
| Agree the plan and budget at home | — | Both of you agree on the goal |

If 3–4 pass, buy in April–May 2027 and plant in the July 2027 monsoon. If most fail, keep the money invested; you've spent Rs 3–5 lakh to learn it instead of Rs 60 lakh.

**Alternative for purely passive income:** a rented shop or small office in Indore yields rent from month one (roughly 5–7% of cost a year) with almost no effort, but doesn't build the farm or platform. One option is rent first, farmland later once the tests pass.

## Financials

One acre of crops needs about Rs 7.7 lakh of setup beyond the land. Who does the work decides whether it pays back: doing it yourself on owned land repays setup in year 4, while a hired caretaker on leased land keeps it below zero through year 5 unless add-on income is layered on.

&#91;embedded content: planning estimates · 1 acre · 5 years · 2 labour scenarios · land excluded\]

In a normal year (year 3 onward), direct selling brings about Rs 5.8 lakh per acre against Rs 1.9 lakh of running cost when you do the work, or about Rs 4 lakh with a caretaker and lease. Selling at the mandi instead roughly halves income and turns the caretaker scenario into a loss, so direct buyers matter more than any growing technique.

### Setup cost for 1 acre (land excluded)

| Item | Approx. cost (Rs) | Note |
| --- | --- | --- |
| Bamboo and wire pavilions, 12 units | 1.25 lakh | Lasts about 5 years |
| Drip and mulch | 70,000 | MP horticulture subsidy may cover part |
| Lined pond and bore or pump | 1.5–2 lakh | Solar pump subsidy under PM-KUSUM |
| Fencing, live plus wire | 1 lakh |  |
| Shed, store, vermicompost unit, nursery | 2.5 lakh |  |
| Saplings, seeds, first inputs | 50,000 | Indigenous seeds cut this later |

### Yearly running cost

About Rs 3.6–4.2 lakh: caretaker family (Rs 1.8 lakh), casual labour at peaks, seeds and inputs, transport to Indore, power and repairs.

### Revenue streams, in order of reliability

1. Weekly organic vegetable and greens boxes to 60–100 Indore households at a premium
2. Vermicompost, jeevamrut and seedlings sold to terrace growers (overlaps with platform users)
3. Fruit from year 3: papaya and banana first, then guava and lemon
4. Value-added: turmeric powder, cold-pressed oil, millet flour
5. Farm visits and paid workshops once the farm is presentable

### Lease or buy

Lease or partner on a small patch during the six-month test and put the platform pilot on it; buy only if the tests pass. On the 2-acre horticulture plan, Rs 4–7 lakh a year from crops on a Rs 60 lakh total budget is roughly 7–12% a year once mature, before land appreciation. I'm not a financial advisor; check this against your wider finances before committing.

### Platform economics

Running cost is low: roughly Rs 0–2,000 a month at pilot scale on an open-source, self-hosted stack, mainly LLM calls, and your own evenings. A month-18 target of 200 Grower, 50 Farm owner and 2 Organisation plans is about Rs 1.6 lakh a month; design visits and courses come on top.

## Risks and mitigations

The biggest risks are selling, not growing: a farm without buyers and a platform without paying users both fail quietly.

| Risk | Likelihood | Mitigation |
| --- | --- | --- |
| No steady buyers for organic produce | High | Pre-sell 40 weekly boxes before scaling beds; start with your own network and residential societies |
| Caretaker leaves or underperforms | High | Housing on site, profit share on sales, task list and photo logs in the field app |
| Land title or boundary dispute | Medium | Full title search, Patwari demarcation, lease first |
| Water fails in April–May | Medium | Check bore in summer, pond sized to driest month, mulch everywhere |
| Waterlogging on black soil | Medium | Raised beds, drainage channels, slope check before buying |
| Pests in year 1 while soil is still weak | Medium | Neem and dashparni ark, trap crops on borders, accept 20–30% loss in year 1 |
| Organic premium without certification | Medium | PGS-India group certification (low cost) and farm visits for trust |
| Platform becomes a hobby with no revenue | Medium | Charge from the first design visit; target weekend farm owners, not smallholders, first |
| Full-time switch too early | Medium | Leave consulting only when farm plus platform cover 12 months of expenses for two straight quarters |

## Phased roadmap

Three phases over three years, each ending in a gate you must pass before spending more; consulting stays on until the final gate.

&#91;embedded content: roadmap · 3 phases, 2 gates and a switch point\]

If a gate is missed, repeat the phase for one more season rather than pushing capital into the next one.

## Open decisions and next steps

**Decisions still open:**

- Is the setup budget a required input, or optional with a low-cost default?
- MVP land range: terrace to 2 acres only, or up to 5 acres?
- Show income estimates to every user, or only when the goal includes income?
- Should the owner approve the plan before tasks start?
- Domain: getfarmap.com (if no active "Farmap" product exists) or khetplan.com.

**Next 30 days:**

- [ ] Register the domain and matching social handles
- [ ] Find a part-time agronomist (KVK Indore or College of Agriculture, Indore) for the crop library
- [ ] Contact KVK Indore and NABARD's Indore office for a list of active FPOs; visit 2–3
- [ ] Start the 800 sq ft plot for the rabi season as the first live farm
- [ ] Build M0 of the platform: open-source stack on a free server
- [ ] Visit Akash Chaurasia's training (27th–28th of the month) and record bed dimensions
- [ ] Sign up 10 households for a trial vegetable box

### Sources

- [Down To Earth — Akash Chaurasia profile](https://www.downtoearth.org.in/agriculture/akash-chaurasia-a-millionaire-farmer-from-bundelkhand-64365)
- [Bharat Express — Chaurasia multilayer method](https://english.bharatexpress.com/india/youth-abandoning-farming-progressive-farmer-akash-chaurasia-shows-the-way-with-multi-layer-farming-161631)
- [The Better India — Chaurasia weed control and training](https://thebetterindia.com/289209/national-award-winning-farmer-akash-chaurasia-uses-multilayer-farming-to-earn-lakhs/)
- [Wikipedia — Bharat Bhushan Tyagi](https://en.wikipedia.org/wiki/Bharat_Bhushan_Tyagi)
- [Bharat Express — Tyagi organic methods](https://english.bharatexpress.com/india/padma-shri-bharat-bhushan-tyagi-revolutionizes-farming-with-organic-methods-169778)
- [99acres — agricultural land listings, Indore](https://www.99acres.com/agricultural-land-in-indore-ffid)
- [RealEstateIndia — low-budget farm land listings, Indore](https://www.realestateindia.com/indore-property/farm-land-for-sale-price-1-lakh-to-5-lakhs.htm)
- [Decentro — agritech startups in India 2026](https://decentro.tech/blog/agritech-startups/)
- [Khetiyaar — farming apps comparison](https://www.khetiyaar.com/en/blog/best-ai-farming-apps-india)
