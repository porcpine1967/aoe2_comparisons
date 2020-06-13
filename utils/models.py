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

LOOKUP = Lookup()

class Player:
    """ Holds information about a given player of the game (loaded from MatchReport data). """
    def __init__(self, player_id):
        self.player_id = player_id
        self.matches = []
        self._best_ratings = {}
        self._best_stdevs = {}

    def best_stdev(self, mincount):
        if not self._best_stdevs[mincount]:
            self.best_rating(mincount)
        return self._best_stdevs[mincount]

    def best_rating(self, mincount):
        """ Returns the median of the slice of ratings length {mincount} with the lowest standard deviation. """
        if len(self.ratings) < mincount*1.5:
            return

        key = mincount
        # return cached calculation
        if key in self._best_ratings:
            return self._best_ratings[key]

        sorted_ratings = sorted(self.ratings)
        best_group = sorted_ratings[:mincount]
        best_std = stdev(best_group)
        for i in range(1, len(sorted_ratings) - mincount):
            test_group = sorted_ratings[i:i+mincount]
            test_std = stdev(test_group)
            if test_std <= best_std:
                best_group = test_group
                best_std = test_std
        best = median(best_group)
        self._best_ratings[key] = best # cache the calculation
        self._best_stdevs[key] = best_std # cache the calculation
        return best

    def add_civ_percentages(self, ctr, map_name, start, edge):
        """ Proportionally adds civs within range to ctr. """
        civ_ctr = Counter()
        for m in self.matches:
            civ, rating, _ = m.info_for(self.player_id)
            if start < rating <= edge and (map_name == 'all' or m.map == map_name):
                civ_ctr[civ] += 1
        total = float(sum(civ_ctr.values()))
        for civ, count in civ_ctr.items():
            ctr[civ] += count/total
        return bool(civ_ctr)

    def add_map_percentages(self, ctr, start, edge):
        """ Proportionally adds maps within range to ctr. """
        map_ctr = Counter()
        for m in self.matches:
            _, rating, _ = m.info_for(self.player_id)
            if start < rating <= edge:
                map_ctr[m.map] += 1
        total = float(sum(map_ctr.values()))
        for m, count in map_ctr.items():
            ctr[m] += count/total
        return bool(map_ctr)

    def ordered_ratings(self, ordering):
        r = []
        if ordering == 'timestamp':
            matches = sorted(self.matches, key=lambda x: x.timestamp)
        else:
            return self.ratings
        for m in matches:
            _, rating, _ = m.info_for(self.player_id)
            r.append(rating)
        return [rating for rating in r if rating > 100]

    @property
    def ratings(self):
        r = []
        for m in self.matches:
            _, rating, _ = m.info_for(self.player_id)
            r.append(rating)
        return [rating for rating in r if rating > 100]

    @property
    def latest_match(self):
        if not self.matches:
            return None
        return sorted(self.matches, key=lambda x: x.timestamp)[-1]

    @property
    def latest_rating(self):
        if not self.matches:
            return None
        m = self.latest_match
        _, rating, _ = m.info_for(self.player_id)
        return rating

    @property
    def latest_civ(self):
        if not self.matches:
            return None
        m = self.latest_match
        civ, _, _ = m.info_for(self.player_id)
        return civ

    @property
    def maps(self):
        """ List of all maps played by this player. """
        return set([m.map for m in self.matches])

    def rated_players(matches, mincount):
        return [p for p in Player.player_values(matches) if p.best_rating(mincount)]

    def player_values(matches):
        player_dict = {}
        for match in matches:
            for player_id in match.players:
                if player_id not in player_dict: player_dict[player_id] = Player(player_id)
            player_dict[match.player_1].matches.append(match)
            player_dict[match.player_2].matches.append(match)
        return player_dict.values()

class MatchReport():
    """ Holds match information from both players' perspective (loaded from Match records). """
    def __init__(self, row):
        self.timestamp = int(row[0])
        self.map = LOOKUP.map_name(row[1])
        self.players = {}
        civs = row[2].split(':')
        ratings = row[3].split(':')
        ids = row[4].split(':')
        teams = row[5].split(':')
        for i in range(len(civs)):
            self.players[ids[i]] = { 'civ': LOOKUP.civ_name(civs[i]), 'rating': int(ratings[i]), 'team': int(teams[i]) }
        team_ctr = Counter()
        for team in teams:
            team_ctr[team] += 1
        self.match_type = 'v'.join([str(i) for i in sorted(team_ctr.values())])
        self.winner = int(row[6])
        self.version = row[7]

    def info_for(self, player_id):
        player_id = str(player_id)
        if not player_id in self.players:
            return None, None, None
        player = self.players[player_id]
        if self.winner == 0:
            winner = 'na'
        elif self.winner == player['team']:
            winner = 'won'
        else:
            winner = 'lost'
        return player['civ'], player['rating'], winner

    def all(klass, data_set_type):
        reports = []
        with open(klass.data_file_template.format(data_set_type)) as f:
            reader = csv.reader(f)
            for row in reader:
                reports.append(MatchReport(row))
        return reports

    def by_map(data_set_type, map_type):
        reports = []
        with open(MatchReport.data_file_template.format(data_set_type)) as f:
            reader = csv.reader(f)
            for row in reader:
                if row[1] == str(map_type):
                    reports.append(MatchReport(row))
        return reports

    def by_map_and_rating(data_set_type, map_type, lower, upper):
        reports = []
        with open(MatchReport.data_file_template.format(data_set_type)) as f:
            reader = csv.reader(f)
            for row in reader:
                if row[1] == str(map_type):
                    report = MatchReport(row)
                    for rating in [p['rating'] for p in self.players.values()]:
                        if lower <= rating < upper:
                            reports.append(report)
                            break
        return reports

