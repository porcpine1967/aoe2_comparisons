#!/usr/bin/env python
""" Build sample data sets. """

import argparse
import concurrent.futures
import csv
import pathlib
import random
import time
import utils.solo_models
import utils.team_models

ROOT_DIR = str(pathlib.Path(__file__).parent.parent.absolute())

def get_record(n):
    return n.to_record()

def matches(module, chunksize=200):
    """ Splits matches into model, verification, and test data sets and writes to separate files. """
    matches = module.Match.all()
    print('{} matches'.format(len(matches)))
    random.shuffle(matches)

    # First 80% go to model
    model_edge = int(len(matches)*.8)
    # Second 10% go to verification
    verification_edge = int(len(matches)*.9)
    start = time.time()
    # Test
    print('{} matches for test'.format(len(matches[verification_edge:])))
    match_records = []
    with concurrent.futures.ProcessPoolExecutor() as executor:
        for match_record in executor.map(get_record, matches[verification_edge:], chunksize=chunksize):
            match_records.append(match_record)
    print('compiled {} match records for test'.format(len(match_records)))
    with open('{}/match_test_data.csv'.format(module.DATA_DIR), 'w') as f:
        writer = csv.writer(f)
        for record in match_records:
            if record[6] > 0:
                writer.writerow(record)
    print('Test took {} seconds with chunksize {}'.format(int(time.time() - start), chunksize))
    # Model
    print('{} matches for model'.format(len(matches[:model_edge])))
    start = time.time()
    match_records = []
    with concurrent.futures.ProcessPoolExecutor() as executor:
        for match_record in executor.map(get_record, matches[:model_edge], chunksize=chunksize):
            match_records.append(match_record)
    print('compiled {} match_records for model'.format(len(match_records)))
    with open('{}/match_model_data.csv'.format(module.DATA_DIR), 'w') as f:
        writer = csv.writer(f)
        for record in match_records:
            if record[6] > 0:
                writer.writerow(record)
    print('Model took {} seconds with chunksize {}'.format(int(time.time() - start), chunksize))
    # Verification
    print('{} matches for verification'.format(len(matches[model_edge:verification_edge])))
    start = time.time()
    match_records = []
    with concurrent.futures.ProcessPoolExecutor() as executor:
        for match_record in executor.map(get_record, matches[model_edge:verification_edge], chunksize=chunksize):
            match_records.append(match_record)
    print('compiled {} match_records for verification'.format(len(match_records)))
    with open('{}/match_verification_data.csv'.format(module.DATA_DIR), 'w') as f:
        writer = csv.writer(f)
        for record in match_records:
            if record[6] > 0:
                writer.writerow(record)
    print('Verification took {} seconds with chunksize {}'.format(int(time.time() - start), chunksize))
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('klass', choices=('team', 'solo',), help="team or solo")
    args = parser.parse_args()
    if args.klass == 'team':
        matches(utils.team_models)
    else:
        matches(utils.solo_models)
