import os
import pathlib

ROOT_DIR = pathlib.Path(__file__).parent.parent.absolute()

import pytest
import requests

import utils.download
import utils.solo_models
import utils.team_models

@pytest.fixture(scope="session", autouse=True)
def set_model_data_file_templates():
    if not '/tests' in utils.solo_models.DATA_DIR:
        utils.solo_models.DATA_DIR = utils.solo_models.DATA_DIR.replace('/data', '/tests/data')
    if not '/tests' in utils.team_models.DATA_DIR:
        utils.team_models.DATA_DIR = utils.team_models.DATA_DIR.replace('/team-data', '/tests/team-data')

def test_fetch_solo_users(requests_mock):
    data = {"total":2,"leaderboard_id":3,"leaderboard":[{"profile_id":199324,"rating":2264,"name":"[aM] Hera","games":1207,},
                                                        {"profile_id":805415,"rating":886,"name":"LittleCaesar","games":53,}]}
    url = 'https://aoe2.net/api/leaderboard?game=aoe2de&leaderboard_id=3&start=1&count=10000'
    requests_mock.get(url, json=data)

    assert len(utils.solo_models.User.all()) == 3

    users = utils.download.users(utils.solo_models, True, False)

    # Make sure ratings file touched since users file
    user_change_time = os.stat(utils.solo_models.User.data_file()).st_mtime
    time_change = (user_change_time + 1, user_change_time + 1,)
    os.utime(utils.solo_models.Rating.data_file('199324'), time_change)

    assert len(users) == 4
    for user in users.values():
        if user.profile_id == 199324:
            assert not user.should_update
        else:
            assert user.should_update

def test_fetch_team_users(requests_mock):
    data = {"total":2,"leaderboard_id":4,"leaderboard":[{"profile_id":199325,"rating":2264,"name":"[aM] Hera","games":1207,},
                                                        {"profile_id":805415,"rating":886,"name":"LittleCaesar","games":53,}]}
    url = 'https://aoe2.net/api/leaderboard?game=aoe2de&leaderboard_id=4&start=1&count=10000'
    requests_mock.get(url, json=data)

    assert len(utils.team_models.User.all()) == 3

    users = utils.download.users(utils.team_models, True, False)

    # Make sure ratings file touched since users file
    user_change_time = os.stat(utils.team_models.User.data_file()).st_mtime
    time_change = (user_change_time + 1, user_change_time + 1,)
    os.utime(utils.team_models.Rating.data_file('199325'), time_change)

    assert len(users) == 4
    for user in users.values():
        if user.profile_id == 199325:
            assert not user.should_update
        else:
            assert user.should_update

def test_profiles_from_files():
    # solo
    assert len(utils.download.profiles_from_files('ratings', utils.solo_models)) == 6
    assert len(utils.download.profiles_from_files('ratings', utils.team_models)) == 5
