from collections import Counter
import csv
import os
import pathlib

import pytest

import utils.team_models

@pytest.fixture(scope="session", autouse=True)
def set_model_data_file_templates():
    if not '/tests' in utils.team_models.DATA_DIR:
        utils.team_models.DATA_DIR = utils.team_models.DATA_DIR.replace('/team-data', '/tests/team-data')

# Match
def test_match_from_data():
    data = { 'match_id': 1, 'started': 1591996736, 'map_type': 74, 'version': '37906',
             'players': [ { 'civ': 17, 'profile_id': 1784541, 'rating': 2745, 'team': 1},
                          { 'civ': 33, 'profile_id': 230432, 'rating': 2593, 'team': 2}, ] }
    m = utils.team_models.Match(data)

def test_match_to_from_csv():
    # Match Id,Started,Map,Civs,Ratings,Player Ids,Teams,Version
    match_row = [ '15483707', '1586536235', '20', '34:24', '659:818', '1310102:1406544', '1:2', '8276',]
    match = utils.team_models.Match.from_csv(match_row)
    assert match_row == [str(x) for x in match.to_csv]

def test_rating_for():
    match_row = [ '15483707', '1586536235', '20', '34:24', '659:818', '1310102:1406544', '1:2', '8276',]
    match = utils.team_models.Match.from_csv(match_row)
    assert 659 == match.rating_for('1310102')
    assert 818 == match.rating_for('1406544')

def test_match_all_for():
    assert len(utils.team_models.Match.all_for('1301032')) == 2

def test_match_all():
    assert len(utils.team_models.Match.all()) == 40
    assert len(utils.team_models.Match.all(True)) == 41

def test_determine_winner():
    match_row = [ '9409809','1582654374','33','30:5','1132:1158','242765:1301032', '1:2', '0', ]
    match = utils.team_models.Match.from_csv(match_row)
    assert 2 == match.determine_winner(utils.team_models.Match, utils.team_models.Rating)

def test_to_record():
    expected = [1582654374, 33, '5:30', '1158:1132', '1301032:242765', '2:1', 2, '0', ]
    # Same as test determine winner
    match_row = [ '9409809','1582654374','33','5:30','1158:1132','1301032:242765', '2:1', '0', ]
    match = utils.team_models.Match.from_csv(match_row)
    assert expected == match.to_record()
    # With players reversed
    match_row = [ '9409809','1582654374','33','30:5','1132:1158','242765:1301032', '1:2', '0', ]
    match = utils.team_models.Match.from_csv(match_row)
    assert expected == match.to_record()
    # With no winner (ratings changed so winner can't be found)
    expected = [1582654374, 33, '5:30', '1258:1100', '1301032:242765', '2:1', 0, '0', ]
    match_row = [ '9409809','1582654374','33','5:30','1258:1100','1301032:242765', '2:1', '0', ]
    match = utils.team_models.Match.from_csv(match_row)
    assert expected == match.to_record()

# Rating
def test_rating_to_from_csv():
    # Profile Id,Rating,Wins,Losses,Drops,Timestamp
    rating_row = [ '1310102','827','818','10','12','0','1586537788','won', ]
    rating = utils.team_models.Rating.from_csv(rating_row)
    assert rating_row == [str(x) for x in rating.to_csv]

def test_rating_all_for():
    assert len(utils.team_models.Rating.all_for('1301032')) == 2

def test_rating_lookup():
    assert utils.team_models.Rating.lookup_for('1301032').keys() == set([1158, 1172,])

# User
def test_user_to_from_csv():
    user_row = [ '196240','TheViper','2318','399', 'False', ]
    user = utils.team_models.User.from_csv(user_row)
    assert user_row == [str(x) for x in user.to_csv]

def test_user_should_update():
    profile_id = '196240'
    user_change_time = os.stat(utils.team_models.User.data_file()).st_mtime
    time_change = (user_change_time + 1, user_change_time + 1,)
    ratings_file = utils.team_models.Rating.data_file(profile_id)
    # Make sure ratings file updated since users file
    os.utime(ratings_file, time_change)
    user_row = [ profile_id, 'TheViper', '2318', '399', ]
    user = utils.team_models.User.from_csv(user_row)
    # Default user should update
    assert user.should_update
    # No data change so should not update
    user_data = { 'name': user_row[1], 'rating': int(user_row[2]), 'games': int(user_row[3]), }
    user.update(user_data)
    assert not user.should_update
    # Data changed so should update
    user_data['games'] += 1
    user.update(user_data)
    assert user.should_update

    # Data not updated, but ratings file users file younger than ratings file, so should update
    os.utime(ratings_file, tuple([t - 2 for t in time_change]))
    user.update(user_data)
    assert user.should_update

