#!/usr/bin/env python
import argparse
from collections import defaultdict
import csv
import json
import concurrent.futures
import functools
import os
import sys
import pathlib
import pprint
import re
import sys
import time

ROOT_DIR = pathlib.Path(__file__).parent.parent.absolute()

import requests

import utils.solo_models
import utils.team_models

MAX_DOWNLOAD = 10000

def users(module, force=False, write=True):
    User = module.User
    existing_users = {}
    if os.path.exists(User.data_file()):
        if force:
            for u in User.all():
                existing_users[u.profile_id] = u
        else:
            print('users.csv already exists')
            return
    url_template = 'https://aoe2.net/api/leaderboard?game=aoe2de&leaderboard_id={lb}&start={start}&count={count}'
    records = 0
    added = 0
    start = 1
    while True:
        print("Downloading users from {} to {}".format(start, start - 1 + MAX_DOWNLOAD))
        r = requests.get(url_template.format(lb=module.leaderboard, start=start, count=MAX_DOWNLOAD))
        if r.status_code != 200:
            print(r.text)
            sys.exit(1)
        d = json.loads(r.text)
        if not records:
            records = d['total']
        for record in d['leaderboard']:
            added += 1
            if record['profile_id'] in existing_users:
                existing_users[record['profile_id']].update(record)
            else:
                u = User(record)
                existing_users[u.profile_id] = u
        if added >= records:
            break
        start = MAX_DOWNLOAD + start
    if write:
        with open(User.data_file(), 'w') as f:
            csv.writer(f).writerows([User.header])
            csv.writer(f).writerows([u.to_csv for u in existing_users.values()])
    return existing_users

def matches(profile_id, module, update=False):
    """ Downloads matches for a given profile"""
    Match = module.Match
    data_file = Match.data_file(profile_id)
    r1v1 = {}
    if os.path.exists(data_file):
        if update:
            for match in Match.all_for(profile_id):
                r1v1[match.started] = match
        else:
            print('  matches for {} already exists'.format(profile_id))
            return
    url_template = 'https://aoe2.net/api/player/matches?game=aoe2de&profile_id={profile_id}&count={count}&start={start}'
    start = 1
    total = 0

    while True:
        print("  Downloading matches {} to {} for {}".format(start, start - 1 + MAX_DOWNLOAD, profile_id))
        r = requests.get(url_template.format(start=start, count=MAX_DOWNLOAD, profile_id=profile_id))
        if r.status_code != 200:
            print(r.text)
            sys.exit(1)

        data = json.loads(r.text)
        for match_data in data:
            if match_data['leaderboard_id'] == module.leaderboard and module.num_player_check(match_data['num_players']):
                match = Match(match_data)
                r1v1[match.started] = match
        if len(data) < MAX_DOWNLOAD:
            break
        start = MAX_DOWNLOAD + start
    matches = []
    for starting in sorted(r1v1, reverse=True):
        match = r1v1[starting]
        try:
            current_rating = match.rating_for(profile_id)
        except:
            print(match.to_csv)
            raise
        if not current_rating:
            continue
        matches.append(match)
    with open(data_file, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(Match.header)
        writer.writerows([m.to_csv for m in matches])

def ratings(profile_id, module, update=False):
    """ Downloads ratings for a given profile """
    Rating = module.Rating
    data_file = Rating.data_file(profile_id)
    r1v1 = {}
    if os.path.exists(data_file):
        if update:
            for rating in Rating.all_for(profile_id):
                r1v1[rating.timestamp] = rating

        else:
            print('  ratings for {} already exists'.format(profile_id))
            return
    url_template = 'https://aoe2.net/api/player/ratinghistory?start={start}&count={count}&game=aoe2de&leaderboard_id={lb}&profile_id={profile_id}'
    start = 1
    total = 0
    while True:
        print("  Downloading ratings {} to {} for {}".format(start, start - 1 + MAX_DOWNLOAD, profile_id))
        r = requests.get(url_template.format(start=start, count=MAX_DOWNLOAD, lb=module.leaderboard, profile_id=profile_id))
        if r.status_code != 200:
            print(r.text)
            sys.exit(1)

        data = json.loads(r.text)
        for rating_data in data:
            rating = Rating(profile_id, rating_data)
            r1v1[rating.timestamp] = rating
        if len(data) < MAX_DOWNLOAD:
            break
        start = MAX_DOWNLOAD + start
    last_rating = None
    for rating in sorted(r1v1.values(), key=lambda x: x.timestamp):
        if last_rating:
            rating.old_rating = last_rating.rating
            if rating.num_wins > last_rating.num_wins:
                rating.won_state = 'won'
            elif rating.num_losses > last_rating.num_losses:
                rating.won_state = 'lost'
        last_rating = rating
    with open(data_file, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(Rating.header)
        writer.writerows([m.to_csv for m in r1v1.values()])

def profiles_from_files(file_prefix, module):
    profile_pattern = re.compile(r'{}_for_([0-9]+)\.csv$'.format(file_prefix))
    profiles = []
    ten_hours_ago = time.time() - 60*60*10
    # Get paths in order of modified time so oldest files first
    for filename in sorted(pathlib.Path(module.DATA_DIR).iterdir(), key=os.path.getmtime):
        m = profile_pattern.search(str(filename))
        if m:
            profiles.append(m.group(1))
    return profiles

def fetch_unchecked(profile_id, module, checked):
    unchecked = set()
    for match in module.Match.all_for(profile_id):
        for player_id in match.players:
            if not player_id in checked:
                unchecked.add(player_id)
    return unchecked

def new_matches_and_ratings(to_check, checked, module):
    print('Calling All Matches and Ratings')
    print('Checking {}, skipping {} profiles'.format(len(to_check), len(checked)))
    to_download = set()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for unchecked in executor.map(functools.partial(fetch_unchecked, module=module, checked=checked), to_check):
            to_download.update(unchecked)

    print('Downloading {} profiles'.format(len(to_download)))
    with concurrent.futures.ThreadPoolExecutor() as p:
        p.map(functools.partial(both, module=module), to_download)
    checked.update(to_download)
    if to_download:
        new_matches_and_ratings(to_download, checked, module)

def both_force(profile_id, module):
    matches(profile_id, module, True)
    ratings(profile_id, module, True)

def both(profile_id, module):
    matches(profile_id, module)
    ratings(profile_id, module)

def reconcile(module):
    match_ids = profiles_from_files('matches', module)
    rating_ids = profiles_from_files('ratings', module)
    for rating in rating_ids:
        if rating not in match_ids:
            matches(rating, module)
    for match in match_ids:
        if match not in rating_ids:
            ratings(match, module)

def update(module):
    file_profiles = profiles_from_files('ratings', module)
    # Sort by last modified, so files updated longest ago are updated first
    def priority(profile_id):
        if profile_id not in file_profiles:
            return 0
        return file_profiles.index(profile_id)
    users(module, True)
    all_users = module.User.all()
    user_list = sorted([str(user.profile_id) for user in all_users if user.should_update], key=priority)
    checked = set(profiles_from_files('matches', module))
    print('Downloading {} profiles'.format(len(user_list)))
    with concurrent.futures.ThreadPoolExecutor() as p:
        p.map(functools.partial(both_force, module=module), user_list)
    downloaded = set([u.profile_id for u in all_users])
    new_matches_and_ratings(downloaded, checked, module)

def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('klass', choices=('team', 'solo',), help="team or solo")
    args = parser.parse_args()
    if args.klass == 'team':
        update(utils.team_models)
    else:
        update(utils.solo_models)

if __name__ == '__main__':
    run()
