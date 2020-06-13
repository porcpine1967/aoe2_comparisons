""" Basic objects used throughout the system."""

from collections import defaultdict, Counter
import csv
from datetime import datetime
import json
import os
import pathlib
import re
from statistics import median, stdev

ROOT_DIR = pathlib.Path(__file__).parent.parent.absolute()

import numpy as np
from utils.lookup import Lookup
import utils.models

LOOKUP = Lookup()

class Player(utils.models.Player):
    pass

class MatchReport(utils.models.MatchReport):
    data_file_template = '{}/team-data/match_{{}}_data.csv'.format(utils.models.ROOT_DIR)
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
    data_file_template = '{}/team-data/matches_for_{{}}.csv'.format(ROOT_DIR)
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
        return utils.models.Match.all(Match, include_duplicates)

class Rating():
    """Holds each change of rating for a single player (loaded from api with old rating extrapolated)"""
    header = ['Profile Id', 'Rating', 'Old Rating', 'Wins', 'Losses', 'Drops', 'Timestamp', 'Won State']
    data_dir = '{}/team-data'.format(ROOT_DIR)
    data_file_template = '{}/team-data/ratings_for_{{}}.csv'.format(ROOT_DIR)
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
        """ Returns all ratings for a profile """
        data_file = Rating.data_file_template.format(profile_id)
        if not os.path.exists(data_file):
            raise RuntimeError('No rating data available for', profile_id)
        ratings = []
        with open(data_file) as f:
            reader = csv.reader(f)
            for row in reader:
                try:
                    ratings.append(Rating.from_csv(row))
                except ValueError:
                    pass
        return ratings

    def lookup_for(profile_id):
        lookup = defaultdict(lambda:[])
        for rating in Rating.all_for(profile_id):
            lookup[rating.old_rating].append(rating)
        return lookup

class User():
    """Holds player data (loaded from api)"""
    header = ['Profile Id', 'Name', 'Rating', 'Number Games Played',]
    data_file = '{}/team-data/users.csv'.format(ROOT_DIR)
    def __init__(self, data):
        self.profile_id = data['profile_id']
        self.name = data['name']
        self.rating = data['rating']
        self.game_count = data['games']
        self.should_update = True

    @property
    def to_csv(self):
        return [self.profile_id, self.name, self.rating, self.game_count, self.should_update]

    def update(self, data):
        # If should have updated and ratings file not updated since last time users updated, don't change
        rating_file = Rating.data_file_template.format(self.profile_id)
        if not os.path.exists(rating_file):
            self.should_update = True
        else:
            should_update = self.game_count != data['games']
            if self.should_update and not should_update:
                self.should_update = os.stat(User.data_file).st_mtime > os.stat(rating_file).st_mtime
            else:
                self.should_update = should_update
        self.name = data['name']
        self.rating = data['rating']
        self.game_count = data['games']

    def from_csv(row):
        u = User({'profile_id': int(row[0]), 'name': row[1], 'rating': int(row[2]), 'games': int(row[3])})
        if len(row) > 4:
            u.should_update = row[4] == 'True'
        return u

    def all():
        if not os.path.exists(User.data_file):
            raise RuntimeError('No user data file available')
        users = []
        with open(User.data_file) as f:
            reader = csv.reader(f)
            for row in reader:
                try:
                    users.append(User.from_csv(row))

                except ValueError:
                    pass
        return users

class PlayerRating:
    """ Caches last calculated best rating for players. """
    data_file_template = '{}/team-data/player_rating_{{}}_{{}}_data.csv'.format(ROOT_DIR)
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
