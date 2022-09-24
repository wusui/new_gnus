# Cbssportsline Rotiserrie league extraction code
# Copyright (c) 2022 Warren Usui
# This code is licensed under the MIT license (see LICENSE.txt for details)
"""
Running get_cbs_league() writes a league's information to a json file.

The config/secrets.ini file contains user, password and leagueid values.

The results are savedin data/league.json
"""
import os
import json
import configparser
from bs4 import BeautifulSoup
import pandas as pd
from selenium_login import selenium_login

class BadPlayerNumber(Exception):
    """
    Thrown when double-checking code is passed a number that does not
    correspond to a player
    """

def get_cbs_team_numbers(webdrvr, league_id):
    """
    Get a list of teams in this league

    Input:
       webdrvr: Selenium driver
       league_id: League website id

    Returns: List of tuples. Each tuple consists of a team number and
             a rotisserie team name.
    """
    webdrvr.get(f"https://{league_id}/standings/overall")
    soup = BeautifulSoup(webdrvr.page_source, "html.parser")
    tables = soup.find_all("table")
    return [(entry['id'], entry.contents[1].text)
            for entry in tables[1].findAll(id=True)]

def get_my_cbs_team_id(webdrvr, league_id):
    """
    Get my team id (a number)

    Input:
       webdrvr: Selenium driver
       league_id: League website id

    Return:
       A team number.
    """
    webdrvr.get(f"https://{league_id}")
    soup = BeautifulSoup(webdrvr.page_source, "html.parser")
    href_tags = soup.find_all(href=True)
    hrefs = [tag.get('href') for tag in href_tags]
    for aref in hrefs:
        if aref.startswith("/teams/page/"):
            return aref.split("/")[-1]
    return "-"

def extract_cbs_info(linfo, in_pddata):
    """
    Get the player information from a team page.

    Parameters:
        linfo -- List of players
        ind_pddata -- Table data extracted by pandas.  Either a pitcher
                      table or batter table

    Returns: List of dictionaries. Each entry contains information about
             a specific player.
    """
    lplist = list(in_pddata.iterrows())
    typev = "Starter"
    retv = []
    for player in lplist:
        name = player[1].values[2]
        if name.find("|") > 0:
            parts1 = name.split("|")
            team = parts1[1].strip()
            firsthalf = parts1[0].split()
            npart = " ".join(firsthalf[0:-1])
            elig = firsthalf[-1]
            tname = {"position": player[1].values[1], "name": npart,
                     "team": team, "eligibility": elig, "status": typev,
                     "number": next(linfo).split("/")[-1]}
            retv.append(tname)
        else:
            typev = name
    return retv

def get_cbs_rosters(webdrvr, league_id, team_num):
    """
    Given a team number, get the roster

    Input:
       webdrvr: Selenium driver
       league_id: League website id
       number: Team number

    Returns:
       Roster expressed as a dictionary
    """
    team_pg = f"https://{league_id}/teams/{team_num}"
    webdrvr.get(team_pg)
    soup = BeautifulSoup(webdrvr.page_source, "html.parser")
    plist = soup.findAll(
        lambda tag:tag.name == "a" and tag.has_attr('aria-label') and
        tag.has_attr('href') and tag.has_attr("class")
    )
    rplist = [
        plyr['href'] for plyr in plist if plyr['class'][0] == 'playerLink'
    ]
    plinks = list(dict.fromkeys(rplist))
    pdinfo = pd.read_html(webdrvr.page_source)
    linfo = iter(plinks)
    roster = extract_cbs_info(linfo, pdinfo[0])
    roster += extract_cbs_info(linfo, pdinfo[1])
    return roster

def check_cbs_player_number(webdrvr, league_id, number):
    """
    Given a player number, return a name

    Input:
       webdrvr: Selenium driver
       league_id: League website id
       number: Player number

    Returns:
       Name of player
    """
    ppg1 = f"https://{league_id}/players/playerpage/{number}"
    webdrvr.get(ppg1)
    soup = BeautifulSoup(webdrvr.page_source, "html.parser")
    glist = soup.findAll(
        lambda tag:tag.name == "meta" and tag.has_attr('property') and
        tag.has_attr('content')
    )
    return [x['content'] for x in glist if x['property'] == 'og:title'][0]

def get_cbs_league(extracheck=False):
    """
    Extract league information

    Input parammeter:
        extracheck: If true, make sure every number used corresponds to
        a real player.
    Results:
        Creation of data/league.json file containing roster data
    """
    secret_info = configparser.ConfigParser()
    in_dir = os.sep.join(["..", "config"])
    secret_info.read(os.sep.join([in_dir, "secret.ini"]))
    league_id = secret_info["DEFAULT"]["leagueid"]
    out_path = os.sep.join(["..", "data", "league.json"])
    driver = selenium_login(in_dir)
    my_team_id = get_my_cbs_team_id(driver, league_id)
    teams = get_cbs_team_numbers(driver, league_id)
    rosters = {}
    for entry in teams:
        rosters[entry[0]] = get_cbs_rosters(driver, league_id, entry[0])
    league = {"my_team": my_team_id, "standings": teams,
              "rosters": rosters}
    with open(out_path, "w", encoding="utf8") as outfile:
        json.dump(league, outfile)
    if extracheck:
        for irosters in rosters.items():
            for player in irosters[1]:
                print(player)
                tname = check_cbs_player_number(driver, league_id,
                                                player['number'])
                if player['name'] != tname:
                    raise BadPlayerNumber

if __name__ == "__main__":
    get_cbs_league()