def test_user_should_update_no_file():
    user_row = [ 0, 'TheViper', '2318', '399', ]
    user = utils.team_models.User.from_csv(user_row)
    user_data = { 'name': user_row[1], 'rating': int(user_row[2]), 'games': int(user_row[3]), }
    user.update(user_data)
    assert user.should_update

# MatchReport
def test_match_report_to_from_csv():
    # started, map_code, civs, ratings, player ids, teams, winner, version
    row = ['1582654374', '33', '5:30', '1258:1100', '1301032:242765', '2:1', '2', '0', ]
    match = utils.team_models.MatchReport(row)
    assert match.timestamp == int(row[0])
    assert match.map == 'Nomad'
    assert match.winner == 2
    assert match.version == '0'
    assert match.players['1301032'] == { 'civ': 'Byzantines', 'rating': 1258, 'team': 2 }
    assert match.players['242765'] == { 'civ': 'Tatars', 'rating': 1100, 'team': 1 }

def test_all():
    assert 10 == len(utils.team_models.MatchReport.all('for_test'))

def test_match_type():
    row = ['1582654374', '33', '5:30', '1258:1100', '1301032:242765', '2:1', '2', '0', ]
    mr = utils.team_models.MatchReport(row)
    assert mr.match_type == '1v1'
    row = ['1582141235', '33', '16:13:20:18', '1563:1605:1609:1624', '1547211:216695:261325:261818', '1:1:2:2', '2', '']
    mr = utils.team_models.MatchReport(row)
    assert mr.match_type == '2v2'
    row = ['1582141235', '33', '16:13:20', '1563:1605:1609', '1547211:216695:261325', '1:1:2', '2', '']
    mr = utils.team_models.MatchReport(row)
    assert mr.match_type == '1v2'
    row = ['1586874994', '72', '17:11:24:2:5:23', '1591:1500:1445:1487:1425:1648', '1540393:1684941:1691937:1720359:1954867:254209', '2:1:1:1:2:2', '2', '36202']
    mr = utils.team_models.MatchReport(row)
    assert mr.match_type == '3v3'

def test_info_for():
    row = ['1582654374', '33', '5:30', '1258:1100', '1301032:242765', '2:1', '2', '0', ]
    mr = utils.team_models.MatchReport(row)
    civ, rating, won_state = mr.info_for('1301032')
    # player 1
    assert civ == 'Byzantines'
    assert rating == 1258
    assert won_state == 'won'
    # player 2
    civ, rating, won_state = mr.info_for('242765')
    assert civ == 'Tatars'
    assert rating == 1100
    assert won_state == 'lost'
    # invalid player
    civ, rating, won_state = mr.info_for('invalid id')
    assert civ == None
    assert rating == None
    assert won_state == None

# Player
def test_add_civ_percentages():
    player = utils.team_models.Player('foo')
    player.matches.append(utils.team_models.MatchReport(['1588091226', '9', '11:16', '10:1014', 'foo:1979688', '1:2', '0', '0']))
    player.matches.append(utils.team_models.MatchReport(['1588091226', '9', '12:17', '100:1014', 'foo:1979688', '1:2', '0', '0']))
    player.matches.append(utils.team_models.MatchReport(['1588091226', '22', '13:16', '1000:1014', 'foo:1979688', '1:2', '0', '0']))
    # One civ
    ctr = Counter()
    has_result = player.add_civ_percentages(ctr, 'Arabia', 0, 20)
    assert has_result
    assert len(ctr) == 1
    assert ctr['Goths'] == 1
    # Two civs
    ctr = Counter()
    has_result = player.add_civ_percentages(ctr, 'Arabia', 0, 2000)
    assert has_result
    assert len(ctr) == 2
    assert ctr['Goths'] == .5
    assert ctr['Huns'] == .5
    # Different map
    ctr = Counter()
    has_result = player.add_civ_percentages(ctr, 'Rivers', 0, 2000)
    assert has_result
    assert len(ctr) == 1
    assert ctr['Incas'] == 1
    # All
    ctr = Counter()
    has_result = player.add_civ_percentages(ctr, 'all', 0, 2000)
    assert has_result
    assert len(ctr) == 3
    assert ctr['Goths'] == 1/3.0
    assert ctr['Huns'] == 1/3.0
    assert ctr['Incas'] == 1/3.0
    # No Result does not update
    has_result = player.add_civ_percentages(ctr, 'No such map', 0, 2000)
    assert not has_result
    assert len(ctr) == 3
    assert ctr['Goths'] == 1/3.0
    assert ctr['Huns'] == 1/3.0
    assert ctr['Incas'] == 1/3.0

