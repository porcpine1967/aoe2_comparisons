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

try:
    from utils.models import Match, Rating, User
except:
    from models import Match, Rating, User

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
    url_template = 'https://aoe2.net/api/leaderboard?game=aoe2de&leaderboard_id=3&start={start}&count={count}'
    records = 0
    added = 0
    start = 1
    while True:
        print("Downloading from {} to {}".format(start, start - 1 + MAX_DOWNLOAD))
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
            if match_data['leaderboard_id'] == 3 and match_data['num_players'] == 2:
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
    url_template = 'https://aoe2.net/api/player/ratinghistory?start={start}&count={count}&game=aoe2de&leaderboard_id=3&profile_id={profile_id}'
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
    profile_pattern = re.compile(r'{}_for_([0-9]+)\.csv'.format(file_prefix))
    profiles = set()
    ten_hours_ago = time.time() - 60*60*10
    for filename in os.listdir('{}/data'.format(ROOT_DIR)):
        m = profile_pattern.match(filename)
        if m:
            profiles.add(m.group(1))
    return profiles

def new_matches_and_ratings(downloaded, checked):
    print('Calling All Matches and Ratings')
    print('Will skip {} profiles'.format(len(downloaded)))
    to_download = set()
    for profile_id in downloaded - checked:
        for match in Match.all_for(profile_id):
            if not match.player_id_1 in downloaded:
                to_download.add(match.player_id_1)
            if not match.player_id_2 in downloaded:
                to_download.add(match.player_id_2)
        checked.add(profile_id)

    print('Downloading {} profiles'.format(len(to_download)))
    with Pool(10) as p:
        p.map(both, to_download)
    for profile_id in to_download:
        downloaded.add(profile_id)
    if to_download:
        new_matches_and_ratings(downloaded, checked)

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
    users(True)
    all_users = User.all()
    user_list = [user.profile_id for user in all_users if user.should_update]
    print('Downloading {} profiles'.format(len(user_list)))
    with Pool(10) as p:
        p.map(both_force, user_list)
    downloaded = set([u.profile_id for u in all_users])
    checked = profiles_from_files('matches')
    new_matches_and_ratings(downloaded.union(checked), checked)

if __name__ == '__main__':
    reconcile()
