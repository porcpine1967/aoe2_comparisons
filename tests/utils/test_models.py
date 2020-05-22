import pytest
import utils.models

def test_match_to_from_csv():
    match_row = [ '15483707', '1586536235', '20', '34', '659', '1406544', '24', '818', '1310102', '2', ]
    match = utils.models.Match.from_csv(match_row)
    assert match_row == [str(x) for x in match.to_csv]

def test_rating_to_from_csv():
    rating_row = [ '1310102','827','818','10','12','0','1586537788','won', ]
    rating = utils.models.Rating.from_csv(rating_row)
    assert rating_row == [str(x) for x in rating.to_csv]

def test_user_to_from_csv():
    user_row = [ '196240','TheViper','2318','399', ]
    user = utils.models.User.from_csv(user_row)
    assert user_row == [str(x) for x in user.to_csv]

