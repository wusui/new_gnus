# Cbssportsline Rotiserrie league extraction code
# Copyright (c) 2022 Warren Usui
# This code is licensed under the MIT license (see LICENSE.txt for details)
"""
Collect game data into dict of player data indexed by cbs sportsline numbers.
Does not require signing in.
"""
import os
import json
import requests
from bs4 import BeautifulSoup
from get_latest_games import get_latest_games, get_al_team_data

def get_players(ptype, p_data, team):
    """
    Collect stats for a player (use branches variable as a switch).
    """
    retv = []
    team_data = get_al_team_data()
    if team not in team_data:
        return retv
    branches = {'HITTERS': hitting, 'PITCHERS': pitching}
    for stats in p_data:
        if stats[0].startswith(ptype):
            continue
        istats = stats[0].split(",")
        plyr = {}
        plyr['number'] = stats[1].split('/')[-3]
        offset = 0
        if istats[1] == '-':
            offset = 3
        plyr['name'] = istats[0 + offset]
        plyr['team'] = team
        plyr = branches[ptype](plyr, istats, offset)
        retv.append(plyr)
    return retv

def ip_to_outs(ipval):
    """
    Convert innings pitched strings to outs
    """
    parts = ipval.split('.')
    outs = int(parts[0].strip()) * 3
    outs += int(parts[1].strip())
    return outs

def pitching(plyr, istats, offset):
    """
    Fill out the stats specifically for a pitcher
    """
    plyr['pos'] = 'P'
    plyr['W'] = 0
    plyr['S'] = 0
    if istats[2 + offset].startswith("("):
        if istats[2 + offset].startswith("(W"):
            plyr['W'] = 1
        if istats[2 + offset].startswith("(S"):
            plyr['S'] = 1
        offset += 2
    while "(" in istats[1 + offset] or ")" in istats[1 + offset]:
        offset += 1
    plyr['outs'] = ip_to_outs(istats[1 + offset])
    plyr['H'] = int(istats[2 + offset])
    plyr['ER'] = int(istats[4 + offset])
    plyr['BB'] = int(istats[5 + offset])
    plyr['KS'] = int(istats[6 + offset])
    return plyr

def hitting(plyr, istats, offset):
    """
    Fill out the stats specifically for a batter
    """
    plyr['pos'] = istats[2 + offset]
    plyr['AB'] = int(istats[3 + offset])
    plyr['R'] = int(istats[4 + offset])
    plyr['H'] = int(istats[5 + offset])
    plyr['RBI'] = int(istats[6 + offset])
    if istats[7 + offset] == '-':
        plyr['HR'] = 0
    else:
        plyr['HR'] = int(istats[7 + offset])
    plyr['SB'] = 0
    return plyr

def add_steals(sdata, ret_stats):
    """
    Insert steals data into the batter records (collected independently)
    """
    for steal in sdata:
        chk = 0
        for count, plyr in enumerate(ret_stats):
            if steal == plyr['name']:
                chk += 1
                ret_stats[count]['SB'] = sdata[steal]
            if chk > 1:
                print(f"possible steal issue with: {steal}")
    return ret_stats

def format_records(raw_data):
    """
    Convert the raw data scraped from box score webpages into a dict
    containing individual stats.
    """
    player_pos = ["HITTERS", "PITCHERS"]
    teams = []
    ret_stats = []
    teams.append(raw_data['visitors'].split(",")[2])
    teams.append(raw_data['home'].split(",")[2])
    if teams[1].endswith("_2"):
        teams[1] = teams[1][0:-2]
    for count, stats in enumerate(raw_data['tables']):
        ret_stats.extend(get_players(player_pos[count // 2], stats,
                         teams[count % 2]))
    ret_stats = add_steals(raw_data["Steals"], ret_stats)
    return ret_stats

def extract_steals(soup):
    """
    Extract the steal data from the box score.  Return as dict of steal
    numbers indexed by player name.
    """
    spans = soup.findAll("span", {"class": "gametracker-row__item"})
    response = []
    prevsb = False
    for entry in spans:
        if prevsb:
            response.append(entry.text)
        prevsb = False
        if entry.text == "SB":
            prevsb = True
    steal_ret = {}
    for stl_data in response:
        for indv in stl_data.split(","):
            indv = indv.strip()
            if " (" in indv:
                indv = indv[0:indv.find(" (")]
            name = indv.split(" ")
            value = 1
            if name[-1].isnumeric():
                value = int(name[-1])
                name = name[0:-1]
            nname = " ".join(name)
            if nname.startswith("- "):
                nname = nname[2:]
            if nname not in steal_ret:
                steal_ret[nname] = value
    return steal_ret

def get_box_data(box_id):
    """
    Given a game id, extract the player info as a dict containing
    the stats
    """
    resp = requests.get(f"https://www.cbssports.com/{box_id}")
    soup = BeautifulSoup(resp.text, "html.parser")
    raw_box_data = {}
    raw_box_data['Steals'] = extract_steals(soup)
    tables = soup.findAll("table")
    frows = tables[0].find_all("tr")
    raw_box_data['visitors'] = frows[1].get_text(separator=',')
    raw_box_data['home'] = frows[2].get_text(separator=',')
    raw_box_data['tables'] = []
    for tnum in range(1, 8, 2):
        lineup = []
        prows = tables[tnum].find_all("tr")
        for pdata in prows:
            idv = pdata.find("a", href=True)
            outv = ''
            if idv:
                outv = idv['href']
            player = [pdata.get_text(separator=","), outv]
            lineup.append(player)
        raw_box_data['tables'].append(lineup)
    return format_records(raw_box_data)

def update_latest_games(datev=None):
    """
    Extract the get_bax_data stats from a list of games generated by
    get_latest_games().  Datev is date in yyyymmdd format.  Use today
    if omitted.
    """
    glist = get_latest_games(datev)
    if not glist:
        return
    gdate = glist[0].split("_")[1]
    out_path = os.sep.join(["..", "data", f"rot{gdate}.json"])
    all_stats = []
    for game in glist:
        stats = get_box_data(game)
        print(stats)
        all_stats.extend(stats)
    with open(out_path, "w", encoding="utf8") as write_file:
        json.dump(all_stats, write_file, indent=0)

if __name__ == "__main__":
    update_latest_games()
