## 9. Records, profit and weather alerts

Every number on the owner's dashboard traces back to a `logs` row or a plan estimate, and the UI always labels which is which.

### Logging

- Harvest: bed (required), crop (defaults to what's in that bed), quantity + unit; converting bunch or piece to kg uses a per-crop factor in the library (optional).
- Cost: amount, category (`seed`, `input`, `labour`, `water`, `transport`, `tools`, `setup`, `other`), optional bed, optional photo of the bill.
- Sale: crop, quantity, amount, buyer type (`household`, `shop`, `restaurant`, `mandi`, `other`).
- Photo / issue / note: optional bed; an issue photo triggers the photo check (section 11).
- Offline logs carry `client_uuid`; the server ignores duplicates.
- Logs can be edited by their creator for 48 hours and by the owner anytime; every edit goes to `audit_log`.

### Calculations

```text
revenue(period)          = Σ sale.amount
home_use_value(period)   = (Σ harvest.kg − Σ sold.kg) × crop.price_direct   -- shown separately, never mixed into revenue
running_cost(period)     = Σ cost.amount where category ≠ 'setup'
setup_amortised(period)  = Σ setup costs ÷ amortisation_years (setting, default 5), pro-rated to the period
profit(period)           = revenue − running_cost − setup_amortised
zone_profit              = same, filtered by bed → zone; unassigned costs split by zone area share
plan_vs_actual(planting) = Σ harvest.kg ÷ expected_yield_kg   -- green ≥ 0.8, amber 0.5–0.8, red < 0.5
payback_month            = first month where cumulative profit incl. full setup ≥ 0
```

Periods: this week, this month, this season (kharif Jun–Oct, rabi Nov–Mar, zaid Mar–Jun), last 12 months, since start. Money is stored in paise and computed in integers; display rounds to rupees.

### Weather alerts (post-MVP)

A daily job at 05:30 IST fetches the Open-Meteo 7-day forecast once per 0.1° grid cell (farms share cells), stores a snapshot, and evaluates rules. Thresholds are defaults in `settings`, to be tuned with the agronomist.

| Alert | Trigger (default) | Actions |
| --- | --- | --- |
| Heat | Max temp ≥ 42 °C on any of the next 3 days (severe ≥ 45 °C) | Shade net on leafy beds, water early morning, mulch check |
| Heavy rain | ≥ 50 mm forecast in a day | Move sowing and recipe tasks, clear drainage, check raised beds |
| Strong wind | Gusts ≥ 40 km/h | Check trellis ties; terrace: secure shade net and light pots |
| Cold | Min temp ≤ 4 °C | Cover nursery and tender seedlings overnight |
| Dry spell | No rain for 10 days in Jul–Sep | Irrigation check, mulch |

- Max one alert message per farm per day; combine multiple alerts into one. Severe alerts can send immediately.
- Each alert creates `weather_action` tasks and reschedules tasks as in section 8.
- If Open-Meteo is unreachable, retry 3 times with backoff; after that, skip alerts for the day and log an error, never send stale warnings.