def test_best_rating():
    player = utils.team_models.Player('bar')
    # Started, map_code, civs, ratings, player ids, teams, winner, version
    player.matches.append(utils.team_models.MatchReport(['1588091225', '9', '11:16', '10:103', 'foo:bar', '1:2', '0', '0']))
    player.matches.append(utils.team_models.MatchReport(['1588091226', '9', '11:16', '10:104', 'foo:bar', '1:2', '0', '0']))
    player.matches.append(utils.team_models.MatchReport(['1588091227', '9', '12:17', '100:105', 'foo:bar', '1:2', '0', '0']))
    player.matches.append(utils.team_models.MatchReport(['1588091228', '22', '13:16', '1000:1015', 'foo:bar', '1:2', '0', '0']))
    player.matches.append(utils.team_models.MatchReport(['1588091229', '22', '13:16', '1000:1016', 'foo:bar', '1:2', '0', '0']))
    player.matches.append(utils.team_models.MatchReport(['1588091230', '22', '13:16', '1000:1017', 'foo:bar', '1:2', '0', '0']))
    # Do not calculate if number of matches less than 1.5 * minimum count
    assert len(player.ratings) == 6
    assert player.best_rating(5) == None
    # Make sure if given the choice the highest choice is given
    assert player.best_rating(3) == 1016
    # Make sure result is cached
    player.matches = []
    assert player.best_rating(3) == 1016
    assert player.best_rating(2) == None

def test_cache_best_rating():
    data_set_type = 'test_cache_best_rating'
    mincount = 3
    # remove cache file
    if os.path.exists(utils.team_models.Player.rating_cache_file(data_set_type, mincount)):
        os.remove(utils.team_models.Player.rating_cache_file(data_set_type, mincount))
    # Set up match report data
    match_reports = []
    match_reports.append(['1588091225', '9', '11:16', '10:103', 'foo:bar', '1:2', '0', '0'])
    match_reports.append(['1588091226', '9', '11:16', '10:104', 'foo:bar', '1:2', '0', '0'])
    match_reports.append(['1588091227', '9', '12:17', '100:105', 'foo:bar', '1:2', '0', '0'])
    match_reports.append(['1588091228', '22', '13:16', '1000:1015', 'foo:bar', '1:2', '0', '0'])
    match_reports.append(['1588091229', '22', '13:16', '1000:1016', 'foo:bar', '1:2', '0', '0'])
    match_reports.append(['1588091230', '22', '13:16', '1000:1017', 'foo:bar', '1:2', '0', '0'])
    with open(utils.team_models.MatchReport.data_file(data_set_type), 'w') as f:
        csv.writer(f).writerows(match_reports)

    # Verify setup
    matches = utils.team_models.MatchReport.all(data_set_type)
    assert len(matches) == 6
    players = utils.team_models.Player.player_values(matches, ((data_set_type, mincount,),))
    assert len(players) == 2
    for player in players:
        assert len(player.matches) == 6
        assert not player._best_ratings

    utils.team_models.Player.cache_player_ratings(data_set_type, mincount)
    players = utils.team_models.Player.player_values(matches, ((data_set_type, mincount,),))
    for player in players:
        assert len(player.matches) == 6
        if player.player_id == 'foo':
            assert not player.best_rating(mincount)
        elif player.player_id == 'bar':
            player.matches = []
            assert player.best_rating(mincount) == 1016
