# Cbssportsline Rotiserrie league extraction code
# Copyright (c) 2022 Warren Usui
# This code is licensed under the MIT license (see LICENSE.txt for details)
"""
One stop routine for the last seven days.
"""
from datetime import datetime, timedelta
from get_cbs_league import get_cbs_league
from get_latest_games import get_latest_games
from update_player_stats_for_day import update_latest_games
from free_agent_report import report_free_agents_in_range

def update_a_range(start_date, end_date):
    """
    Call get_latest_games and update_latest_games for days in the range
    specified
    """
    dval = datetime.strptime(start_date, "%Y%m%d")
    enddate = datetime.strptime(end_date, "%Y%m%d")
    while dval != enddate:
        str_date = datetime.strftime(dval, "%Y%m%d")
        get_latest_games(str_date)
        update_latest_games(str_date)
        dval += timedelta(1)

def roto_gnus():
    """
    Do all the calculations for the last seven day period
    """
    get_cbs_league()
    enddate = datetime.today()
    startdate = enddate - timedelta(7)
    startvalue = startdate.strftime('%Y%m%d')
    endvalue = enddate.strftime('%Y%m%d')
    update_a_range(startvalue, endvalue)
    report_free_agents_in_range(startvalue, endvalue)

if __name__ == "__main__":
    roto_gnus()
