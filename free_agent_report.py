# Cbssportsline Rotiserrie league extraction code
# Copyright (c) 2022 Warren Usui
# This code is licensed under the MIT license (see LICENSE.txt for details)
"""
Produce a set of tables of stats for free agent players
"""
import os
from datetime import datetime, timedelta
from operator import itemgetter
import json
import pandas as pd

MAGIC_BHITS = 7
MAGIC_BABS = 30
MAGIC_OUTS = 15
MAGIC_ER = 3
MAGIC_WHIP = 7
MAGIC_KCOUNT = 3
OUTS_PER_GAME = 27
OUTS_PER_INNING = 3
DISP_TABLES = [['HR', 'SB', 'RBI', 'R', 'aavg'],
               ['W', 'S', 'aera', 'awhip', 'aks9']]
COLUMNS = [['name', 'team', 'pos', 'AB', 'R', 'H', 'RBI',
                 'HR', 'SB', 'aavg'],
            ['name', 'team', 'W', 'S', 'outs', 'H', 'ER', 'BB', 'KS',
                  'aera', 'awhip', 'aks9']]
FUNC_TABLE = [[False, False, False, False,
               lambda x : x > MAGIC_BHITS / MAGIC_BABS],
               [False, False,
                lambda x : x < OUTS_PER_GAME * MAGIC_ER / MAGIC_OUTS,
                lambda x : x < OUTS_PER_INNING * MAGIC_WHIP / MAGIC_OUTS,
                lambda x : x > OUTS_PER_GAME * MAGIC_KCOUNT / MAGIC_OUTS
               ]]
TITLES = [['HOME RUNS', 'STOLEN BASES', 'RBIS', 'RUNS', 'AVERAGE'],
          ['WINS', 'SAVES', 'ERA', 'WHIP', 'Ks/9']]

def get_taken_players():
    """
    Return a list of players that are on roto teams (read from league.json)
    """
    taken_list = []
    pfile = os.sep.join(["..", "data", "league.json"])
    with open(pfile, "r", encoding="utf8") as fdesc:
        data = json.load(fdesc)
    for team in data['rosters']:
        for player in data['rosters'][team]:
            taken_list.append(player['number'])
    return taken_list

def add_stats(accum, posv, entry):
    """
    Accumulate stats for a player (passed in entry).  Posv is either "Bat"
    or "Pit"
    """
    slabels = {"Bat": ['AB', 'R', 'H', 'RBI', 'HR', 'SB'],
               "Pit": ['W', 'S', 'outs', 'H', 'ER', 'BB', 'KS']}
    for stat in slabels[posv]:
        accum[posv][entry["number"]][stat] += entry[stat]
    if posv == "Bat":
        accum[posv][entry["number"]]['pos'] += "-" + entry['pos']
    return accum[posv][entry["number"]]

def get_stats_on_date(accum, in_date):
    """
    Give a date specified, collect stats on that date and add those to
    the accum parameter.  Return that new accum value.
    """
    sfile = os.sep.join(["..", "data", f"rot{in_date}.json"])
    with open(sfile, "r", encoding="utf8") as fdesc:
        data = json.load(fdesc)
    for entry in data:
        posv = "Bat"
        if entry["pos"] == "P":
            posv = "Pit"
            if 'AB' in entry:
                continue
        if entry["number"] in accum[posv]:
            accum[posv][entry["number"]] = add_stats(accum, posv, entry)
        else:
            accum[posv][entry["number"]] = entry
    return accum

def get_stats_in_range(start_date, end_date):
    """
    Get stats for all players with the range specified.
    """
    dval = datetime.strptime(start_date, "%Y%m%d")
    enddate = datetime.strptime(end_date, "%Y%m%d")
    enddate += timedelta(1)
    date_diff = enddate - dval
    all_stats = {"Bat": {}, "Pit": {}}
    while dval != enddate:
        all_stats = get_stats_on_date(all_stats, dval.strftime("%Y%m%d"))
        dval += timedelta(1)
    return all_stats, date_diff

def get_available(all_stats):
    """
    Given the stats for all players, return stats for only those players
    who are not on any roto team.
    """
    takenlist = get_taken_players()
    retv = {}
    for pos in ["Bat", "Pit"]:
        retv[pos] = {}
        for pstat in all_stats[pos]:
            if pstat not in takenlist:
                retv[pos][pstat] = all_stats[pos][pstat]
    return retv

