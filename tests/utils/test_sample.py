import os

import pytest

import utils.solo_models
import utils.team_models
import utils.sample

@pytest.fixture(scope="session", autouse=True)
def set_model_data_file_templates():
    if not '/tests' in utils.solo_models.DATA_DIR:
        utils.solo_models.DATA_DIR = utils.solo_models.DATA_DIR.replace('/data', '/tests/data')
    if not '/tests' in utils.team_models.DATA_DIR:
        utils.team_models.DATA_DIR = utils.team_models.DATA_DIR.replace('/team-data', '/tests/team-data')
    # Make sure all the files exist to hit with stat
    for module in (utils.solo_models, utils.team_models):
        for data_set_type in ('test', 'model', 'verification',):
            with open (module.MatchReport.data_file(data_set_type), 'a') as f:
                f.write('')

def test_build_files():
    data_set_types = ('test', 'model', 'verification',)
    for module in (utils.solo_models, utils.team_models):
        last_changes = {}
        for data_set_type in data_set_types:
            last_changes[data_set_type] = os.stat(module.MatchReport.data_file(data_set_type)).st_mtime
        utils.sample.matches(module)
        for data_set_type in data_set_types:
            assert os.stat(module.MatchReport.data_file(data_set_type)).st_mtime > last_changes[data_set_type]
