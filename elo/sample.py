#!/usr/bin/env python
""" Build sample data sets. """

import csv
import pathlib
import random

from utils.models import Match

ROOT_DIR = str(pathlib.Path(__file__).parent.parent.absolute())

def matches():
    """ Splits matches into model, verification, and test data sets and writes to separate files. """
    matches = Match.all()
    random.shuffle(matches)

    # First 80% go to model
    model_edge = int(len(matches)*.8)
    # Second 10% go to verification
    verification_edge = int(len(matches)*.9)

    # Model
    with open('{}/data/match_model_data.csv'.format(ROOT_DIR), 'w') as f:
        writer = csv.writer(f)
        for match in matches[:model_edge]:
            record = match.to_record()
            if record[-1] > 0:
                writer.writerow(record)

    # Verification
    with open('{}/data/match_verification_data.csv'.format(ROOT_DIR), 'w') as f:
        writer = csv.writer(f)
        for match in matches[model_edge:verification_edge]:
            record = match.to_record()
            if record[-1] > 0:
                writer.writerow(record)

    # Test
    with open('{}/data/match_test_data.csv'.format(ROOT_DIR), 'w') as f:
        writer = csv.writer(f)
        for match in matches[verification_edge:]:
            record = match.to_record()
            if record[-1] > 0:
                writer.writerow(record)

if __name__ == '__main__':
    matches()
