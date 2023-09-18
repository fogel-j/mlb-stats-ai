import json
import os
from datetime import datetime
import itertools

import quart
import quart_cors
from quart import request, jsonify

from helpers import helper

# Python baseball stat retrieval imports
from pybaseball import \
standings, batting_stats_bref, pitching_stats_bref, team_batting_bref, team_fielding_bref, \
team_pitching_bref, playerid_lookup, statcast_batter, statcast_outs_above_average, \
statcast_pitcher, top_prospects, batting_stats, team_batting, starting_pitching_stats, \
relief_pitching_stats, cache, team_pitching, schedule_and_record, team_game_logs, \
statcast_sprint_speed, statcast_pitcher_pitch_arsenal, player_game_logs, get_splits

import logging


# Note: Setting CORS to allow chat.openapi.com is only required when running a localhost plugin
app = quart_cors.cors(quart.Quart(__name__), allow_origin="https://chat.openai.com")

# logging.basicConfig(filename='/home/LogFiles/server_errors.log', level=logging.ERROR)
logger = logging.getLogger()

# app = quart.Quart(__name__)

cache.enable()

@app.get("/standings")
async def get_standings():
    # Return the overall MLB standings
    overall_standings = []
    year = int(request.args.get("year"))
    standing = standings(year)
    for i in standing:
        overall_standings.append(json.loads(i.to_json(orient='table')))
    

    return quart.Response(json.dumps(overall_standings), status=200, content_type='application/json')

@app.get("/news")
async def get_news():
    # Return relevant news articles for the team being asked about
    team_name = request.args.get("team_name")

    if not team_name.isalnum():
        return quart.abort(400, "Invalid team_name parameter. It must be a string consisting only of alphanumeric characters.")

    directory_path = os.getcwd() + '/mlb_crawler/scraped_data/' 
    all_files = os.listdir(directory_path)
    news_files = [f for f in all_files if f.startswith('mlb_news')]

    articles = []
    for filename in news_files:
        with open(os.path.join(directory_path, filename)) as file:
            data = json.load(file)
            # Filter articles for the requested team
            team_name = team_name.lower()
            # Due to the current token prompt capacity, we must limit the number of articles collected
            team_articles = list(itertools.islice((article for article in data if article['team'] == team_name), 7))
            articles.extend(team_articles)

    
    return quart.Response(json.dumps(articles, ensure_ascii=False), content_type='application/json', status=200)

@app.get("/batting_stats_individual")
async def get_batting_stats_individual():
    #Retrieves an individual's batting statistics from Fangraphs, providing detailed 320 column batting information
    year = int(request.args.get("year"))
    fg_id = int(request.args.get("key_fangraphs"))
    
    batting = batting_stats(year, qual=4)
    individual_batting = batting[batting['IDfg'] == fg_id]
    individual_batting = batting.iloc[:, :47]
    individual_batting = json.loads(individual_batting.to_json(orient='records'))

    

    return quart.Response(json.dumps(individual_batting), content_type='application/json')


@app.get("/batting_stats")
async def get_batting_stats():
    # Return a specific batting statistic at a season level for all players from Fangraphs
    # To see what data is being collected refer to 

    year = int(request.args.get("year"))
    bat_stat = request.args.get("batting_stat")

    if year < 2008:
        return quart.Response("The starting date is before data started being collected in 2008.", status=500)
    
    batting = batting_stats(year)
    filtered_batting = batting[['Name',bat_stat]]
    filtered_batting = filtered_batting.sort_values(by=[bat_stat], ascending=False)
    # table = table.to_markdown()
    filtered_batting = json.loads(filtered_batting.to_json(orient='records'))
    

    return quart.Response(json.dumps(filtered_batting),content_type='application/json')

@app.get("/starting_pitching_stats")
async def get_starting_pitching_stats():
    # Return a specific pitching statistic at a season level for all starting pitcher players from Fangraphs
    
    year = int(request.args.get("year"))
    pitching_stat = request.args.get("pitching_stat")
    if year < 2008:
        return quart.Response("The starting date is before data started being collected in 2008.", status=500)
    
    pitching = starting_pitching_stats(year)
    filtered_pitching = pitching[['Name', 'Team', pitching_stat]]
    filtered_pitching = filtered_pitching.sort_values(by=[pitching_stat])
    
    filtered_pitching = json.loads(filtered_pitching.to_json(orient='records'))
    

    return quart.Response(json.dumps(filtered_pitching), content_type='application/json')

