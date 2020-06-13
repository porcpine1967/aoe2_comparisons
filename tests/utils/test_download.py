import os
import pathlib

ROOT_DIR = pathlib.Path(__file__).parent.parent.absolute()

import pytest
import requests

import utils.download
import utils.team_models

@pytest.fixture(scope="session", autouse=True)
def set_model_data_file_templates():
    if not '/tests' in utils.team_models.Rating.data_file_template:
        utils.team_models.Rating.data_file_template = utils.team_models.Rating.data_file_template.replace('/team-data', '/tests/team-data')
    if not '/tests' in utils.team_models.Rating.data_dir:
        utils.team_models.Rating.data_dir = utils.team_models.Rating.data_dir.replace('/team-data', '/tests/team-data')
    if not '/tests' in utils.team_models.User.data_file:
        utils.team_models.User.data_file = utils.team_models.User.data_file.replace('/team-data', '/tests/team-data')

def test_fetch_users(requests_mock):
    data = {"total":2,"leaderboard_id":3,"leaderboard":[{"profile_id":199325,"rating":2264,"name":"[aM] Hera","games":1207,},
                                                        {"profile_id":805415,"rating":886,"name":"LittleCaesar","games":53,}]}
    url = 'https://aoe2.net/api/leaderboard?game=aoe2de&leaderboard_id=4&start=1&count=10000'
    requests_mock.get(url, json=data)

    assert len(utils.team_models.User.all()) == 3

    users = utils.download.users(True, False)

    # Make sure ratings file touched since users file
    user_change_time = os.stat(utils.team_models.User.data_file).st_mtime
    time_change = (user_change_time + 1, user_change_time + 1,)
    os.utime(utils.team_models.Rating.data_file_template.format('199325'), time_change)

    assert len(users) == 4
    for user in users.values():
        if user.profile_id == 199325:
            assert not user.should_update
        else:
            assert user.should_update

def test_profiles_from_files():
    assert len(utils.download.profiles_from_files('ratings')) == 4
