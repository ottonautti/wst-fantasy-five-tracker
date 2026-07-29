import json
import requests
from bs4 import BeautifulSoup

def main():
    with open('teams.json', 'r') as f:
        teams = json.load(f)
    
    unique_players = set()
    for team, team_data in teams.items():
        for pot, history_list in team_data.get("pots", {}).items():
            for entry in history_list:
                unique_players.add(entry['name'])
    
    # Needs a User-Agent or it might get blocked
    headers = {'User-Agent': 'Mozilla/5.0'}
    url = "https://www.snooker.org/res/index.asp?template=34"
    resp = requests.get(url, headers=headers)
    
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    player_map = {}
    
    # Find all player links
    for a in soup.find_all('a'):
        href = a.get('href', '')
        if 'player=' in href:
            name = a.text.strip().replace(' (a)', '')
            # Try to match the name cleanly
            p_id = href.split('player=')[1].split('&')[0]
            player_map[name] = p_id
            
    # Load existing to avoid overwriting unless new
    try:
        with open('name_mapping.json', 'r') as f:
            final_mapping = json.load(f)
    except FileNotFoundError:
        final_mapping = {}

    # Now build the filtered mapping
    for p in unique_players:
        if p in final_mapping:
            continue # already mapped

        # Simple matching
        matched_id = player_map.get(p)
        if not matched_id:
            # Try matching by last name or subset
            for k, v in player_map.items():
                if p.lower() in k.lower() or k.lower() in p.lower():
                    matched_id = v
                    break
        
        if matched_id:
            final_mapping[p] = matched_id
            print(f"Mapped {p} to {matched_id}")
        else:
            print(f"Failed to map {p}")
            
    with open('name_mapping.json', 'w') as f:
        json.dump(final_mapping, f, indent=2)

if __name__ == "__main__":
    main()