@app.get("/relief_pitching_stats")
async def get_relief_pitching_stats():
    # Return a specific pitching statistic at a season level for all starting pitcher players from Fangraphs
    
    year = int(request.args.get("year"))
    pitching_stat = request.args.get("pitching_stat")
    if year < 2008:
        return quart.Response("The starting date is before data started being collected in 2008.", status=500)
    
    pitching = relief_pitching_stats(year)
    filtered_pitching = pitching[['Name','Team', pitching_stat]]
    filtered_pitching = filtered_pitching.sort_values(by=[pitching_stat])
    
    filtered_pitching = json.loads(filtered_pitching.to_json(orient='records'))
    

    return quart.Response(json.dumps(filtered_pitching), content_type='application/json')


@app.get("/pitching_stats_individual")
async def get_pitching_stats_individual():
    # Return the pitching statistics for an individual pitcher for the season specified
    year = int(request.args.get("year"))
    fg_id = int(request.args.get("key_fangraphs"))
    pitching = starting_pitching_stats(year, qual=0)

    individual_pitching = pitching[pitching['IDfg'] == fg_id]
    individual_pitching = json.loads(individual_pitching.to_json(orient='records'))

    return quart.Response(json.dumps(individual_pitching), content_type='application/json')


@app.get("/team_batting")
async def get_team_batting():
    # Return the batting statistics from Baseball Reference for each player on the team for the provided season
    team_abr = request.args.get('team_abbreviation')
    year = int(request.args.get("year"))
    team_batting_stats = team_batting_bref(team_abr,year)
    team_batting_stats = json.loads(team_batting_stats.to_json(orient='records'))
    

    return quart.Response(json.dumps(team_batting_stats), content_type='application/json')


@app.get("/team_batting_combined")
async def get_team_batting_combined():
    # Returns the combined batting statistics for each team across the MLB for the season being specified
    year = int(request.args.get("year"))
    team_abr = request.args.get('team_abbreviation')
    batting_stat = request.args.get('batting_stat')

    team_batting_stats = team_batting(year)


    if team_abr != None: # Get's a bunch of combined batting stats for one specific team
        team_batting_stats = team_batting_stats[team_batting_stats['Team'] == team_abr]
    
    else:
        # Moving team abbreviation to the first column for easier model interpretation
        cols = team_batting_stats.columns.to_list()
        cols = [cols[2]] + cols[:2] + cols[3:]
        team_batting_stats = team_batting_stats[cols]
        team_batting_stats = team_batting_stats.iloc[:, :40] # consider adding more columns

    if batting_stat != None: # Filter a single stat 
        team_batting_stats = team_batting_stats[['Team',batting_stat]]
        team_batting_stats = team_batting_stats.sort_values(by=batting_stat, ascending=False)
        
    team_batting_stats = json.loads(team_batting_stats.to_json(orient='records'))
    

    return quart.Response(json.dumps(team_batting_stats), content_type='application/json')

@app.get("/team_fielding")
async def get_team_fielding():
    # Return the fielding statistics from Baseball Reference for each player on the team for the provided season
    team_abr = request.args.get('team_abbreviation')
    year = int(request.args.get("year"))
    team_fielding_stats = team_fielding_bref(team_abr,year)
    team_fielding_stats = json.loads(team_fielding_stats.to_json(orient='records'))
    

    return quart.Response(json.dumps(team_fielding_stats), content_type='application/json')

@app.get("/team_pitching")
async def get_team_pitching():
    # Return the pitching statistics from Baseball Reference for each player on the team for the provided season
    team_abr = request.args.get('team_abbreviation')
    year = int(request.args.get("year"))
    team_pitching_stats = team_pitching_bref(team_abr,year)
    team_pitching_stats = json.loads(team_pitching_stats.to_json(orient='records'))
    # team_pitching_stats = team_pitching_stats.to_markdown()
    

    return quart.Response(json.dumps(team_pitching_stats), content_type='application/json')

