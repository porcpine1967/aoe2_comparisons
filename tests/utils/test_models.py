import pathlib

ROOT_DIR = pathlib.Path(__file__).parent.parent.absolute()

import pytest

import utils.models

@pytest.fixture(scope="session", autouse=True)
def set_model_data_file_templates():
    if not '/tests' in utils.models.Match.data_file_template:
        utils.models.Match.data_file_template = utils.models.Match.data_file_template.replace('/data', '/tests/data')
    if not '/tests' in utils.models.Rating.data_file_template:
        utils.models.Rating.data_file_template = utils.models.Rating.data_file_template.replace('/data', '/tests/data')
    if not '/tests' in utils.models.MatchReport.data_file_template:
        utils.models.MatchReport.data_file_template = utils.models.MatchReport.data_file_template.replace('/data', '/tests/data')
    if not '/tests' in utils.models.User.data_file:
        utils.models.User.data_file = utils.models.User.data_file.replace('/data', '/tests/data')

# Match
def test_match_to_from_csv():
    match_row = [ '15483707', '1586536235', '20', '34', '659', '1406544', '24', '818', '1310102', '0', '8276',]
    match = utils.models.Match.from_csv(match_row)
    assert match_row == [str(x) for x in match.to_csv]

def test_rating_for():
    # Match Id,Started,Map,Civ 1,RATING 1,Player 1,Civ 2,RATING 2,Player 2,Winner
    match_row = [ '15483707', '1586536235', '20', '34', '659', '1406544', '24', '818', '1310102', '0', ]
    match = utils.models.Match.from_csv(match_row)
    assert match.rating_1 == match.rating_for(match.player_id_1)
    assert match.rating_2 == match.rating_for(match.player_id_2)

def test_mark_lost():
    # Match Id,Started,Map,Civ 1,RATING 1,Player 1,Civ 2,RATING 2,Player 2,Winner
    match_row = [ '15483707', '1586536235', '20', '34', '659', '1406544', '24', '818', '1310102', '0', ]
    match = utils.models.Match.from_csv(match_row)
    match.mark_lost(match.player_id_1)
    assert match.winner == 2
    match.mark_lost(match.player_id_2)
    assert match.winner == 1
    match.mark_lost('foo')
    assert match.winner == 0

def test_mark_won():
    # Match Id,Started,Map,Civ 1,RATING 1,Player 1,Civ 2,RATING 2,Player 2,Winner
    match_row = [ '15483707', '1586536235', '20', '34', '659', '1406544', '24', '818', '1310102', '0', ]
    match = utils.models.Match.from_csv(match_row)
    match.mark_won(match.player_id_1)
    assert match.winner == 1
    match.mark_won(match.player_id_2)
    assert match.winner == 2
    match.mark_won('foo')
    assert match.winner == 0

def test_winner_id():
    # Match Id,Started,Map,Civ 1,RATING 1,Player 1,Civ 2,RATING 2,Player 2,Winner
    match_row = [ '15483707', '1586536235', '20', '34', '659', '1406544', '24', '818', '1310102', '0', ]
    match = utils.models.Match.from_csv(match_row)
    assert match.winner_id == None
    match.winner = 2
    assert match.winner_id == match.player_id_2
    match.winner = 1
    assert match.winner_id == match.player_id_1

def test_rating_diff():
    # Match Id,Started,Map,Civ 1,RATING 1,Player 1,Civ 2,RATING 2,Player 2,Winner
    match_row = [ '15483707', '1586536235', '20', '34', '659', '1406544', '24', '818', '1310102', '0', ]
    match = utils.models.Match.from_csv(match_row)
    assert match.rating_diff == None
    match.winner = 1
    assert match.rating_diff == match.rating_1 - match.rating_2
    match.winner = 2
    assert match.rating_diff == match.rating_2 - match.rating_1

def test_match_all_for():
    assert len(utils.models.Match.all_for('1301032')) == 2

def test_match_all():
    assert len(utils.models.Match.all()) == 3
    assert len(utils.models.Match.all(True)) == 4

def test_determine_winner():
    match_row = [ '9409809','1582654374','33','30','1132','242765','5','1158','1301032','0', ]
    match = utils.models.Match.from_csv(match_row)
    assert 2 == match.determine_winner()

def test_to_record():
    expected = ['5-30-33', 1158, 1132, 26, 1, '1301032', '242765', 1582654374]
    # Same as test determine winner
    match_row = [ '9409809','1582654374','33','30','1132','242765','5','1158','1301032','0', ]
    match = utils.models.Match.from_csv(match_row)
    assert expected == match.to_record()
    # With players reversed
    match_row = [ '9409809','1582654374','33','5','1158','1301032','30','1132','242765','0', ]
    match = utils.models.Match.from_csv(match_row)
    assert expected == match.to_record()
    # With no winner (ratings changed so winner can't be found)
    expected = ['5-30-33', 115, 113, 0, 0, '1301032', '242765', 1582654374]
    match_row = [ '9409809','1582654374','33','30','113','242765','5','115','1301032','0', ]
    match = utils.models.Match.from_csv(match_row)
    assert expected == match.to_record()

# Rating
def test_rating_to_from_csv():
    # Profile Id,Rating,Wins,Losses,Drops,Timestamp
    rating_row = [ '1310102','827','818','10','12','0','1586537788','won', ]
    rating = utils.models.Rating.from_csv(rating_row)
    assert rating_row == [str(x) for x in rating.to_csv]

def test_rating_all_for():
    assert len(utils.models.Rating.all_for('1301032')) == 2

def test_rating_lookup():
    assert utils.models.Rating.lookup_for('1301032').keys() == set([1158, 1172,])

# User
def test_user_to_from_csv():
    user_row = [ '196240','TheViper','2318','399', 'False', ]
    user = utils.models.User.from_csv(user_row)
    assert user_row == [str(x) for x in user.to_csv]

def test_user_should_update():
    user_row = [ '196240','TheViper','2318','399', ]
    user_data = { 'name': 'TheViper', 'rating': 2318, 'games': 399, }
    user = utils.models.User.from_csv(user_row)
    assert user.should_update
    user.update(user_data)
    assert not user.should_update
    user_data['games'] += 1
    user.update(user_data)
    assert user.should_update

# MatchReport
def test_all():
    utils.models.MatchReport.all('test')
