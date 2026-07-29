import csv
import json
import os
from datetime import datetime

import requests
from bs4 import BeautifulSoup


def fetch_data():
    headers = {'User-Agent': 'Mozilla/5.0'}
    url = "https://www.snooker.org/res/index.asp?template=34"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, 'html.parser')

    # We want to extract player IDs and their points.
    # The table structure has rows where player name is linked to ?player=ID
    # The points usually appear in a specific column or the last column for total.

    # Let's find all rows with a player link
    points_data = {}
    table = soup.find('table', id='oneyearrankings')
    if not table:
        table = soup.find('table') # Fallback

    if not table:
        print("Could not find table")
        return points_data

    # Find the index of the CL column
    headers = [th.text.strip() for th in table.find('thead').find_all('th')]
    try:
        cl_index = headers.index('CL')
    except ValueError:
        cl_index = -1

    rows = table.find('tbody').find_all('tr') if table.find('tbody') else table.find_all('tr')[1:]

    for row in rows:
        player_link = row.find('a', href=lambda h: h and 'player=' in h)
        if player_link:
            href = player_link['href']
            p_id = href.split('player=')[1].split('&')[0]

            sum_td = row.find('td', class_=lambda c: c and 'sum' in c and 'javascript_on' in c)
            if not sum_td:
                sum_td = row.find('td', class_=lambda c: c and 'sum' in c)

            cl_points = 0
            if cl_index != -1:
                tds = row.find_all('td')
                if len(tds) > cl_index:
                    val = tds[cl_index].text.strip().replace(',', '').replace('\xa0', '').replace(' ', '')
                    if val.isdigit():
                        cl_points = int(val)

            if sum_td:
                # Remove spaces, commas, nbsp
                val = sum_td.text.strip().replace(',', '').replace('\xa0', '').replace(' ', '')
                if val.isdigit():
                    points_data[p_id] = {'total': int(val), 'cl': cl_points}
                else:
                    points_data[p_id] = {'total': 0, 'cl': 0}
            else:
                points_data[p_id] = {'total': 0, 'cl': 0}

    return points_data

def main():
    # Load required configurations
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    history_file = os.path.join(base_dir, 'history.csv')

    points_data = fetch_data()
    if not points_data:
        print("Failed to fetch points data.")
        return

    date_str = datetime.now().strftime('%Y-%m-%d')
    print(f"Fetched points for {len(points_data)} players on {date_str}")

    # Append to CSV
    row_count = 0
    file_exists = os.path.exists(history_file)
    with open(history_file, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(['Date', 'PlayerID', 'Points', 'CLPoints'])

        for p_id, points in points_data.items():
            writer.writerow([date_str, p_id, points['total'], points['cl']])
            row_count += 1

    print(f"Appended {row_count} rows to {history_file}")

if __name__ == "__main__":
    main()
