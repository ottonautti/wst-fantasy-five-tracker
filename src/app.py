import csv
import json
import os
from collections import defaultdict
from datetime import datetime

import streamlit as st

st.set_page_config(page_title="WST Fantasy Five Tracker", layout="wide")

# Point multipliers as described
POT_WEIGHTS = {
    "1": 1.0,
    "2": 1.0,
    "3": 3.0,
    "4": 4.0,
    "5": 5.0
}
@st.cache_data(ttl=3600)
def load_data():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    teams_path = os.path.join(base_dir, 'teams.json')
    mapping_path = os.path.join(base_dir, 'name_mapping.json')
    history_path = os.path.join(base_dir, 'history.csv')

    with open(teams_path, 'r') as f:
        teams = json.load(f)

    if os.path.exists(mapping_path):
        with open(mapping_path, 'r') as f:
            mapping = json.load(f)
    else:
        mapping = {}

    history = []
    if os.path.exists(history_path):
        with open(history_path, 'r') as f:
            reader = csv.DictReader(f)
            latest_by_date = {}
            for row in reader:
                latest_by_date[(row['Date'], row['PlayerID'])] = row
            history = list(latest_by_date.values())
            # Ensure it is sorted by Date just in case
            history.sort(key=lambda x: x['Date'])

    # 1. Learn the history of dates to iterate in chronological order
    all_dates = sorted(list(set(r['Date'] for r in history)))

    # 2. Replay history to calculate daily deltas (points earned per day)
    player_previous_points = defaultdict(int)
    team_points_cumulative = defaultdict(float)
    team_points_unweighted_cumulative = defaultdict(float)
    team_history = {}

    for date_str in all_dates:
        current_date_rows = [r for r in history if r['Date'] == date_str]

        # Determine each player's delta earnings on this day
        date_deltas = {}
        for r in current_date_rows:
            p_id = r['PlayerID']
            total_pts = int(r['Points'])
            cl_pts = int(r.get('CLPoints', 0))
            pts = total_pts - cl_pts

            # Since rank points are cumulative through the year, the day's earned points are current - previous
            # If this is the FIRST time seeing the player, they came into the tracker with PTS,
            # so their delta is the full PTS.
            delta = pts - player_previous_points[p_id]
            date_deltas[p_id] = delta
            player_previous_points[p_id] = pts

        # Distribute daily earnings to the actively rostered team players
        team_history[date_str] = {}
        for team, team_data in teams.items():
            team_daily_earned = 0
            team_daily_earned_unweighted = 0
            for pot, history_list in team_data.get("pots", {}).items():
                for entry in history_list:
                    start = entry.get('start')
                    end = entry.get('end')

                    # Check if player was mathematically active on this 'date_str'
                    is_active = (not start or start <= date_str) and (not end or end > date_str)

                    if is_active:
                        p_id = mapping.get(entry['name'])
                        if p_id and p_id in date_deltas:
                            weight = POT_WEIGHTS.get(pot, 1.0)
                            team_daily_earned += date_deltas[p_id] * weight
                            team_daily_earned_unweighted += date_deltas[p_id]
                        break # Found the active player for this pot

            team_points_cumulative[team] += team_daily_earned
            team_points_unweighted_cumulative[team] += team_daily_earned_unweighted
            manager = teams[team].get("manager", team)
            team_history[date_str][manager] = team_points_cumulative[team]

    # Convert to chart data format
    chart_data = []
    for date_str in all_dates:
        entry = {"Date": date_str}
        entry.update(team_history[date_str])
        chart_data.append(entry)

    # Pre-calculate active players and current total for the leaderboard snapshot
    latest_date = all_dates[-1] if all_dates else None

    # Map back active players right now (or as of the latest_date)
    active_rosters = defaultdict(dict)
    for team, team_data in teams.items():
        for pot, history_list in team_data.get("pots", {}).items():
            for entry in history_list:
                start = entry.get('start')
                end = entry.get('end')
                # If no latest date, just show the currently open ended
                compare_date = latest_date or datetime.now().strftime('%Y-%m-%d')
                is_active = (not start or start <= compare_date) and (not end or end > compare_date)
                if is_active:
                    active_rosters[team][pot] = entry['name']
                    break

    return teams, active_rosters, mapping, player_previous_points, team_points_cumulative, team_points_unweighted_cumulative, chart_data, latest_date

st.title("WST Fantasy Five Tracker")

teams, active_rosters, mapping, latest_points, team_points, team_points_unweighted, chart_data, latest_date = load_data()

if not chart_data:
    st.warning("No data found. Please run the collector script (`python src/collector.py`)")
    st.stop()

st.write(f"Latest data from: **{latest_date}**")
st.caption("Source: [snooker.org Provisional Season Points](https://www.snooker.org/res/index.asp?template=34) — *Note: This tracker considers guaranteed money for current and upcoming events. Points from Champions League are excluded.*")

# Construct leaderboard
leaderboard = []
for team, team_data in teams.items():
    pots_data = team_data.get("pots", {})
    team_total = team_points.get(team, 0)
    team_total_unweighted = team_points_unweighted.get(team, 0)
    manager = team_data.get("manager", team)

    row = {
        "Manager": manager,
        "Team": team,
        "Points": int(team_total),
        "PointsUnweighted": int(team_total_unweighted)
    }

    # Ensure they stay in pot order 1 to 5
    for pot in ["1", "2", "3", "4", "5"]:
        history_list = pots_data.get(pot, [])
        cell_parts = []
        for entry in history_list:
            name = entry["name"]
            start = entry.get("start")
            end = entry.get("end")
            compare_date = latest_date or datetime.now().strftime('%Y-%m-%d')
            is_active = (not start or start <= compare_date) and (not end or end > compare_date)

            if is_active:
                cell_parts.append(name)
            else:
                cell_parts.append(f"<s>{name}</s>")

        row[f"P{pot}"] = " <br> ".join(cell_parts)

    leaderboard.append(row)

# Sort leaderboard by points
leaderboard.sort(key=lambda x: x["Points"], reverse=True)

st.header("🏆 Leaderboard")
html = "<div style='max-width: 1100px;'>"
html += "<table style='width: 100%; border-collapse: collapse; text-align: left;'>"
html += "<tr style='border-bottom: 2px solid #ddd;'>"
html += "<th>Manager</th><th>Team</th><th style='text-align: right; width: 150px;'>Points</th><th style='text-align: right; width: 150px;'>Points (unweighted)</th><th>P1</th><th>P2</th><th>P3</th><th>P4</th><th>P5</th>"
html += "</tr>"
for r in leaderboard:
    html += "<tr style='border-bottom: 1px solid #eee;'>"
    html += f"<td style='padding: 8px;'>{r['Manager']}</td>"
    html += f"<td style='padding: 8px;'><b>{r['Team']}</b></td>"
    html += f"<td style='padding: 8px; text-align: right;'><b>{r['Points']:,}</b></td>"
    html += f"<td style='padding: 8px; text-align: right;'>{r['PointsUnweighted']:,}</td>"
    html += f"<td style='padding: 8px;'>{r['P1']}</td>"
    html += f"<td style='padding: 8px;'>{r['P2']}</td>"
    html += f"<td style='padding: 8px;'>{r['P3']}</td>"
    html += f"<td style='padding: 8px;'>{r['P4']}</td>"
    html += f"<td style='padding: 8px;'>{r['P5']}</td>"
    html += "</tr>"
html += "</table></div><br>"

st.markdown(html, unsafe_allow_html=True)

st.header("📈 Progress")
if chart_data:
    st.line_chart(chart_data, x="Date")
