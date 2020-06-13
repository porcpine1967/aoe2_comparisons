import pathlib

import utils.models


class Player(utils.models.Player):
    pass

class MatchReport(utils.models.MatchReport):
    data_file_template = '{}/data/match_{{}}_data.csv'.format(utils.models.ROOT_DIR)
    def all(data_set_type):
        return utils.models.MatchReport.all(MatchReport, data_set_type)
    def by_rating(data_set_type, lower, upper):
        return utils.models.MatchReport.by_rating(MatchReport, data_set_type, lower, upper)
    def by_map(data_set_type, map_type):
        return utils.models.MatchReport.by_map(MatchReport, data_set_type, map_type)
    def by_map_and_rating(data_set_type, map_type, lower, upper):
        return utils.models.MatchReport.by_map_and_rating(MatchReport, data_set_type, map_type, lower, upper)

class Match(utils.models.Match):
    data_file_template = '{}/data/matches_for_{{}}.csv'.format(utils.models.ROOT_DIR)
    def all_for(profile_id):
        return utils.models.Match.all_for(Match, profile_id)
    def all(include_duplicates=False):
        return utils.models.Match.all(Match, include_duplicates)
    def from_csv(row):
        return utils.models.Match.from_csv(Match, row)

    def to_record(self):
        return super().to_record(Match, Rating)

    @property
    def players(self):
        if self.player_id_1 > self.player_id_2:
            teams = (1, 2,)
        else:
            teams = (2, 1,)
        return { self.player_id_1: { 'civ': self.civ_1, 'rating': self.rating_1, 'team': teams[0] },
                 self.player_id_2: { 'civ': self.civ_2, 'rating': self.rating_2, 'team': teams[1] } } 


class Rating(utils.models.Rating):
    data_dir = '{}/data'.format(utils.models.ROOT_DIR)
    data_file_template = '{}/data/ratings_for_{{}}.csv'.format(utils.models.ROOT_DIR)
    def all_for(profile_id):
        return utils.models.Rating.all_for(Rating, profile_id)
    def lookup_for(profile_id):
        return utils.models.Rating.lookup_for(Rating, profile_id)
class User(utils.models.User):
    def update(self, data):
        return super().update(User, Rating, data)
    def from_csv(row):
        u = User({'profile_id': int(row[0]), 'name': row[1], 'rating': int(row[2]), 'games': int(row[3])})
        if len(row) > 4:
            u.should_update = row[4] == 'True'
        return u

class PlayerRating(utils.models.PlayerRating):
    pass

class CachedPlayer(utils.models.CachedPlayer):
    pass

if __name__ == '__main__':
    for data_set_type in ('test', 'model', 'verification',):
        PlayerRating.ratings_for(data_set_type, update=True)
