from collections import Counter
import os
import pathlib

ROOT_DIR = pathlib.Path(__file__).parent.parent.absolute()

import pytest

import utils.team_models

@pytest.fixture(scope="session", autouse=True)
def set_model_data_file_templates():
    if not '/tests' in utils.team_models.Match.data_file_template:
        utils.team_models.Match.data_file_template = utils.team_models.Match.data_file_template.replace('/team-data', '/tests/team-data')
    if not '/tests' in utils.team_models.Rating.data_file_template:
        utils.team_models.Rating.data_file_template = utils.team_models.Rating.data_file_template.replace('/team-data', '/tests/team-data')
    if not '/tests' in utils.team_models.MatchReport.data_file_template:
        utils.team_models.MatchReport.data_file_template = utils.team_models.MatchReport.data_file_template.replace('/team-data', '/tests/team-data')
    if not '/tests' in utils.team_models.User.data_file:
        utils.team_models.User.data_file = utils.team_models.User.data_file.replace('/team-data', '/tests/team-data')

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
    assert len(utils.team_models.Match.all()) == 3
    assert len(utils.team_models.Match.all(True)) == 4

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
    user_change_time = os.stat(utils.team_models.User.data_file).st_mtime
    time_change = (user_change_time + 1, user_change_time + 1,)
    ratings_file = utils.team_models.Rating.data_file_template.format(profile_id)
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
    print(utils.team_models.MatchReport.data_file_template.format('test'))
    assert 11 == len(utils.team_models.MatchReport.all('test'))

def test_match_type():
    row = ['1582654374', '33', '5:30', '1258:1100', '1301032:242765', '2:1', '2', '0', ]
    mr = utils.team_models.MatchReport(row)
    assert mr.match_type == '1v1'
    row = ['1582141235', '33', '16:13:20:18', '1563:1605:1609:1624', '1547211:216695:261325:261818', '1:1:2:2', '2', '']
    mr = utils.team_models.MatchReport(row)
    assert mr.match_type == '2v2'
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

# # Player
# def test_add_civ_percentages():
#     player = utils.team_models.Player('foo')
#     player.matches.append(utils.team_models.MatchReport(['11-16-9', '10', '1014', '26', '0', 'foo', '1979688', '1588091226']))
#     player.matches.append(utils.team_models.MatchReport(['12-17-9', '100', '1014', '26', '0', 'foo', '1979688', '1588091226']))
#     player.matches.append(utils.team_models.MatchReport(['13-16-22', '1000', '1014', '26', '0', 'foo', '1979688', '1588091226']))
#     # One civ
#     ctr = Counter()
#     has_result = player.add_civ_percentages(ctr, 'Arabia', 0, 20)
#     assert has_result
#     assert len(ctr) == 1
#     assert ctr['Goths'] == 1
#     # Two civs
#     ctr = Counter()
#     has_result = player.add_civ_percentages(ctr, 'Arabia', 0, 2000)
#     assert has_result
#     assert len(ctr) == 2
#     assert ctr['Goths'] == .5
#     assert ctr['Huns'] == .5
#     # Different map
#     ctr = Counter()
#     has_result = player.add_civ_percentages(ctr, 'Rivers', 0, 2000)
#     assert has_result
#     assert len(ctr) == 1
#     assert ctr['Incas'] == 1
#     # All
#     ctr = Counter()
#     has_result = player.add_civ_percentages(ctr, 'all', 0, 2000)
#     assert has_result
#     assert len(ctr) == 3
#     assert ctr['Goths'] == 1/3.0
#     assert ctr['Huns'] == 1/3.0
#     assert ctr['Incas'] == 1/3.0
#     # No Result does not update
#     has_result = player.add_civ_percentages(ctr, 'No such map', 0, 2000)
#     assert not has_result
#     assert len(ctr) == 3
#     assert ctr['Goths'] == 1/3.0
#     assert ctr['Huns'] == 1/3.0
#     assert ctr['Incas'] == 1/3.0

# def test_add_map_percentages():
#     player = utils.team_models.Player('foo')
#     player.matches.append(utils.team_models.MatchReport(['11-16-9', '10', '1014', '26', '0', 'foo', '1979688', '1588091226']))
#     player.matches.append(utils.team_models.MatchReport(['12-17-9', '100', '1014', '26', '0', 'foo', '1979688', '1588091226']))
#     player.matches.append(utils.team_models.MatchReport(['13-16-22', '1000', '1014', '26', '0', 'foo', '1979688', '1588091226']))
#     # One map one play
#     ctr = Counter()
#     has_result = player.add_map_percentages(ctr, 0, 20)
#     assert has_result
#     assert len(ctr) == 1
#     assert ctr['Arabia'] == 1
#     # One map two plays
#     ctr = Counter()
#     has_result = player.add_map_percentages(ctr, 0, 200)
#     assert has_result
#     assert len(ctr) == 1
#     assert ctr['Arabia'] == 1
#     # Two maps
#     ctr = Counter()
#     has_result = player.add_map_percentages(ctr, 0, 2000)
#     assert has_result
#     assert len(ctr) == 2
#     assert ctr['Arabia'] == 2/3.0
#     assert ctr['Rivers'] == 1/3.0
#     # No Result does not update
#     has_result = player.add_map_percentages(ctr, 0, 1)
#     assert not has_result
#     assert len(ctr) == 2
#     assert ctr['Arabia'] == 2/3.0
#     assert ctr['Rivers'] == 1/3.0