def get_bat_list(bdata, day_range):
    """
    Return a list of stats for batters. bdata is a list of raw statistics.
    Add adjusted batting average to each player.
    """
    retv = []
    for entry in bdata:
        batter = bdata[entry]
        pos_info = list(set(batter["pos"].split("-")))
        batter["pos"] = "-".join(pos_info)
        batter["aavg"] = ((day_range * MAGIC_BHITS + batter['H']) /
                          (day_range * MAGIC_BABS + batter['AB']))
        retv.append(batter)
    return retv

def get_pit_list(pdata, day_range):
    """
    Return a list of stats for pitchers. pdata is a list of raw statistics.
    Add adjusted era, whip and ks/9 stats to each player.
    """
    retv = []
    for entry in pdata:
        pitcher = pdata[entry]
        denominator = day_range * MAGIC_OUTS + pitcher['outs']
        pitcher["aera"] = OUTS_PER_GAME * ((day_range * MAGIC_ER +
                                            pitcher['ER']) / denominator)
        whval = pitcher['BB'] + pitcher['H']
        pitcher["awhip"] = OUTS_PER_INNING * ((day_range * MAGIC_WHIP
                                               + whval) / denominator)
        pitcher["aks9"] = OUTS_PER_GAME * ((day_range * MAGIC_KCOUNT +
                                            pitcher['KS']) / denominator)
        retv.append(pitcher)
    return retv

def collect_stats_free_agents(from_date, to_date):
    """
    Return a list of batter stats and a list of pitcher stats for the
    date range specified (inclusive)
    """
    astats, day_range = get_stats_in_range(from_date, to_date)
    avail = get_available(astats)
    bat_list = get_bat_list(avail['Bat'], day_range.days)
    pit_list = get_pit_list(avail['Pit'], day_range.days)
    return bat_list, pit_list

def sort_fields(data, fields):
    """
    Return a structure indexd by stat name.  Each element of that structure
    is a list of player records sorted by the stat key value.

    fields is a list of lists containing the stat name, and an indicator
    if stats should be sorted in ascending or descending order.
    """
    retv = {}
    for info in fields:
        retv[info[0]] = sorted(data, key=itemgetter(info[0]),
                               reverse=info[1])
    return retv

def get_sorted_tables(data):
    """
    Call sort_fields for all batter and pitcher stats
    """
    batter_tables = sort_fields(data[0], [['HR', True], ['SB', True],
                                          ['RBI', True], ['R', True],
                                          ['aavg', True]])
    pitcher_tables = sort_fields(data[1], [['W', True], ['S', True],
                                          ['aera', False], ['awhip', False],
                                          ['aks9', True]])
    return batter_tables, pitcher_tables


def limit_list(frame, stat, func=None):
    """
    If func is specfied, use that function to set the conditions for
    the DataFrame.  Otherwise, use positive results.
    """
    if not func:
        return frame[frame[stat] > 0]
    return frame[func(frame[stat])]

def report_free_agents_in_range(from_d, to_d):
    """
    from_d and to_d are date fields in "yyyymmdd" format.

    Collect free agent stats for all games in the range specfied (including
    both dates.

    Generate a set of tables for each scoring stat in html format.
    """
    data1 = collect_stats_free_agents(from_d, to_d)
    tables = get_sorted_tables(data1)
    out_data = ""
    for ptype in range(0, 2):
        for count, stat_name in enumerate(DISP_TABLES[ptype]):
            tframe = pd.DataFrame(tables[ptype][stat_name])
            dframe = tframe[COLUMNS[ptype]]
            sframe = limit_list(dframe, stat_name,
                                func=FUNC_TABLE[ptype][count])
            out_data += f"<br><br><h1>{TITLES[ptype][count]}</h1>"
            out_data += sframe.head(20).to_html(index=False)
    html_file_name = f"stats_from_{from_d}_to_{to_d}.html"
    fname = os.sep.join(["..", "data", html_file_name])
    with open(fname, "w", encoding="utf8") as data_out:
        data_out.write(out_data)

if __name__ == "__main__":
    report_free_agents_in_range("20220914", "20220920")