@app.get("/team_pitching_combined")
async def get_team_pitching_combined():
    # Return the combined pitching statistics for a team from Fangraphs
    year = int(request.args.get("year"))
    team_abr = request.args.get("team_abbreviation")
    team_pitching_stats = team_pitching(year)
    if team_abr != None:
        team_pitching_stats = team_pitching_stats[team_pitching_stats['Team'] == team_abr]
    
    else:
        # Moving team abbreviation to the first column for easier model interpretation
        cols = team_pitching_stats.columns.to_list()
        cols = [cols[2]] + cols[:2] + cols[3:]
        team_pitching_stats = team_pitching_stats[cols]
        team_pitching_stats = team_pitching_stats.iloc[:, :40] # consider adding more columns
        
    team_pitching_stats = json.loads(team_pitching_stats.to_json(orient='records'))
    

    return quart.Response(json.dumps(team_pitching_stats), content_type='application/json')


@app.get("/playerid_lookup")
async def get_playerid_lookup():
    # Retrieves the player id based on a players name that is given
    first_name = request.args.get("first")
    last_name = request.args.get("last")
    playerid = playerid_lookup(last_name, first_name, fuzzy=True)

    #If multiple players have the same name or multiple results are returned for the function 
    if len(playerid.index) > 1:
        heading = 'Multiple MLB players found'
        playerid = playerid.to_markdown()
        return quart.Response(response=heading+playerid, status=200, content_type='text/markdown')
        
    
    #Test with the model to see if it can retrieve the key_mlbam from the output and adjust the YAML file accordingly
    playerid = json.loads(playerid.to_json(orient='records'))

    return quart.Response(json.dumps(playerid), content_type='application/json', status=200)

@app.get("/statcast_batter")
async def get_statcast_batter():
    #Retrieves detailed pitch-level statcast information about a player's batting performance over a given time period.  
    starting_date = request.args.get('date')
    mlbam_player_id = int(request.args.get('key_mlbam'))

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

    batter_stats = json.loads(batter_stats.to_json(orient='records'))
    

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
    fielding = json.loads(fielding.to_json(orient='records'))
    print(helper.num_tokens(str(fielding)))
    # TODO - There are more stats that can be retrieved for player fielding from pybaseball. Testing should be done with model for the other functions

    return quart.Response(json.dumps(fielding), content_type='application/json')

@app.get("/statcast_pitcher")
async def get_statcast_pitcher():
    #Retrieves pitch-level statistics for a pitcher
    starting_date = request.args.get('date')
    mlbam_player_id = int(request.args.get('key_mlbam'))

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
    pitching = json.loads(pitching.to_json(orient='records'))
    
    return quart.Response(json.dumps(pitching), content_type='application/json')

@app.get("/statcast_pitch_arsenal")
async def get_statcast_pitch_arsenal():
    # Retrieves the percentage of each pitch thrown by the pitcher being queried
    year = int(request.args.get('year'))
    mlbam_player_id = int(request.args.get('key_mlbam'))

    if int(year) < 2008:
        return quart.Response("The starting date is before statcast data started being collected in 2008.", status=500)
    
    pitch_arsenal = statcast_pitcher_pitch_arsenal(year=year,arsenal_type='n_')
    player_pitch_arsenal = pitch_arsenal[pitch_arsenal['pitcher'] == mlbam_player_id]

    # Rename the columns for easier interpretation
    player_pitch_arsenal = player_pitch_arsenal.rename(columns={'n_ff': '4-seam fastball', 
                                                            'n_si': 'sinker', 
                                                            'n_fc': 'cutter', 
                                                            'n_sl': 'slider', 
                                                            'n_ch': 'changeup',
                                                            'n_cu': 'curveball',
                                                            'n_fs': 'splitter',
                                                            'n_kn': 'knuckleball',
                                                            'n_st': 'sweeper',
                                                            'n_sv': 'slurve'})

    player_pitch_arsenal = json.loads(player_pitch_arsenal.to_json(orient='records'))

    return quart.Response(json.dumps(player_pitch_arsenal), content_type='application/json')

@app.get("/statcast_sprint_speed")
async def get_statcast_sprint_speed():
    # Retrieves the sprint speed for the top 250 players across the MLB
    year = request.args.get('year')

    sprint = statcast_sprint_speed(year)

    # We must filter the output because of OpenAI token limits
    sprint = sprint[['last_name', 'first_name', 'team', 'sprint_speed']]
    sprint = sprint.head(250)
    sprint = json.loads(sprint.to_json(orient='records'))


    return quart.Response(json.dumps(sprint), content_type='application/json')

