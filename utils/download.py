#!/usr/bin/env python
from collections import defaultdict
import csv
import json
import os
import sys
import pathlib
import re

ROOT_DIR = pathlib.Path(__file__).parent.parent.absolute()

import requests

try:
    from utils.models import Match, Rating, User
except:
    from models import Match, Rating, User

MAX_DOWNLOAD = 10000

class DownloadMatch(Match):

    @property
    def recordable(self):
        return self.rating_1 and self.rating_2

def users():
    if os.path.exists(User.data_file):
        print('users.csv already exists')
        return
    url_template = 'https://aoe2.net/api/leaderboard?game=aoe2de&leaderboard_id=3&start={start}&count={count}'
    country_counter = defaultdict(lambda: [])
    records = 0
    rows = []
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
            rows.append(User(record))
        if len(rows) >= records:
            break
        start = MAX_DOWNLOAD + start
    with open(User.data_file, 'w') as f:
        csv.writer(f).writerows([User.header])
        csv.writer(f).writerows([u.to_csv for u in rows])

def matches(profile_id):
    """ Downloads matches for a given profile"""
    data_file = Match.data_file_template.format(profile_id)
    if os.path.exists(data_file):
        print('  matches for {} already exists'.format(profile_id))
        return
    url_template = 'https://aoe2.net/api/player/matches?game=aoe2de&profile_id={profile_id}&count={count}&start={start}'
    start = 1
    r1v1 = {}
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
                match = DownloadMatch(match_data)
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
        if match.recordable:
            matches.append(match)
    with open(data_file, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(Match.header)
        writer.writerows([m.to_csv for m in matches])

def ratings(profile_id):
    """ Downloads ratings for a given profile """
    data_file = Rating.data_file_template.format(profile_id)
    if os.path.exists(data_file):
        print('  ratings for {} already exists'.format(profile_id))
        return
    url_template = 'https://aoe2.net/api/player/ratinghistory?start={start}&count={count}&game=aoe2de&leaderboard_id=3&profile_id={profile_id}'
    start = 1
    r1v1 = {}
    total = 0
    ratings = []
    while True:
        print("  Downloading ratings {} to {} for {}".format(start, start - 1 + MAX_DOWNLOAD, profile_id))
        r = requests.get(url_template.format(start=start, count=MAX_DOWNLOAD, profile_id=profile_id))
        if r.status_code != 200:
            print(r.text)
            sys.exit(1)

        data = json.loads(r.text)
        for rating_data in data:
            rating = Rating(profile_id, rating_data)
            ratings.append(rating)
        if len(data) < MAX_DOWNLOAD:
            break
        start = MAX_DOWNLOAD + start
    last_rating = None
    for rating in sorted(ratings, key=lambda x: x.timestamp):
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
        writer.writerows([m.to_csv for m in ratings])

def profiles_from_files(file_prefix):
    profile_pattern = re.compile(r'{}_for_([0-9]+)\.csv'.format(file_prefix))
    profiles = set()
    for filename in os.listdir('{}/data'.format(ROOT_DIR)):
        m = profile_pattern.match(filename)
        if m:
            profiles.add(m.group(1))
    return profiles

def all_matches_and_ratings():
    print('Calling All Matches and Ratings')
    profile_ids = profiles_from_files('matches')

    to_download = set()
    for match in Match.all():
        if not match.player_id_1 in profile_ids:
            to_download.add(match.player_id_1)
        if not match.player_id_2 in profile_ids:
            to_download.add(match.player_id_2)
    print('Downloading {} profiles'.format(len(to_download)))
    for profile_id in to_download:
        matches(profile_id)
        ratings(profile_id)
    if to_download:
        all_matches_and_ratings()

if __name__ == '__main__':
    matching_profiles = profiles_from_files('matches')
    rating_profiles = profiles_from_files('ratings')
    for p in matching_profiles - rating_profiles:
        print(p)
