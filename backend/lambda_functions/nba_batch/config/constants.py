from typing import Any

# ESPN API エンドポイント
ESPN_BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
ESPN_STANDINGS_URL = "https://site.api.espn.com/apis/v2/sports/basketball/nba/standings"

# ESPN に公開レート制限はないが礼儀として少し待機する（秒）
ESPN_REQUEST_SLEEP_SEC = 0.3

# ESPN API が conference/division を返さないためハードコードする
# キーは ESPN の abbreviation (nba.com 略称と異なるものあり: GS/NY/NO/SA/UTAH/WSH)
TEAM_STATIC: dict[str, dict[str, Any]] = {
    # Eastern / Atlantic
    "BOS":  {"state": "Massachusetts",       "year_founded": 1946, "conference": "East", "division": "Atlantic"},
    "BKN":  {"state": "New York",            "year_founded": 1967, "conference": "East", "division": "Atlantic"},
    "NY":   {"state": "New York",            "year_founded": 1946, "conference": "East", "division": "Atlantic"},
    "PHI":  {"state": "Pennsylvania",        "year_founded": 1946, "conference": "East", "division": "Atlantic"},
    "TOR":  {"state": "Ontario",             "year_founded": 1995, "conference": "East", "division": "Atlantic"},
    # Eastern / Central
    "CHI":  {"state": "Illinois",            "year_founded": 1966, "conference": "East", "division": "Central"},
    "CLE":  {"state": "Ohio",               "year_founded": 1970, "conference": "East", "division": "Central"},
    "DET":  {"state": "Michigan",            "year_founded": 1941, "conference": "East", "division": "Central"},
    "IND":  {"state": "Indiana",             "year_founded": 1967, "conference": "East", "division": "Central"},
    "MIL":  {"state": "Wisconsin",           "year_founded": 1968, "conference": "East", "division": "Central"},
    # Eastern / Southeast
    "ATL":  {"state": "Georgia",             "year_founded": 1946, "conference": "East", "division": "Southeast"},
    "CHA":  {"state": "North Carolina",      "year_founded": 1988, "conference": "East", "division": "Southeast"},
    "MIA":  {"state": "Florida",             "year_founded": 1988, "conference": "East", "division": "Southeast"},
    "ORL":  {"state": "Florida",             "year_founded": 1989, "conference": "East", "division": "Southeast"},
    "WSH":  {"state": "District of Columbia","year_founded": 1961, "conference": "East", "division": "Southeast"},
    # Western / Northwest
    "DEN":  {"state": "Colorado",            "year_founded": 1967, "conference": "West", "division": "Northwest"},
    "MIN":  {"state": "Minnesota",           "year_founded": 1989, "conference": "West", "division": "Northwest"},
    "OKC":  {"state": "Oklahoma",            "year_founded": 1967, "conference": "West", "division": "Northwest"},
    "POR":  {"state": "Oregon",              "year_founded": 1970, "conference": "West", "division": "Northwest"},
    "UTAH": {"state": "Utah",               "year_founded": 1974, "conference": "West", "division": "Northwest"},
    # Western / Pacific
    "GS":   {"state": "California",          "year_founded": 1946, "conference": "West", "division": "Pacific"},
    "LAC":  {"state": "California",          "year_founded": 1970, "conference": "West", "division": "Pacific"},
    "LAL":  {"state": "California",          "year_founded": 1948, "conference": "West", "division": "Pacific"},
    "PHX":  {"state": "Arizona",             "year_founded": 1968, "conference": "West", "division": "Pacific"},
    "SAC":  {"state": "California",          "year_founded": 1945, "conference": "West", "division": "Pacific"},
    # Western / Southwest
    "DAL":  {"state": "Texas",              "year_founded": 1980, "conference": "West", "division": "Southwest"},
    "HOU":  {"state": "Texas",              "year_founded": 1967, "conference": "West", "division": "Southwest"},
    "MEM":  {"state": "Tennessee",           "year_founded": 1995, "conference": "West", "division": "Southwest"},
    "NO":   {"state": "Louisiana",           "year_founded": 2002, "conference": "West", "division": "Southwest"},
    "SA":   {"state": "Texas",              "year_founded": 1967, "conference": "West", "division": "Southwest"},
}
