import json
import requests
import urllib.parse
import os

import quart
import quart_cors
from quart import request, jsonify

from pybaseball import standings, batting_stats, pitching_stats, team_batting, team_fielding
import pandas as pd


# Note: Setting CORS to allow chat.openapi.com is only required when running a localhost plugin
app = quart_cors.cors(quart.Quart(__name__), allow_origin="https://chat.openai.com")

HOST_URL = "http://localhost:5003"
ESPN_URL = "https://www.espn.com"


@app.get("/standings")
async def get_standings():
    # Return the overall MLB standings
    overall_standings = []
    year = request.args.get("query")
    standing = standings(int(year))
    for i in standing:
        overall_standings.append(json.loads(i.to_json(orient='table')))

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
            team_articles = [article for article in data if article['team'] == team_name]
            articles.extend(team_articles)


    return quart.Response(json.dumps(articles, ensure_ascii=False), content_type='application/json', status=200)

@app.get("/batting_stats_fangraphs")
async def get_batting_stats_fangraphs():
    # Return batting statistics at a season level from FanGraphs
    # To see what data is being collected refer to 
    # https://www.fangraphs.com/leaders.aspx?pos=all&stats=bat&lg=all&qual=y&type=8&season=2023&month=0&season1=2023&ind=0&team=0&rost=0&age=0&filter=&players=0&startdate=2023-01-01&enddate=2023-12-31&sort=22,d
    
    year = request.args.get("year")
    batting = batting_stats(year)
    batting = json.loads(batting.to_json(orient='table'))

    return quart.Response(json.dumps(batting),content_type='application/json')

@app.get("/pitching_stats_fangraphs")
async def get_pitching_stats_fangraphs():
    # Return pitching statistics at a season level from FanGraphs
    
    year = request.args.get("year")
    pitching = pitching_stats(year)
    pitching = json.loads(pitching.to_json(orient='table'))

    return quart.Response(json.dumps(pitching), content_type='application/json')

@app.get("/team_batting")
async def get_team_batting():
    # Return all the teams combined batting statistics from FanGraphs for the provided season
    year = request.args.get("year")
    team_batting_stats = team_batting(year)
    team_batting_stats = json.loads(team_batting_stats.to_json(orient='table'))

    return quart.Response(json.dumps(team_batting_stats), content_type='application/json')

@app.get("/team_fielding")
async def get_team_fielding():
    # Return all the teams combined fielding statistics for the provided season
    year = request.args.get("year")
    team_fielding_stats = team_fielding(year)
    team_fielding_stats = json.loads(team_fielding_stats.to_json(orient='table'))

    return quart.Response(json.dumps(team_fielding_stats), content_type='application/json')



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
    with open("ai-plugin.json") as f:
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