#!/usr/bin/env python
from collections import defaultdict
import csv
import json
import os
import sys

import requests

try:
    from utils.models import Match, User
except:
    from models import Match, User

MAX_DOWNLOAD = 10000

class DownloadMatch(Match):
    def mark_lost(self, profile_id):
        if profile_id == self.player_id_1:
            self.winner = 2
        elif profile_id == self.player_id_2:
            self.winner = 1
        
    def mark_won(self, profile_id):
        if str(profile_id) == self.player_id_1:
            self.winner = 1
        elif str(profile_id) == self.player_id_2:
            self.winner = 2

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
        print('matches for {} already exists'.format(profile_id))
        return
    url_template = 'https://aoe2.net/api/player/matches?game=aoe2de&profile_id={profile_id}&count={count}&start={start}'
    start = 1
    r1v1 = {}
    total = 0

    while True:
        print("Downloading matches {} to {} for {}".format(start, start - 1 + MAX_DOWNLOAD, profile_id))
        r = requests.get(url_template.format(start=start, count=MAX_DOWNLOAD, profile_id=profile_id))
        if r.status_code != 200:
            print(r.text)
            sys.exit(1)
        
        data = json.loads(r.text)
        for match_data in data:
            if match_data['leaderboard_id'] == 3:
                match = DownloadMatch(match_data)
                r1v1[match.started] = match
        if len(data) < MAX_DOWNLOAD:
            break
        start = MAX_DOWNLOAD + start
    next_rating = None
    matches = []
    for starting in sorted(r1v1, reverse=True):
        match = r1v1[starting]
        current_rating = match.rating_for(profile_id)
        if not current_rating:
            continue
        if next_rating and match.recordable:
            if next_rating > current_rating:
                match.mark_won(profile_id)
                matches.append(match)
            elif next_rating < current_rating:
                match.mark_lost(profile_id)
                matches.append(match)
        next_rating = current_rating
    with open(data_file, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(Match.header)
        writer.writerows([m.to_csv for m in matches])
if __name__ == '__main__':
    matches('261906')
