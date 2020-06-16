from collections import Counter
import os
import pathlib

ROOT_DIR = pathlib.Path(__file__).parent.parent.absolute()

import pytest

import utils.solo_models

@pytest.fixture(scope="session", autouse=True)
def set_model_data_file_templates():
    if not '/tests' in utils.solo_models.DATA_DIR:
        utils.solo_models.DATA_DIR = utils.solo_models.DATA_DIR.replace('/data', '/tests/data')

# Match
def test_match_to_from_csv():
    match_row = [ '15483707', '1586536235', '20', '34', '659', '1406544', '24', '818', '1310102', '0', '8276',]
    match = utils.solo_models.Match.from_csv(match_row)
    print(match.to_csv)
    assert match_row == [str(x) for x in match.to_csv]

def test_rating_for():
    # Match Id,Started,Map,Civ 1,RATING 1,Player 1,Civ 2,RATING 2,Player 2,Winner
    match_row = [ '15483707', '1586536235', '20', '34', '659', '1406544', '24', '818', '1310102', '0', ]
    match = utils.solo_models.Match.from_csv(match_row)
    assert match.rating_1 == match.rating_for(match.player_id_1)
    assert match.rating_2 == match.rating_for(match.player_id_2)

def test_match_all_for():
    assert len(utils.solo_models.Match.all_for('1301032')) == 2

def test_match_all():
    assert len(utils.solo_models.Match.all()) == 3
    assert len(utils.solo_models.Match.all(True)) == 4

def test_determine_winner():
    match_row = [ '9409809','1582654374','33','30','1132','242765','5','1158','1301032','0', ]
    match = utils.solo_models.Match.from_csv(match_row)
    assert 2 == match.determine_winner(utils.solo_models.Match, utils.solo_models.Rating)

def test_to_record():
    expected = [1582654374, 33, '5:30', '1158:1132', '1301032:242765', '2:1', 2, '0']
    # Same as test determine winner
    match_row = [ '9409809','1582654374','33','30','1132','242765','5','1158','1301032', '0', '0' ]
    match = utils.solo_models.Match.from_csv(match_row)
    assert expected == match.to_record()
    # With players reversed
    match_row = [ '9409809','1582654374','33','5','1158','1301032','30','1132','242765', '0', '0']
    match = utils.solo_models.Match.from_csv(match_row)
    assert expected == match.to_record()
    # With no winner (ratings changed so winner can't be found)
    expected = [1582654374, 33, '5:30', '115:113', '1301032:242765', '2:1', 0, '0']
    match_row = [ '9409809','1582654374','33','30','113','242765','5','115','1301032','0', '0']
    match = utils.solo_models.Match.from_csv(match_row)
    assert expected == match.to_record()

# Rating
def test_rating_to_from_csv():
    # Profile Id,Rating,Wins,Losses,Drops,Timestamp
    rating_row = [ '1310102','827','818','10','12','0','1586537788','won', ]
    rating = utils.solo_models.Rating.from_csv(rating_row)
    assert rating_row == [str(x) for x in rating.to_csv]

def test_rating_all_for():
    assert len(utils.solo_models.Rating.all_for('1301032')) == 2

def test_rating_lookup():
    assert utils.solo_models.Rating.lookup_for('1301032').keys() == set([1158, 1172,])

# User
def test_user_to_from_csv():
    user_row = [ '196240','TheViper','2318','399', 'False', ]
    user = utils.solo_models.User.from_csv(user_row)
    assert user_row == [str(x) for x in user.to_csv]

def test_user_should_update():
    profile_id = '196240'
    user_change_time = os.stat(utils.solo_models.User.data_file()).st_mtime
    time_change = (user_change_time + 1, user_change_time + 1,)
    ratings_file = utils.solo_models.Rating.data_file(profile_id)
    # Make sure ratings file updated since users file
    os.utime(ratings_file, time_change)
    user_row = [ profile_id, 'TheViper', '2318', '399', ]
    user = utils.solo_models.User.from_csv(user_row)
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
    user = utils.solo_models.User.from_csv(user_row)
    user_data = { 'name': user_row[1], 'rating': int(user_row[2]), 'games': int(user_row[3]), }
    user.update(user_data)
    assert user.should_update

