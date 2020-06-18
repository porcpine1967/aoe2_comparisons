""" Objects for analyzing data in team matches."""

import pathlib

import utils.models

leaderboard = 4

DATA_DIR = '{}/team-data'.format(utils.models.ROOT_DIR)
GRAPH_DIR = '{}/team-graphs'.format(utils.models.ROOT_DIR)

MAPS = [
    'Arabia',
    'Arena',
    'MegaRandom',
    'Nomad',
    'Hideout',
    'Lombardia',
    'Black Forest',
    'Scandinavia',
    'Golden Swamp',
    'Hill Fort',
    'Oasis',
    'Gold Rush',
    'Steppe',
    'Team Islands',
    'Golden Pit',
    'Mediterranean',
    'Wolf Hill',
]

class Player(utils.models.Player):
    def rating_cache_file(data_set_type, mincount):
        return '{}/player_rating_{}_{}_data.csv'.format(DATA_DIR, data_set_type, mincount)
    def cache_player_ratings(data_set_type, mincount=5):
        return utils.models.Player.cache_player_ratings(utils.team_models, data_set_type, mincount)
    def player_values(matches, include_ratings=()):
        return utils.models.Player.player_values(utils.team_models, matches, include_ratings)

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
