import json
import requests
import urllib.parse
import os
from datetime import datetime

import quart
import quart_cors
from quart import request, jsonify

from helpers import helper

# Python baseball stat retrieval imports
from pybaseball import \
standings, batting_stats_bref, pitching_stats_bref, team_batting_bref, team_fielding_bref, \
team_pitching_bref, playerid_lookup, statcast_batter, statcast_outs_above_average, \
statcast_pitcher, top_prospects

import pandas as pd


# Note: Setting CORS to allow chat.openapi.com is only required when running a localhost plugin
app = quart_cors.cors(quart.Quart(__name__), allow_origin="https://chat.openai.com")

PLUGIN_HOSTNAME = "localhost:5003"
ESPN_URL = "https://www.espn.com"


@app.get("/standings")
async def get_standings():
    # Return the overall MLB standings
    overall_standings = []
    year = request.args.get("year")
    standing = standings(int(year))
    for i in standing:
        overall_standings.append(json.loads(i.to_json(orient='table')))
    print(helper.num_tokens(str(overall_standings)))

    return quart.Response(json.dumps(overall_standings), status=200, content_type='application/json')

@app.get("/news")
async def get_news():
    # Return relevant news articles for the team being asked about
    team_name = request.args.get("team_name")

    directory_path = 'C:/Users/joefo/dev/baseball-stats-ai/scraped_data' # Change upon deployment to hosting service
    all_files = os.listdir(directory_path)
    news_files = [f for f in all_files if f.startswith('mlb_news')]

    articles = []
    for filename in news_files:
        with open(os.path.join(directory_path, filename)) as file:
            data = json.load(file)
            # Filter articles for the requested team
            team_name = team_name.lower()
            team_articles = [article for article in data if article['team'] == team_name]
            articles.extend(team_articles)

    print(helper.num_tokens(articles))
    return quart.Response(json.dumps(articles, ensure_ascii=False), content_type='application/json', status=200)

@app.get("/batting_stats_bref")
async def get_batting_stats_bref():
    # Return batting statistics at a season level from Baseball Reference
    # To see what data is being collected refer to 
    # 

    year = request.args.get("year")

    if year < 2008:
        return quart.Response("The starting date is before data started being collected in 2008.", status=500)
    
    batting = batting_stats_bref(year)
    batting = json.loads(batting.to_json(orient='table'))
    print(helper.num_tokens(batting))

    return quart.Response(json.dumps(batting),content_type='application/json')

@app.get("/pitching_stats_bref")
async def get_pitching_stats_bref():
    # Return pitching statistics at a season level from Baseball Reference
    
    year = int(request.args.get("year"))
    if year < 2008:
        return quart.Response("The starting date is before data started being collected in 2008.", status=500)
    
    pitching = pitching_stats_bref(int(year))
    pitching = json.loads(pitching.to_json(orient='table'))
    print(helper.num_tokens(pitching))

    return quart.Response(json.dumps(pitching), content_type='application/json')

@app.get("/team_batting")
async def get_team_batting():
    # Return a team's combined batting statistics from Baseball Reference for the provided season
    team_abr = request.args.get('team_abbreviation')
    year = request.args.get("year")
    team_batting_stats = team_batting_bref(team_abr,int(year))
    team_batting_stats = json.loads(team_batting_stats.to_json(orient='table'))
    print(helper.num_tokens(team_batting_stats))

    return quart.Response(json.dumps(team_batting_stats), content_type='application/json')

@app.get("/team_fielding")
async def get_team_fielding():
    # Return all the teams combined fielding statistics for the provided season
    year = request.args.get("year")
    team_fielding_stats = team_fielding_bref(year)
    team_fielding_stats = json.loads(team_fielding_stats.to_json(orient='table'))

    return quart.Response(json.dumps(team_fielding_stats), content_type='application/json')

