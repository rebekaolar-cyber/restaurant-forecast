# Baseline forecast: backtest against the manager's plan

Period: 2026-07-10 to 2026-10-09, 84 evenings scored, dinner shift. Average 119.8 guests per evening.

Not scored: 4 evening(s) when the restaurant was closed (Mondays before 10 August 2026) and 4 Monday(s) right after it opened, when there were not yet 3 earlier Mondays to average.

Data: fake history rebuilt from the saved weather file `daily_weather_2024-10-09_to_2026-10-23.csv` with seed 20261010, as of 2026-10-10 03:00 Amsterdam time.

**This is fake history.** It shows the method works on data shaped like the restaurant's. It does not show how good the forecast is on the restaurant's real evenings.

## Average error in guests per evening

Lower is better. "Days ahead" counts as the nightly job writes it: day 1 is the evening of the day the job runs, day 14 is thirteen days later.

| Days ahead | Our forecast | Weekday average alone | Manager's plan | Manager's plan x 0.70 |
|---|---|---|---|---|
| 1 | 13.0 | 14.5 | 51.9 | 13.9 |
| 3 | 14.7 | 14.5 | 51.9 | 13.9 |
| 7 | 15.8 | 14.5 | 51.9 | 13.9 |
| 14 | 16.8 | 14.5 | 51.9 | 13.9 |

- **Our forecast**: the average of the same weekday over the last 6 weeks, corrected by how the bookings already made compare with what is normal that many days ahead.
- **Weekday average alone**: the same without looking at the bookings. The difference between these two columns is what the reservation book adds.
- **Manager's plan**: Mon 100, Tue 100, Wed 100, Thu 120, Fri 250, Sat 300, Sun 180, every week.
- **Manager's plan x 0.70**: his plan scaled by 174/250, the one real Friday we know (47 reservations, 174 people against 250 planned). In this fake history that is exactly the level the evenings were built around, so it is the best any fixed weekly plan could do here. Nobody has that number for the real restaurant.

Verdict: our forecast beats the manager's plan at every distance.

## Why the plan is so far off here

The fake history was built about 30% below his plan on every weekday, because the one real number we have says so for a Friday. That is an assumption for the other six days. Most of the plan's error in the table above comes from this level difference, not from anything clever in the forecast. Compare our forecast with the last column to see what it adds beyond the level.

| Weekday | Evenings | Average guests (fake) | Manager's plan |
|---|---|---|---|
| Monday | 5 | 78.4 | 100 |
| Tuesday | 13 | 76.1 | 100 |
| Wednesday | 13 | 77.9 | 100 |
| Thursday | 13 | 81.6 | 120 |
| Friday | 14 | 165.4 | 250 |
| Saturday | 13 | 202.1 | 300 |
| Sunday | 13 | 127.8 | 180 |

## A longer look: the months before

The same comparison for 2024-12-04 to 2026-07-09 (500 evenings, average 116.8 guests). Three summer months are a small sample without a single public holiday. This longer period has Christmas, Easter and the quiet January weeks in it, which is where the reservation book earns its place.

| Days ahead | Our forecast | Weekday average alone | Manager's plan | Manager's plan x 0.70 |
|---|---|---|---|---|
| 1 | 13.3 | 19.7 | 59.0 | 18.9 |
| 3 | 15.3 | 19.7 | 59.0 | 18.9 |
| 7 | 17.3 | 19.7 | 59.0 | 18.9 |
| 14 | 19.5 | 20.4 | 59.0 | 18.9 |

## What it means for the roster

Floor, bar, runner and food staff together, from the manager's own table, for the forecast made 7 days ahead. "Right roster" means the same table row as the real guest number called for. This depends on how the table is read between its rows (a row applies from its guest number up to the next row), which the manager still has to confirm.

| | Our forecast | Manager's plan |
|---|---|---|
| Evenings with the right roster | 74 of 84 | 31 of 84 |
| Staff rostered beyond what was needed (person-evenings) | 14 | 194 |
| Staff short of what was needed (person-evenings) | 20 | 0 |
