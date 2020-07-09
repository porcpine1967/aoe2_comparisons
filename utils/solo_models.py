""" Objects for analyzing data in 1v1 matches."""

import pathlib

import utils.models

leaderboard = 3

DATA_DIR = '{}/data'.format(utils.models.ROOT_DIR)
GRAPH_DIR = '{}/graphs'.format(utils.models.ROOT_DIR)

MAPS = [
    'Acropolis',
    'Alpine Lakes',
    'Arabia',
    'Arena',
    'Black Forest',
    'Bog Islands',
    'Continental',
    'Four Lakes',
    'Gold Rush',
    'Golden Pit',
    'Golden Swamp',
    'Hideout',
    'Hill Fort',
    'Islands',
    'Kilimanjaro',
    'Mediterranean',
    'MegaRandom',
    'Mountain Pass',
    'Nomad',
    'Serengeti',
    'Steppe',
    'Team Islands',
    ]

def acceptable_player_count(cnt):
    cnt == 2

def as_str():
    return 'Ranked 1v1 Matches'

class Player(utils.models.Player):
    def rating_cache_file(data_set_type, mincount):
        return '{}/player_rating_{}_{}_data.csv'.format(DATA_DIR, data_set_type, mincount)
    def cache_player_ratings(data_set_type, mincount=5):
        return utils.models.Player.cache_player_ratings(utils.solo_models, data_set_type, mincount)
    def player_values(matches, include_ratings=()):
        return utils.models.Player.player_values(utils.solo_models, matches, include_ratings)

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
    def data_file(profile_id):
        return '{}/matches_for_{}.csv'.format(DATA_DIR, profile_id)
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
            self.version = data['version']
            self.winner = 0
        except IndexError:
            print(json.dumps(data))
            raise

    @property
    def players(self):
        if self.player_id_1 > self.player_id_2:
            teams = (1, 2,)
        else:
            teams = (2, 1,)
        return { self.player_id_1: { 'civ': self.civ_1, 'rating': self.rating_1, 'team': teams[0] },
                 self.player_id_2: { 'civ': self.civ_2, 'rating': self.rating_2, 'team': teams[1] } }

    @property
    def to_csv(self):
        return [ self.match_id, self.started, self.map_type, self.civ_1, self.rating_1, self.player_id_1,
                 self.civ_2, self.rating_2, self.player_id_2, self.winner, self.version]

    def from_csv(row):
        if len(row) > 10:
            version = row[10]
        else:
            version = None
        match_data = {
            'match_id': row[0],
            'started': int(row[1]),
            'map_type': int(row[2]),
            'players': [
                { 'civ': int(row[3]), 'rating': int(row[4]), 'profile_id': row[5], },
                { 'civ': int(row[6]), 'rating': int(row[7]), 'profile_id': row[8], },
                ],
            'version': version,
            }
        match = Match(match_data)
        match.winner = int(row[9])
        return match

    def to_record(self):
        return super().to_record(Match, Rating)

    def all_for(profile_id):
        return utils.models.Match.all_for(Match, profile_id)
    def all(include_duplicates=False):
        return utils.models.Match.all(utils.solo_models, include_duplicates)

class Rating(utils.models.Rating):
    def data_file(profile_id):
        return '{}/ratings_for_{}.csv'.format(DATA_DIR, profile_id)
    def all_for(profile_id):
        return utils.models.Rating.all_for(Rating, profile_id)
    def lookup_for(profile_id):
        return utils.models.Rating.lookup_for(Rating, profile_id)
class User(utils.models.User):
    def data_file():
        return '{}/users.csv'.format(DATA_DIR)
    def all():
        return utils.models.User.all(User)
    def update(self, data):
        return super().update(User, Rating, data)
    def from_csv(row):
        return utils.models.User.from_csv(User, row)

if __name__ == '__main__':
    for data_set_type in ('test', 'model', 'verification',):
        Player.cache_player_ratings(data_set_type)
