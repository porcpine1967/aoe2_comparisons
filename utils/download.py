#!/usr/bin/env python
from collections import defaultdict
import csv
import json
from concurrent.futures import ThreadPoolExecutor as Pool
import os
import sys
import pathlib
import re
import time

ROOT_DIR = pathlib.Path(__file__).parent.parent.absolute()

import requests

from utils.team_models import Match, Rating, User

MAX_DOWNLOAD = 10000

def users(force=False, write=True):
    existing_users = {}
    if os.path.exists(User.data_file):
        if force:
            for u in User.all():
                existing_users[u.profile_id] = u
        else:
            print('users.csv already exists')
            return
    url_template = 'https://aoe2.net/api/leaderboard?game=aoe2de&leaderboard_id=4&start={start}&count={count}'
    records = 0
    added = 0
    start = 1
    while True:
        print("Downloading users from {} to {}".format(start, start - 1 + MAX_DOWNLOAD))
        r = requests.get(url_template.format(start=start, count=MAX_DOWNLOAD))
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
        with open(User.data_file, 'w') as f:
            csv.writer(f).writerows([User.header])
            csv.writer(f).writerows([u.to_csv for u in existing_users.values()])
    return existing_users

def matches(profile_id, update=False):
    """ Downloads matches for a given profile"""
    data_file = Match.data_file_template.format(profile_id)
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
            if match_data['leaderboard_id'] == 4 and match_data['num_players'] >= 2:
                match = Match(match_data)
                r1v1[match.started] = match
        if len(data) < MAX_DOWNLOAD:
            break
        start = MAX_DOWNLOAD + start
    matches = []
    for starting in sorted(r1v1, reverse=True):
        match = r1v1[starting]
        current_rating = match.rating_for(profile_id)
        if not current_rating:
            continue
        matches.append(match)
    with open(data_file, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(Match.header)
        writer.writerows([m.to_csv for m in matches])

def ratings(profile_id, update=False):
    """ Downloads ratings for a given profile """
    data_file = Rating.data_file_template.format(profile_id)
    r1v1 = {}
    if os.path.exists(data_file):
        if update:
            for rating in Rating.all_for(profile_id):
                r1v1[rating.timestamp] = rating

        else:
            print('  ratings for {} already exists'.format(profile_id))
            return
    url_template = 'https://aoe2.net/api/player/ratinghistory?start={start}&count={count}&game=aoe2de&leaderboard_id=4&profile_id={profile_id}'
    start = 1
    total = 0
    while True:
        print("  Downloading ratings {} to {} for {}".format(start, start - 1 + MAX_DOWNLOAD, profile_id))
        r = requests.get(url_template.format(start=start, count=MAX_DOWNLOAD, profile_id=profile_id))
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

def profiles_from_files(file_prefix):
    profile_pattern = re.compile(r'{}_for_([0-9]+)\.csv$'.format(file_prefix))
    profiles = []
    ten_hours_ago = time.time() - 60*60*10
    # Get paths in order of modified time so oldest files first
    for filename in sorted(pathlib.Path(Rating.data_dir).iterdir(), key=os.path.getmtime):
        m = profile_pattern.search(str(filename))
        if m:
            profiles.append(m.group(1))
    return profiles

def new_matches_and_ratings(to_check, checked):
    print('Calling All Matches and Ratings')
    print('Will skip {} profiles'.format(len(downloaded)))
    to_download = set()
    for profile_id in to_check:
        for match in Match.all_for(profile_id):
            for player_id in match.players:
                if not player_id in checked:
                    to_download.add(player_id)

    print('Downloading {} profiles'.format(len(to_download)))
    with Pool() as p:
        p.map(both, to_download)
    if to_download:
        new_matches_and_ratings(to_download, checked + to_download)

def both_force(profile_id):
    matches(profile_id, True)
    ratings(profile_id, True)

def both(profile_id):
    matches(profile_id)
    ratings(profile_id)

def reconcile():
    match_ids = profiles_from_files('matches')
    rating_ids = profiles_from_files('ratings')
    for rating in rating_ids:
        if rating not in match_ids:
            matches(rating)
    for match in match_ids:
        if match not in rating_ids:
            ratings(match)

def update():
    file_profiles = profiles_from_files('ratings')
    # Sort by last modified, so files updated longest ago are updated first
    def priority(profile_id):
        if profile_id not in file_profiles:
            return 0
        return file_profiles.index(profile_id)
    users(True)
    all_users = User.all()
    user_list = sorted([str(user.profile_id) for user in all_users if user.should_update], key=priority)
    checked = set(profiles_from_files('matches'))
    print('Downloading {} profiles'.format(len(user_list)))
    with Pool() as p:
        p.map(both_force, user_list)
    downloaded = set([u.profile_id for u in all_users])
    new_matches_and_ratings(downloaded, checked)

if __name__ == '__main__':
    all_users = User.all()
    downloaded = set([u.profile_id for u in all_users])
    new_matches_and_ratings(downloaded, set(profiles_from_files('ratings')))
