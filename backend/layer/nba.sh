#!/bin/bash

UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'

echo "=== NBA CDN Access Test ==="
echo

# A: そもそもブロックされてるのか（gameId 非依存）
A=$(curl -s -o /dev/null -w "%{http_code}" -A "$UA" \
  https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json)

# B: 直近シーズンの試合（25-26レギュラー）
B=$(curl -s -o /dev/null -w "%{http_code}" -A "$UA" \
  -H "Referer: https://www.nba.com/" \
  -H "Origin: https://www.nba.com" \
  https://cdn.nba.com/static/json/liveData/boxscore/boxscore_0022500602.json)

# C: 古い試合（20-21レギュラー）
C=$(curl -s -o /dev/null -w "%{http_code}" -A "$UA" \
  -H "Referer: https://www.nba.com/" \
  -H "Origin: https://www.nba.com" \
  https://cdn.nba.com/static/json/liveData/boxscore/boxscore_0022000181.json)

echo "A: $A"
echo "B: $B"
echo "C: $C"