# MatchReport
def test_match_report_to_from_csv():
    # started, map_code, civs, ratings, player ids, teams, winner, version
    row = ['1582654374', '33', '5:30', '1258:1100', '1301032:242765', '2:1', '2', '0', ]
    match = utils.solo_models.MatchReport(row)
    assert match.timestamp == int(row[0])
    assert match.map == 'Nomad'
    assert match.winner == 2
    assert match.version == '0'
    assert match.players['1301032'] == { 'civ': 'Byzantines', 'rating': 1258, 'team': 2 }
    assert match.players['242765'] == { 'civ': 'Tatars', 'rating': 1100, 'team': 1 }

def test_all():
    assert 11 == len(utils.solo_models.MatchReport.all('for_test'))

def test_info_for():
    mr = utils.solo_models.MatchReport(['1588091226', '9', '12:16', '1040:1014', '994498:1979688', '1:2', '1', '0'])
    civ, rating, won_state = mr.info_for('994498')
    # player 1
    assert civ == 'Huns'
    assert rating == 1040
    assert won_state == 'won'
    # player 2
    civ, rating, won_state = mr.info_for('1979688')
    assert civ == 'Japanese'
    assert rating == 1014
    assert won_state == 'lost'
    # invalid player
    civ, rating, won_state = mr.info_for('invalid id')
    assert civ == None
    assert rating == None
    assert won_state == None
    mr = utils.solo_models.MatchReport(['1588091226', '9', '12:16', '1040:1014', '994498:1979688', '1:2', '0', '0'])
    # test no clear winner
    civ, rating, won_state = mr.info_for('994498')
    assert won_state == 'na'

# Player
def test_add_civ_percentages():
    player = utils.solo_models.Player('foo')
    player.matches.append(utils.solo_models.MatchReport(['1588091226', '9', '11:16', '10:1014', 'foo:1979688', '1:2', '0', '0']))
    player.matches.append(utils.solo_models.MatchReport(['1588091226', '9', '12:17', '100:1014', 'foo:1979688', '1:2', '0', '0']))
    player.matches.append(utils.solo_models.MatchReport(['1588091226', '22', '13:16', '1000:1014', 'foo:1979688', '1:2', '0', '0']))
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

def test_add_map_percentages():
    player = utils.solo_models.Player('foo')
    # Started, map_code, civs, ratings, player ids, teams, winner, version
    player.matches.append(utils.solo_models.MatchReport(['1588091226', '9', '11:16', '10:1014', 'foo:1979688', '1:2', '0', '0']))
    player.matches.append(utils.solo_models.MatchReport(['1588091226', '9', '12:17', '100:1014', 'foo:1979688', '1:2', '0', '0']))
    player.matches.append(utils.solo_models.MatchReport(['1588091226', '22', '13:16', '1000:1014', 'foo:1979688', '1:2', '0', '0']))
    # One map one play
    ctr = Counter()
    has_result = player.add_map_percentages(ctr, 0, 20)
    assert has_result
    assert len(ctr) == 1
    assert ctr['Arabia'] == 1
    # One map two plays
    ctr = Counter()
    has_result = player.add_map_percentages(ctr, 0, 200)
    assert has_result
    assert len(ctr) == 1
    assert ctr['Arabia'] == 1
    # Two maps
    ctr = Counter()
    has_result = player.add_map_percentages(ctr, 0, 2000)
    assert has_result
    assert len(ctr) == 2
    assert ctr['Arabia'] == 2/3.0
    assert ctr['Rivers'] == 1/3.0
    # No Result does not update
    has_result = player.add_map_percentages(ctr, 0, 1)
    assert not has_result
    assert len(ctr) == 2
    assert ctr['Arabia'] == 2/3.0
    assert ctr['Rivers'] == 1/3.0