@app.get("/team_pitching")
async def get_team_pitching():
    # Return all the teams combined pitching statistics for the provided season
    year = request.args.get("year")
    team_pitching_stats = team_pitching_bref(year)
    team_pitching_stats = json.loads(team_pitching_stats.to_json(orient='table'))

    return quart.Response(json.dumps(team_pitching_stats), content_type='application/json')

# Statcast routes
@app.get("/statcast_playerid_lookup")
async def get_statcast_playerid_lookup():
    # Retrieves the player id based on a players name that is given
    first_name = request.args.get("first")
    last_name = request.args.get("last")
    playerid = playerid_lookup(last_name, first_name)

    #If multiple players have the same name or multiple results are returned for the function 
    if len(playerid.index) > 1:
        heading = 'Multiple MLB players found with the same name\n\n'
        body = playerid[['name_last', 'name_first', 'key_mlbam', 'mlb_played_first', 'mlb_played_last']]
        body = body.to_markdown()
        return quart.Response(response=heading+body, status=500, content_type='text/markdown')
        # There is some testing that should be done with this function once we get developer access
        # We want another prompt that can handle a specific ID value being passed after the error is returned
    
    #Test with the model to see if it can retrieve the key_mlbam from the output and adjust the YAML file accordingly
    playerid = json.loads(playerid.to_json(orient='table'))

    return quart.Response(json.dumps(playerid), content_type='application/json', status=200)

@app.get("/statcast_batter")
async def get_statcast_batter():
    #Retrieves detailed pitch-level statcast information about a player's batting performance over a given time period.  
    starting_date = request.args.get('date')
    mlbam_player_id = request.args.get('key_mlbam')

    #Statcast data is only available from 2008 onward. An error is returned for queries before that.
    if starting_date == None:
        pass
    else: 
        date_format = "%Y-%m-%d"
        date = datetime.strptime(starting_date, date_format)
        if date.year < 2008:
            return quart.Response("The starting date is before statcast data started being collected in 2008.", status=500)

    batter_stats = statcast_batter(start_dt=starting_date,player_id=mlbam_player_id)
    #Retrieving only the first 26 columns because of output limitations
    batter_stats = batter_stats.iloc[:, :26]

    batter_stats = json.loads(batter_stats.to_json(orient='table'))
    print(helper.num_tokens(str(batter_stats)))

    return quart.Response(json.dumps(batter_stats), content_type='application/json')

@app.get("/statcast_fielding")
async def get_statcast_fielding():
    #Retrieves the fielding stat 'Outs Above Average' for all players across the league with a provided year
    year = int(request.args.get('year'))
    pos_abbr = str(request.args.get('position_abbreviation'))
    
    if int(year) < 2008:
        return quart.Response("The starting date is before statcast data started being collected in 2008.", status=500)
    
    
    fielding = statcast_outs_above_average(year,pos=pos_abbr)
    fielding = fielding.sort_values(by=['outs_above_average'],ascending=False)
    fielding = json.loads(fielding.to_json(orient='table'))
    print(helper.num_tokens(str(fielding)))
    # TODO - There are more stats that can be retrieved for player fielding from pybaseball. Testing should be done with model for the other functions

    return quart.Response(json.dumps(fielding), content_type='application/json')

@app.get("/statcast_pitcher")
async def get_statcast_pitcher():
    #Retrieves pitch-level statistics for a pitcher
    starting_date = request.args.get('date')
    mlbam_player_id = request.args.get('key_mlbam')

    #Statcast data is only available from 2008 onward. An error is returned for queries before that. 
    if starting_date == None:
        pass
    else:
        date_format = "%Y-%m-%d"
        date = datetime.strptime(starting_date, date_format)
        if date.year < 2008:
            return quart.Response("The starting date is before statcast data started being collected in 2008.", status=500)

    # TODO - There are more statcast pitching stats that can be retrieved from pybaseball. 

    pitching = statcast_pitcher(start_dt=starting_date,player_id=mlbam_player_id)
    pitching = json.loads(pitching.to_json(orient='table'))
    print(helper.num_tokens(pitching))


    return quart.Response(json.dumps(pitching), content_type='application/json')


