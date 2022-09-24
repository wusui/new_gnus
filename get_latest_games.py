# Cbssportsline Rotiserrie league extraction code
# Copyright (c) 2022 Warren Usui
# This code is licensed under the MIT license (see LICENSE.txt for details)
"""
Game extraction code. Does not require logging in.
"""
import os
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import pandas as pd

def get_al_team_data():
    """
    Return a dictionary of real team names indexed by abbreviation
    """
    resp = requests.get("https://www.cbssports.com/mlb/teams/")
    soup = BeautifulSoup(resp.text, "html.parser")
    tables = soup.findAll('table')
    refss = []
    for atag in tables[0].find_all("a", href=True):
        refss.append(":".join(atag['href'].split("/")[3:5]))
    retv = {}
    for part in list(set(refss)):
        parts = part.split(":")
        teamname = " ".join([str.capitalize(x) for x in parts[1].split("-")])
        retv[parts[0]] = teamname
    return retv

def is_okay_stat_day(stat_d):
    """
    Given a date (yyyymmdd format) return true if that day has results
    and all games are complete

    Input:
        stat_d -- date in yyyymmdd format
    Returns:
        True if this day has all completed results
    """
    resp = requests.get(f"https://www.cbssports.com/mlb/schedule/{stat_d}/")
    pdinfo = pd.read_html(resp.text)
    result = False
    all_done = True
    for ptable in pdinfo:
        pyval = ptable.to_dict()
        if "Result" in pyval:
            result = True
        if "Home Starter" in pyval:
            all_done = False
    return result and all_done

def get_last_full_day():
    """
    Find most recent date for which is_okay_stat_day is true.

    Returns:
        date in yyyymmdd format
    """
    dvalue = datetime.today()
    sdvalue = dvalue.strftime('%Y%m%d')
    while not is_okay_stat_day(sdvalue):
        dvalue -= timedelta(1)
        sdvalue = dvalue.strftime('%Y%m%d')
    return sdvalue

def get_recent_games(datev=None):
    """
    Find games played on the most recent complete date.

    Params:
        datev -- Date to start searching from.  If not specified, use today.
    Returns:
        list of boxscore urls
    """
    if datev:
        gdate = datev
    else:
        gdate = get_last_full_day()
    out_path = os.sep.join(["..", "data", f"rot{gdate}.json"])
    if os.path.exists(out_path):
        print(f"Skipping -- rot{gdate}.json already exists")
        return []
    resp = requests.get(f"https://www.cbssports.com/mlb/scoreboard/{gdate}")
    soup = BeautifulSoup(resp.text, "html.parser")
    result = soup.find_all("a", href=True)
    boxlist = []
    for entry in result:
        if entry['href'].find("boxscore/MLB_") > 0:
            boxlist.append(entry['href'])
    return boxlist

def filter_al_teams_from_boxscores(list_of_box_scores):
    """
    Given a list of boxscores, return a list of those boxscores where at
    least one AL team played.
    """
    team_data = get_al_team_data()
    outlist = []
    for game in list_of_box_scores:
        parts = game.split("@")
        visitor = parts[0].split("_")[-1]
        home = parts[1].split("/")[0]
        if home.endswith("_2"):
            home = home[0:-2]
        if home in team_data or visitor in team_data:
            outlist.append(game)
    return outlist

def get_latest_games(datev=None):
    """
    Return a list of boxscores to check.  datev is a date in yyyymmdd
    format.  If not specified, search from today.
    """
    return filter_al_teams_from_boxscores(get_recent_games(datev))

if __name__ == "__main__":
    print(get_latest_games())