class Match():
    """Holds match data from one player's perspective (loaded from api) """
    header = ['Match Id', 'Started', 'Map', 'Civ 1', 'RATING 1', 'Player 1', 'Civ 2', 'RATING 2', 'Player 2', 'Winner',]

    def all_for(klass, profile_id):
        """ Returns all matches for a profile """
        data_file = klass.data_file_template.format(profile_id)
        if not os.path.exists(data_file):
            raise RuntimeError('No match data available for {}'.format(profile_id))
        matches = []
        with open(data_file) as f:
            reader = csv.reader(f)
            for row in reader:
                try:
                    matches.append(klass.from_csv(row))
                except ValueError:
                    pass
        return matches

    def all(klass, include_duplicates=False):
        """ Returns all matches for all users, with duplicates removed """
        data_file_pattern = re.compile(r'matches_for_[0-9]+\.csv$')
        data_dir = pathlib.Path(klass.data_file_template.format('')).parent.absolute()
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
                                matches.append(klass.from_csv(row))
                            except ValueError:
                                pass
        return matches

    def player_won_state(rating_klass, profile_id, rating, started):
        """ Looks in the ratings file for ratings with the same rating and a timestamp less than an hour ahead
        and and determines whether the player won or lost. If both or neither potential outcomes are
        available, it returns a "don't know" response (None). """
        possibles = set()
        try:
            for possible_rating in rating_klass.lookup_for(profile_id)[rating]:
                if 0 < possible_rating.timestamp - started < 3600:
                    possibles.add(possible_rating.won_state)
        except (KeyError, RuntimeError):
            """ Thrown when there are no rating records matching that player's current rating. """
            pass
        if len(possibles) != 1: # we have a contradiction or no information
            return None
        return possibles.pop()

    def determine_winner(self, klass, rating_klass):
        """ Determines which team won by assessing the combined information from all players.
        Ideal case is one team knows it won and the other knows it lost. Else it just goes
        with the one who knows. If neither knows or they disagree, it returns 0 meaning cannot determine. """

        teams = defaultdict(lambda: None)
        for player_id, data in self.players.items():
            player_won_state = klass.player_won_state(rating_klass, player_id, data['rating'], self.started)
            if player_won_state:
                if not teams[data['team']]:
                    teams[data['team']] = player_won_state
                elif teams[data['team']] != player_won_state:
                    teams[data['team']] = 'na'
        answers = list(teams.values())
        if 'na' in answers:
            return 0
        winners = [team for team, answer in teams.items() if answer == 'won']
        if len(winners) == 1:
            return winners[0]
        return 0

    def to_record(self, klass, rating_klass):
        """ Outputs self as record for analysis.
        timestamp
        map code
        colon-delimited civilization codes
        colon-delimited player ratings
        colon-delimited player ids
        colon-delimited teams
        winning team
        version
        """
        winning_team = self.determine_winner(klass, rating_klass)

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
        return [self.started, self.map_type, ':'.join(civs), ':'.join(ratings), ':'.join(ids), ':'.join(teams), winning_team, self.version]

    def rating_for(self, profile_id):
        return self.players[str(profile_id)]['rating']

class Rating():
    """Holds each change of rating for a single player (loaded from api with old rating extrapolated)"""
    header = ['Profile Id', 'Rating', 'Old Rating', 'Wins', 'Losses', 'Drops', 'Timestamp', 'Won State']
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

    def all_for(klass, profile_id):
        """ Returns all ratings for a profile """
        data_file = klass.data_file_template.format(profile_id)
        if not os.path.exists(data_file):
            raise RuntimeError('No rating data available for', profile_id)
        ratings = []
        with open(data_file) as f:
            reader = csv.reader(f)
            for row in reader:
                try:
                    ratings.append(klass.from_csv(row))
                except ValueError:
                    pass
        return ratings

    def lookup_for(klass, profile_id):
        lookup = defaultdict(lambda:[])
        for rating in klass.all_for(profile_id):
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
        self.should_update = True

    @property
    def to_csv(self):
        return [self.profile_id, self.name, self.rating, self.game_count, self.should_update]

    def update(self, klass, rating_klass, data):
        # If should have updated and ratings file not updated since last time users updated, don't change
        rating_file = rating_klass.data_file_template.format(self.profile_id)
        if not os.path.exists(rating_file):
            self.should_update = True
        else:
            should_update = self.game_count != data['games']
            if self.should_update and not should_update:
                self.should_update = os.stat(klass.data_file).st_mtime > os.stat(rating_file).st_mtime
            else:
                self.should_update = should_update
        self.name = data['name']
        self.rating = data['rating']
        self.game_count = data['games']

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
    data_file_template = '{}/data/player_rating_{{}}_{{}}_data.csv'.format(ROOT_DIR)    
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
