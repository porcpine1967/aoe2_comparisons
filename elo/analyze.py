#!/usr/bin/env python

""" Looks at the elo progression of 100 random players from 1v1 ranked in order to see if there are any patterns."""
from collections import defaultdict, Counter
import csv
import json
import os
import pathlib
import random
import sys

import matplotlib.pyplot as plt
import requests

ROOT_DIR = str(pathlib.Path(__file__).parent.parent.absolute())

from utils.models import Match, Rating, User, MatchReport
import utils.download
import utils.lookup

class SampleUser(User):
    @property
    def diffs(self):
        """ Returns an array of values for plotting over time"""
        differences = []
        sorted_ratings = sorted(self.ratings, key=lambda x: x.timestamp)
        last = None
        for cnt, rating in enumerate(sorted_ratings):
            if last and cnt > 9:
                differences.append(rating.rating - sorted_ratings[-1].rating)
            last = rating
            if len(differences) > 20000:
                break
        return differences

    @property
    def count(self):
        """ Returns a scalar for counting vs others"""
        last_rating = sorted(self.ratings, key=lambda x: x.timestamp)[-1]
        return abs(last_rating.num_wins - last_rating.num_losses)/(last_rating.num_wins + last_rating.num_losses)

def rating_from_csv(row):
    return Rating(row[0], { 'rating': int(row[1]), 'num_wins': int(row[2]), 'num_losses': int(row[3]), 'drops': int(row[4]), 'timestamp' : int(row[5]) })

def get_users():
    """ Gets all users in users.csv """
    users = {}
    with open('{}/data/users.csv'.format(ROOT_DIR)) as f:
        r = csv.reader(f)
        for row in r:
            try:
                users[row[0]] = SampleUser(row)
            except ValueError:
                pass
    return users

def get_random_users(cnt):
    """ Selects 'cnt' users from ranked 1v1"""
    return random.sample([x for x in SampleUser.all()], cnt)

def retrieve_data(url):
    r = requests.get(url)
    if r.status_code != 200:
        print(r.text)
        sys.exit(1)
    return json.loads(r.text)

def download_data(users):
    """ Downloads and stores the ratings history of supplied users.
        Returns path to file in which data is stored
"""
    for user in users:
        utils.download.matches(user.profile_id)

def graph_sample():
    ctr = Counter()
    for report in MatchReport.all('test'):
        ctr[report.score] += 1
    x = []
    for i in range(max(ctr) + 1):
        x.append(ctr[i])
    plt.plot(x)
    plt.show()

def civ_details():
    constants = utils.lookup.constants()
    matchup_counter = Counter()
    tot_ctr = 0
    for match in Match.all():
        tot_ctr += 1
        matchup_code = '{}-{}-{}'.format(min(match.civ_1, match.civ_2), max(match.civ_1, match.civ_2), 1)
        matchup_counter[matchup_code] += 1
    same_ctr = 0
    for c, v in matchup_counter.most_common():
        c1, c2, m = [int(x) for x in c.split('-')]
        if c1 != c2:
            continue
        print(constants['civ'][c1],constants['civ'][c2], v) #,constants['map_type'][m], v)
        if c1 == c2:
            same_ctr += v
    print(same_ctr)

def elo_as_determinant():
    diff_ctr = Counter()
    pos = 0
    neg = 0
    for match in Match.all():
        if match.civ_1 != match.civ_2:
            continue
        diff_ctr[match.rating_diff] += 1
        if match.rating_diff < -600:
            print(match.to_csv)
    x = []
    y = []
    for i in range(min(diff_ctr) - 1, max(diff_ctr) + 1):
        if diff_ctr[i] > 0:
            if i >= 0:
                pos += 1
            else:
                neg += 1
            x.append(i)
            y.append(diff_ctr[i])
    print(pos, neg)
    print(len(x))
    plt.scatter(x, y, s=3)
    plt.show()

def map_details():
    constants = utils.lookup.constants()
    map_counter = Counter()
    for match in Match.all():
        map_counter[match.map_type] += 1
    for m, v in map_counter.most_common():
        print(constants['map_type'][m], v)
def get_some_users(cnt):
    users = get_random_users(cnt)
    download_data(users)

def contradictions():
    """ Go through all the matches and see if there are contradictions in who won """
    match_info = defaultdict(lambda: [])
    matches = Match.all(True)
    for match in matches:
        match_info[match.match_id].append(match.winner)
    ctr = Counter()
    for match_id, winners in match_info.items():
        ctr['-'.join([str(x) for x in sorted(winners)])] += 1
    for k, cnt in ctr.most_common():
        print(k, cnt)

def test_match_winner():
    match_info = defaultdict(lambda: [])
    matches = Match.all(True)
    for match in matches:
        if match.winner == 0:
            continue
        if not match.determine_winner() == match.winner:
            print('****************************')
            print(match.winner, match.determine_winner())
            row = match.to_csv
            for profile_id in (row[5], row[8]):
                old_determine(profile_id, [str(x) for x in row])

def test_determine(row):
    """ Takes a match row and determines winner """
    match = Match.from_csv(row)
    print(match.determine_winner())

def old_determine(profile_id, row):
    won_state = set(('won',))
    lost_state = set(('lost',))
    rating_lookup = defaultdict(lambda:[])
    for rating in Rating.all_for(profile_id):
        rating_lookup[rating.old_rating].append(rating)

    match = Match.from_csv(row)
    match_rating = match.rating_for(profile_id)
    if not match_rating in rating_lookup:
        return
    possible_win_states = set()
    for rating in rating_lookup[match_rating]:
        if 0 < rating.timestamp - match.started < 3600:
            possible_win_states.add(rating.won_state)
    if possible_win_states == won_state:
        print('{} won'.format(profile_id))
    elif possible_win_states == lost_state:
        print('{} lost'.format(profile_id))

def run():
    row = ['21258848', 1589298957, 86, 28, 982, '1372812', 4, 1017, '1135871', 2]
    test_determine([str(x) for x in row])
    for profile_id in (row[5], row[8]):
        old_determine(profile_id, [str(x) for x in row])
if __name__ == '__main__':
    graph_sample()
