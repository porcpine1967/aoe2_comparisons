import os

import pytest

import utils.solo_models
import utils.team_models
import utils.sample

@pytest.fixture(scope="session", autouse=True)
def set_model_data_file_templates():
    if not '/tests' in utils.solo_models.Match.data_file_template:
        utils.solo_models.Match.data_file_template = utils.solo_models.Match.data_file_template.replace('/data', '/tests/data')
    if not '/tests' in utils.solo_models.MatchReport.data_file_template:
        utils.solo_models.MatchReport.data_file_template = utils.solo_models.MatchReport.data_file_template.replace('/data', '/tests/data')
    if not '/tests' in utils.solo_models.Rating.data_dir:
        utils.solo_models.Rating.data_dir = utils.solo_models.Rating.data_dir.replace('/data', '/tests/data')
    if not '/tests' in utils.team_models.Match.data_file_template:
        utils.team_models.Match.data_file_template = utils.team_models.Match.data_file_template.replace('/team-data', '/tests/team-data')
    if not '/tests' in utils.team_models.MatchReport.data_file_template:
        utils.team_models.MatchReport.data_file_template = utils.team_models.MatchReport.data_file_template.replace('/team-data', '/tests/team-data')
    if not '/tests' in utils.team_models.Rating.data_dir:
        utils.team_models.Rating.data_dir = utils.team_models.Rating.data_dir.replace('/team-data', '/tests/team-data')

def test_build_files():
    data_set_types = ('test', 'model', 'verification',)
    for module in (utils.solo_models, utils.team_models):
        last_changes = {}
        for data_set_type in data_set_types:
            last_changes[data_set_type] = os.stat(module.MatchReport.data_file_template.format(data_set_type)).st_mtime
        utils.sample.matches(module)
        for data_set_type in data_set_types:
            assert os.stat(module.MatchReport.data_file_template.format(data_set_type)).st_mtime > last_changes[data_set_type]
