""" Basic objects used throughout the system."""

from collections import defaultdict, Counter
import csv
from datetime import datetime
import json
import os
import re
from statistics import median, stdev


import numpy as np
from utils.lookup import Lookup
import utils.models

ROOT_DIR = utils.models.ROOT_DIR
DATA_DIR = '{}/team-data'.format(utils.models.ROOT_DIR)
LOOKUP = Lookup()
leaderboard = 4

class Player(utils.models.Player):
    pass

class MatchReport(utils.models.MatchReport):
    def data_file(data_set_type):
        return '{}/match_{}_data.csv'.format(DATA_DIR, data_set_type)
    def all(data_set_type):
        return utils.models.MatchReport.all(MatchReport, data_set_type)
    def by_rating(data_set_type, lower, upper):
        return utils.models.MatchReport.by_rating(MatchReport, data_set_type, lower, upper)
    def by_map(data_set_type, map_type):
        return utils.models.MatchReport.by_map(MatchReport, data_set_type, map_type)
    def by_map_and_rating(data_set_type, map_type, lower, upper):
        return utils.models.MatchReport.by_map_and_rating(MatchReport, data_set_type, map_type, lower, upper)

class Match(utils.models.Match):
    """Holds match data from one player's perspective (loaded from api) """
    def data_file(profile_id):
        return '{}/matches_for_{}.csv'.format(DATA_DIR, profile_id)
    header = ['Match Id', 'Started', 'Map', 'Civs', 'Ratings', 'Player Ids', 'Teams', 'Version',]
    def __init__(self, data):
        try:
            self.match_id = str(data['match_id'])
            self.started = data['started']
            self.map_type = data['map_type']
            self.players = {}
            for player in data['players']:
                self.players[str(player['profile_id'])] = {'civ': player['civ'], 'rating': player['rating'], 'team': player['team']}
            self.version = data['version']
        except IndexError:
            print(json.dumps(data))
            raise

    @property
    def to_csv(self):
        ids = []
        civs = []
        ratings = []
        teams = []
        for player_id in sorted(self.players):
            data = self.players[player_id]
            ids.append(player_id)
            civs.append(str(data['civ']))
            ratings.append(str(data['rating']))
            teams.append(str(data['team']))
        return [ self.match_id, self.started, self.map_type, ':'.join(civs), ':'.join(ratings), ':'.join(ids), ':'.join(teams), self.version]

    def from_csv(row):
        civs = row[3].split(':')
        ratings = row[4].split(':')
        ids = row[5].split(':')
        teams = row[6].split(':')
        players = []
        for i in range(len(civs)):
            players.append({ 'civ': int(civs[i]), 'profile_id': ids[i], 'rating': int(ratings[i]), 'team': int(teams[i]) })
        match_data = {
            'match_id': row[0],
            'started': int(row[1]),
            'map_type': int(row[2]),
            'players': players,
            'version': row[7],
            }
        match = Match(match_data)
        return match

    def to_record(self):
        return super().to_record(Match, Rating)

    def all_for(profile_id):
        return utils.models.Match.all_for(Match, profile_id)
    def all(include_duplicates=False):
        return utils.models.Match.all(utils.team_models, include_duplicates)

class Rating():
    """Holds each change of rating for a single player (loaded from api with old rating extrapolated)"""
    header = ['Profile Id', 'Rating', 'Old Rating', 'Wins', 'Losses', 'Drops', 'Timestamp', 'Won State']
    def data_file(profile_id):
        return '{}/ratings_for_{}.csv'.format(DATA_DIR, profile_id)
    def __init__(self, profile_id, data):
        self.profile_id = profile_id
        self.rating = data['rating']
        self.num_wins = data['num_wins']
        self.num_losses = data['num_losses']
        self.drops = data['drops']
        self.timestamp = data['timestamp']
        self.old_rating = None
        self.won_state = None

    @property
    def to_csv(self):
        return [self.profile_id, self.rating, self.old_rating, self.num_wins, self.num_losses, self.drops, self.timestamp, self.won_state,]

    def from_csv(row):
        rating = Rating(row[0], {'rating': int(row[1]),
                               'num_wins': int(row[3]),
                               'num_losses': int(row[4]),
                               'drops': int(row[5]),
                               'timestamp': int(row[6])})
        rating.won_state = row[7]
        rating.old_rating = int(row[2])
        return rating

    def all_for(profile_id):
        return utils.models.Rating.all_for(Rating, profile_id)

    def lookup_for(profile_id):
        return utils.models.Rating.lookup_for(Rating, profile_id)

class User(utils.models.User):
    """Holds player data (loaded from api)"""
    header = ['Profile Id', 'Name', 'Rating', 'Number Games Played',]
    def data_file():
        return '{}/users.csv'.format(DATA_DIR)
    def all():
        return utils.models.User.all(User)
    def update(self, data):
        return super().update(User, Rating, data)
    def from_csv(row):
        return utils.models.User.from_csv(User, row)
    @property
    def to_csv(self):
        return [self.profile_id, self.name, self.rating, self.game_count, self.should_update]

class PlayerRating:
    """ Caches last calculated best rating for players. """
    def data_file(data_set_type, mincount=5):
        return '{}/player_rating_{{}}_{{}}_data.csv'.format(DATA_DIR, data_set_type, mincount)
    def ratings_for(data_set_type, mincount=5, update=False):
        data_file = PlayerRating.data_file_template.format(data_set_type, mincount)
        if update or not os.path.exists(data_file):
            rows = []
            for player in Player.rated_players(MatchReport.all(data_set_type), mincount):
                rows.append([player.player_id, player.best_rating(mincount),])
            with open(data_file, 'w') as f:
                csv.writer(f).writerows(rows)
        ratings = {}
        with open(data_file) as f:
            reader = csv.reader(f)
            for row in reader:
                ratings[row[0]] = int(row[1])
        return ratings

class CachedPlayer(Player):
    def __init__(self, player_id, matches, best_rating):
        self.player_id = player_id
        self.matches = matches
        self.best_rating = best_rating

    def rated_players(data_set_type, mincount=5):
        ratings = PlayerRating.ratings_for(data_set_type, mincount)
        players = []
        for player in Player.player_values(MatchReport.all(data_set_type)):
            if player.player_id in ratings:
                players.append(CachedPlayer(player.player_id, player.matches, ratings[player.player_id]))
        return players

if __name__ == '__main__':
    for data_set_type in ('test', 'model', 'verification',):
        PlayerRating.ratings_for(data_set_type, update=True)