@app.get("/top_prospects")
async def get_top_prospects():
    #Retrieves the top prospects for a team or across the entire MLB
    team_name = request.args.get('team_name')
    player_type = request.args.get('player_type')
    prospects = top_prospects(teamName=team_name,playerType=player_type)
    # We must cut down to top 50 prospects due to token limit from OpenAI
    prospects = prospects.head(25)

    prospects = json.loads(prospects.to_json(orient='records'))
    

    return quart.Response(json.dumps(prospects), content_type='application/json')

@app.get("/schedule_and_record")
async def get_schedule_and_record():
    # Retrieves the schedule and record of game-level results for a given month of a season
    year = int(request.args.get('year'))
    month = request.args.get('month')
    team_abr = request.args.get('team_abbreviation')

    team_record = schedule_and_record(year, team_abr)
    team_record = team_record.iloc[:, :-1]
    # Must filter the data based on the month due to token limits
    team_record = team_record[team_record['Date'].str.contains(month)]
    team_record = team_record.drop(['Time','D/N','Attendance', 'Win', 'Loss','Save'],axis=1)
    team_record = json.loads(team_record.to_json(orient='records'))


    return quart.Response(json.dumps(team_record), content_type='application/json')

@app.get("/team_game_logs")
async def get_team_game_logs():
    # Retrieves detailed batting or pitching statistics for a team over a month time period
    year = int(request.args.get('year'))
    month = request.args.get('month')
    team_abr = request.args.get('team_abbreviation')
    log_type = request.args.get('log_type')

    game_logs = team_game_logs(year,team_abr,log_type)
    # Must filter the data based on the month due to token limits
    try: 
        game_logs = game_logs[game_logs['Date'].str.contains(month)]
    except:
        return quart.Response('No team games found for that month!', status=500)

    game_logs = game_logs.drop(['OppStart', 'Thr', 'BA', 'SLG','OPS','LOB','NumPlayers','ROE', 'IBB', 'SF', 'SH','RBI','Home','GDP','OBP','PA','AB'],axis=1)
    
    game_logs = json.loads(game_logs.to_json(orient='records'))


    return quart.Response(json.dumps(game_logs), content_type='application/json')

@app.get("/player_game_logs")
async def get_player_game_logs():
    # Retrieves the individual game stats for each game the player played in for a given year
    year = int(request.args.get('year'))
    month = request.args.get('month')
    player_id = request.args.get('key_bbref')
    log_type = request.args.get('log_type')
    try:
        player_logs = player_game_logs(year,player_id,log_type)
        #Must filter the data based on the month due to token limits
        player_logs = player_logs[player_logs['Date'].str.contains(month)]
    except: 
        return quart.Response(json.dumps({'error': "No player game logs found for those parameters. Please check you are using the proper 'log_type' and the player played a game during that month and year."}), status=500)
    
    player_logs = player_logs.iloc[:, :16]
    player_logs = player_logs.drop(['Inngs'], axis=1)

    player_logs = json.loads(player_logs.to_json(orient='records'))


    return quart.Response(json.dumps(player_logs), content_type='application/json')


@app.get("/player_split_stats")
async def get_player_split_stats():
    # Retrieves a player's split stats over a given season
    year = int(request.args.get('year'))
    player_id = request.args.get('key_bbref')
    split_type = request.args.get('split_type')
    split_type = split_type.replace('_',' ')

    split_data = get_splits(playerid=player_id,year=year,player_info=True)

    if split_data[1]['Position'].strip() == 'Pitcher':
        split_data = get_splits(playerid=player_id,year=year,pitching_splits=True)
        
    split_data = split_data[0]
    split_data = split_data.loc[split_type]
    split_data = split_data.reset_index()

    split_data = json.loads(split_data.to_json(orient='records'))

    return quart.Response(json.dumps(split_data), content_type='application/json')



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

@app.get("/api/health")
async def healthcheck():
    return quart.Response("ALIVE", status=200)

@app.errorhandler(404)
async def page_not_found(e):
    return "Page Not Found" , 404

@app.errorhandler(500)
async def internal_server_error(error):
    logger.error(f"Error on URL: {request.url}")
    logger.error(f"Internal Server Error: {error}")
    return quart.Response("Internal Server Error"), 500

if __name__ == "__main__":
    app.run()