@app.get("/top_prospects")
async def get_top_prospects():
    #Retrieves the top prospects for a team or across the entire MLB
    team_name = request.args.get('team_name')
    prospects = top_prospects(team_name)



@app.get("/players")
async def get_players():
    query = request.args.get("query")
    res = requests.get(
        f"{ESPN_URL}/search/_/q/{query}")
    body = res.json()
    return quart.Response(response=json.dumps(body), status=200)


@app.get("/teams")
async def get_teams():
    res = requests.get(
        "{HOST_URL}/api/v1/teams?page=0&per_page=100")
    body = res.json()
    return quart.Response(response=json.dumps(body), status=200)


@app.get("/games")
async def get_games():
    query_params = [("page", "0")]
    limit = request.args.get("limit")
    query_params.append(("per_page", limit or "100"))
    start_date = request.args.get("start_date")
    if start_date:
        query_params.append(("start_date", start_date))
    end_date = request.args.get("end_date")

    if end_date:
        query_params.append(("end_date", end_date))
    seasons = request.args.getlist("seasons")

    for season in seasons:
        query_params.append(("seasons[]", str(season)))
    team_ids = request.args.getlist("team_ids")

    for team_id in team_ids:
        query_params.append(("team_ids[]", str(team_id)))

    res = requests.get(
        f"{HOST_URL}/api/v1/games?{urllib.parse.urlencode(query_params)}")
    body = res.json()
    return quart.Response(response=json.dumps(body), status=200)


@app.get("/stats")
async def get_stats():
    query_params = [("page", "0")]
    limit = request.args.get("limit")
    query_params.append(("per_page", limit or "100"))
    start_date = request.args.get("start_date")
    if start_date:
        query_params.append(("start_date", start_date))
    end_date = request.args.get("end_date")

    if end_date:
        query_params.append(("end_date", end_date))
    player_ids = request.args.getlist("player_ids")

    for player_id in player_ids:
        query_params.append(("player_ids[]", str(player_id)))
    game_ids = request.args.getlist("game_ids")

    for game_id in game_ids:
        query_params.append(("game_ids[]", str(game_id)))
    res = requests.get(
        f"{HOST_URL}/api/v1/stats?{urllib.parse.urlencode(query_params)}")
    body = res.json()
    return quart.Response(response=json.dumps(body), status=200)


@app.get("/season_averages")
async def get_season_averages():
    query_params = []
    season = request.args.get("season")
    if season:
        query_params.append(("season", str(season)))
    player_ids = request.args.getlist("player_ids")

    for player_id in player_ids:
        query_params.append(("player_ids[]", str(player_id)))
    res = requests.get(
        f"{HOST_URL}/api/v1/season_averages?{urllib.parse.urlencode(query_params)}")
    body = res.json()
    return quart.Response(response=json.dumps(body), status=200)


@app.get("/logo.png")
async def plugin_logo():
    filename = 'logo.png'
    return await quart.send_file(filename, mimetype='image/png')


@app.get("/.well-known/ai-plugin.json")
async def plugin_manifest():
    host = request.headers['Host']
    with open(".well-known/ai-plugin.json") as f:
        text = f.read()
        # This is a trick we do to populate the PLUGIN_HOSTNAME constant in the manifest
        text = text.replace("PLUGIN_HOSTNAME", f"https://{host}")
        return quart.Response(text, mimetype="text/json")


@app.get("/openapi.yaml")
async def openapi_spec():
    host = request.headers['Host']
    with open("openapi.yaml") as f:
        text = f.read()
        # This is a trick we do to populate the PLUGIN_HOSTNAME constant in the OpenAPI spec
        text = text.replace("PLUGIN_HOSTNAME", f"https://{host}")
        return quart.Response(text, mimetype="text/yaml")

@app.errorhandler(404)
async def page_not_found(e):
    return "Page Not Found" , 404

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5003)