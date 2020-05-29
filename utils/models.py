""" Basic objects used throughout the system."""

from collections import defaultdict
import csv
import json
import os
import pathlib
import re

ROOT_DIR = pathlib.Path(__file__).parent.parent.absolute()

import numpy as np
from utils.lookup import constants

LOOKUP = constants()


class MatchReport():
    """ Holds match information from both players' perspective (loaded from Match records). """
    data_file_template = '{}/data/match_{{}}_data.csv'.format(ROOT_DIR)
    def __init__(self, row):
        self.code = row[0]
        self.rating_1 = int(row[1])
        self.rating_2 = int(row[2])
        self.score = int(row[3])
        self.winner = int(row[4])
        c1, c2, m = self.code.split('-')
        self.civ_1 = LOOKUP['civ'][int(c1)]
        self.civ_2 = LOOKUP['civ'][int(c2)]
        self.mirror = c1 == c2
        self.map = LOOKUP['map_type'][int(m)]

    def rating_edges(data_set_type, map_type, split, exclude_mirror=True):
        ratings = []
        for report in MatchReport.by_map(data_set_type, map_type):
            if exclude_mirror and self.mirror:
                continue
            ratings.append(report.rating_1)
            ratings.append(report.rating_2)
        pct = 1.0/split
        return [int(np.quantile(ratings, pct + pct*i)) for i in range(split - 1)]

    def all(data_set_type):
        reports = []
        with open(MatchReport.data_file_template.format(data_set_type)) as f:
            reader = csv.reader(f)
            for row in reader:
                reports.append(MatchReport(row))
        return reports

    def by_map(data_set_type, map_type):
        reports = []
        with open(MatchReport.data_file_template.format(data_set_type)) as f:
            reader = csv.reader(f)
            for row in reader:
                _, _, m = row[0].split('-')
                if m == str(map_type):
                    reports.append(MatchReport(row))
        return reports

    def by_map_and_rating(data_set_type, map_type, lower, upper):
        reports = []
        with open(MatchReport.data_file_template.format(data_set_type)) as f:
            reader = csv.reader(f)
            for row in reader:
                _, _, m = row[0].split('-')
                if m == str(map_type):
                    report = MatchReport(row)
                    if lower <= report.rating_1 < upper or lower <= report.rating_2 < upper:
                        reports.append(report)
        return reports

class Match():
    """Holds match data from one player's perspective (loaded from api) """
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

    def player_won(profile_id, rating, started):
        """ Looks in the ratings file for ratings with the same rating and a timestamp less than an hour ahead
        and and determines whether the player won or lost. If both or neither potential outcomes are
        available, it returns a "don't know" response (None). """
        won_state = set(('won',))
        possibles = set()
        try:
            for rating in Rating.lookup_for(profile_id)[rating]:
                if 0 < rating.timestamp - started < 3600:
                    possibles.add(rating.won_state)
        except KeyError:
            """ Thrown when there are no rating records matching that player's current rating. """
            pass
        if len(possibles) != 1: # we have a contradiction or no information
            return None
        return possibles == won_state

    def determine_winner(self):
        """ Determines which player won be assessing the combined information from both players.
        Ideal case is one player knows it won and the other knows it lost. Else it just goes
        with the one who knows. If neither knows or they disagree, it returns 0 meaning cannot determine. """
        player_1_won = Match.player_won(self.player_id_1, self.rating_1, self.started)
        player_2_won = Match.player_won(self.player_id_2, self.rating_2, self.started)
        # Player 1 and player 2 either both won or both lost or we don't know either
        if player_1_won == player_2_won:
            return 0
        # Player 1 won and/or player 2 lost
        if player_1_won or player_2_won == False:
            return 1
        # Player 2 won and/or player 1 lost
        if player_2_won or player_1_won == False:
            return 2

    def to_record(self):
        """ Outputs self as record for analysis.
        Note: "Player 1" and "Player 2" do not map to player_1 and player_2 in the match record. Unless it
        is a mirror match. Instead, they indicate the player associated with the lowest and highest ordinal civ code.
        Competition-code: {lowest ordinal civ code}-{highest ordinal civ code}-{map code}
        Player 1 Rating: Rating of player with the lowest ordinal civ code
        Player 2 Rating: Rating of player with the highest ordinal civ code
        Rating difference: The difference between the rating of the winning player minus the rating of the
                           losing player. It will be negative if a lower-rated player upsets a higher-rated player.
        Winner: 1 or 2, depending on which player won
        """
        determined_winner = self.determine_winner()
        if self.civ_1 > self.civ_2:
            code = '{}-{}-{}'.format(self.civ_2, self.civ_1, self.map_type)
            rating_1 = self.rating_2
            rating_2 = self.rating_1
            winner = determined_winner == 1 and 2 or 1
        else:
            code = '{}-{}-{}'.format(self.civ_1, self.civ_2, self.map_type)
            rating_1 = self.rating_1
            rating_2 = self.rating_2
            winner = determined_winner
        if determined_winner == 0:
            winner = 0
            score = 0
        elif determined_winner == 1:
            score = self.rating_1 - self.rating_2
        else:
            score = self.rating_2 - self.rating_1
        return [code, rating_1, rating_2, score, winner,]

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
        else:
            self.winner = 0

    def mark_won(self, profile_id):
        if str(profile_id) == self.player_id_1:
            self.winner = 1
        elif str(profile_id) == self.player_id_2:
            self.winner = 2
        else:
            self.winner = 0

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
        data_file_pattern = re.compile(r'matches_for_[0-9]+\.csv$')
        data_dir = pathlib.Path(Match.data_file_template.format('')).parent.absolute()
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
    """Holds each change of rating for a single player (loaded from api with old rating extrapolated)"""
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
    """Holds player data (loaded from api)"""
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
