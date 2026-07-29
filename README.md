# WST Fantasy Five Tracker

A minimal web application to track WST (Snooker) Fantasy Five teams' point progression! It calculates cumulative points by taking the daily delta of player points and respects player roster timings.

## Features
- **Scraper**: A lightweight crawler to harvest current 25/26 points directly from snooker.org. Since points are strictly delta-accumulated locally over time, you can swap players out effectively!
- **Dynamic Multipliers**: By default, assigns weightings of 3x, 4x, and 5x to pots 3, 4, and 5.
- **Transfers Engine**: Teams are backed chronologically. If a player is substituted out via `end` date, their previous points stick to the team history! New substitutes simply accumulate points starting from their `start` date.

## Setup

First, initialize your environment:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running the Architecture

### 1) The Data Collector (Background Job)
To ensure the historical line graph updates consistently, decouple the data fetching into an independent background script.

Every day, execute:
```bash
python src/collector.py
```
**Recommended Cron Setup:**
You can set this up to run daily at 2:00 AM automatically. Edit your crontab (`crontab -e`) and add:
```cron
0 2 * * * cd /path/to/fantasy-five-tracker && /path/to/fantasy-five-tracker/venv/bin/python src/collector.py
```

### 2) The Streamlit UI
To view the leaderboard and progression:
```bash
streamlit run src/app.py
```

## Managing Teams & Transfers
`teams.json` enforces pot architecture tracking.

When establishing your team, `start` and `end` are completely optional (`null`). Example substitution when the December window opens:

```json
"3": [
  { "name": "Current Player", "start": null, "end": "2025-12-01" },
  { "name": "New Transferred Player", "start": "2025-12-01", "end": null }
]
```

When you add a *new* transferred player for the first time, simply run `python generate_mapping.py` to pull their Snooker.org internal ID. From then on, their incoming daily points delta applies immediately to the team's total moving forward.
