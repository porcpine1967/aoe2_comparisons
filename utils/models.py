""" Basic objects used throughout the system."""

import csv
import json
import os
import pathlib
import re

ROOT_DIR = pathlib.Path(__file__).parent.parent.absolute()

class Match():
    """Holds match data from api"""
    data_file_template = '{}/data/matches_for_{{}}.csv'.format(ROOT_DIR)
    header = ['Match Id', 'Started', 'Map', 'Civ 1', 'RATING 1', 'Player 1', 'Civ 2', 'RATING 2', 'Player 2', 'Winner',]
    def __init__(self, data):
        try:
            self.match_id = str(data['match_id'])
            self.started = data['started']
            self.map_type = data['map_type']
            self.player_id_1 = str(data['players'][0]['profile_id'])
            self.civ_1 = data['players'][0]['civ']
            self.rating_1 = data['players'][0]['rating']
            self.player_id_2 = str(data['players'][1]['profile_id'])
            self.civ_2 = data['players'][1]['civ']
            self.rating_2 = data['players'][1]['rating']
            self.winner = 0
        except IndexError:
            print(json.dumps(data))
            raise

    def rating_for(self, profile_id):
        if str(profile_id) == self.player_id_1:
            return self.rating_1
        elif str(profile_id) == self.player_id_2:
            return self.rating_2
        else:
            return None

    def mark_lost(self, profile_id):
        if profile_id == self.player_id_1:
            self.winner = 2
        elif profile_id == self.player_id_2:
            self.winner = 1
        
    def mark_won(self, profile_id):
        if str(profile_id) == self.player_id_1:
            self.winner = 1
        elif str(profile_id) == self.player_id_2:
            self.winner = 2

    @property
    def winner_id(self):
        if self.winner == 1:
            return self.player_id_1
        elif self.winner == 2:
            return self.player_id_2
        else:
            return None

    @property
    def rating_diff(self):
        """ Returns the winner's rating minus the looser's rating """
        if self.winner == 1:
            return self.rating_1 - self.rating_2
        elif self.winner == 2:
            return self.rating_2 - self.rating_1

    @property
    def to_csv(self):
        return [ self.match_id, self.started, self.map_type, self.civ_1, self.rating_1, self.player_id_1,
                 self.civ_2, self.rating_2, self.player_id_2, self.winner, ]

    def from_csv(row):
        match_data = {
            'match_id': row[0],
            'started': int(row[1]),
            'map_type': int(row[2]),
            'players': [
                { 'civ': int(row[3]), 'rating': int(row[4]), 'profile_id': row[5], },
                { 'civ': int(row[6]), 'rating': int(row[7]), 'profile_id': row[8], },
                ],
            }
        match = Match(match_data)
        match.winner = int(row[9])
        return match

    def elo(profile_id):
        matches = Match.all_for(profile_id)
        won = 0
        for cnt, match in enumerate(matches):
            if match.winner_id == profile_id:
                won += 1
            print(won, cnt - won, match.rating_for(profile_id))

    def all_for(profile_id):
        """ Returns all matches for a profile """
        data_file = Match.data_file_template.format(profile_id)
        if not os.path.exists(data_file):
            raise RuntimeError('No match data available for {}'.format(profile_id))
        matches = []
        with open(data_file) as f:
            reader = csv.reader(f)
            for row in reader:
                try:
                    matches.append(Match.from_csv(row))
                except ValueError:
                    pass
        return matches

    def all(include_duplicates=False):
        """ Returns all matches for all users, with duplicates removed """
        data_file_pattern = re.compile('matches_for_[0-9]+\.csv')
        data_dir = '{}/data'.format(ROOT_DIR)
        matches = []
        match_ids = set()
        for filename in os.listdir(data_dir):
            if data_file_pattern.match(filename):
                with open('{}/{}'.format(data_dir, filename)) as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if include_duplicates or row[0] not in match_ids:
                            match_ids.add(row[0])
                            try:
                                matches.append(Match.from_csv(row))
                            except ValueError:
                                pass
        return matches
        
class Rating():
    """Holds rating data from api
    example: "rating":1150,"num_wins":27,"num_losses":26,"streak":-4,"drops":0,"timestamp":1589316182"""
    header = ['Profile Id', 'Rating', 'Wins', 'Losses', 'Drops', 'Timestamp',]
    data_file_template = '{}/data/ratings_for_{{}}.csv'.format(ROOT_DIR)
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
            raise RuntimeError('No rating data available')
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
    """Holds user data from user.csv"""
    header = ['Profile Id', 'Name', 'Rating', 'Number Games Played',]
    data_file = '{}/data/users.csv'.format(ROOT_DIR)
    def __init__(self, data):
        self.profile_id = data['profile_id']
        self.name = data['name']
        self.rating = data['rating']
        self.game_count = data['games']
        self.ratings = []

    @property
    def to_csv(self):
        return [self.profile_id, self.name, self.rating, self.game_count,]

    def from_csv(row):
        return User({'profile_id': row[0], 'name': row[1], 'rating': int(row[2]), 'games': int(row[3])})

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

if __name__ == '__main__':
    print(len(Match.all()))
