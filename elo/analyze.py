#!/usr/bin/env python

""" Functions for exploring rating data """
from collections import defaultdict, Counter
import csv
import json
import os
import pathlib
import random
import re
from statistics import stdev
import sys
import time

import matplotlib.pyplot as plt
import requests
import numpy as np
from scipy import stats
from statsmodels.stats.proportion import proportion_confint

ROOT_DIR = str(pathlib.Path(__file__).parent.parent.absolute())

from utils.filters import unique_player_reports
from utils.models import Match, Rating, User, MatchReport
from utils.models import Player as ModelPlayer
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
    with open('{}/team-data/users.csv'.format(ROOT_DIR)) as f:
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

def get_some_users(cnt):
    users = get_random_users(cnt)
    download_data(users)

def contradictions():
    """ Go through all the matches and see if there are contradictions in who won """
    match_info = defaultdict(lambda: [])
    matches = Match.all(True)
    for match in matches:
        if match.winner:
            match_info[match.match_id].append(match.winner)
    ctr = Counter()
    for match_id, winners in match_info.items():
        if len(winners) < 1:
            ctr['no info'] += 1
        elif len(winners) == 1:
            ctr['solo'] += 1
        elif len(set(winners)) == 1:
            ctr['confirmed'] += 1
        else:
            ctr['contradictory'] += 1
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

def ratings_hist():
    ctr = Counter()
    for report in MatchReport.all('all'):
        for rating in (report.rating_1, report.rating_2):
            if rating < 400:
                ctr[400] += 1
            elif rating < 500:
                ctr[500] += 1
            elif rating < 600:
                ctr[600] += 1
            elif rating < 700:
                ctr[700] += 1
            elif rating < 800:
                ctr[800] += 1
            elif rating < 900:
                ctr[900] += 1
            elif rating < 1000:
                ctr[1000] += 1
            elif rating < 1100:
                ctr[1100] += 1
            elif rating < 1200:
                ctr[1200] += 1
            elif rating < 1300:
                ctr[1300] += 1
            elif rating < 1400:
                ctr[1400] += 1
            elif rating < 1500:
                ctr[1500] += 1
            elif rating < 1600:
                ctr[1600] += 1
            elif rating < 1700:
                ctr[1700] += 1
            elif rating < 1800:
                ctr[1800] += 1
            elif rating < 1900:
                ctr[1900] += 1
            elif rating < 2000:
                ctr[2000] += 1
            elif rating < 2100:
                ctr[2100] += 1
            else:
                ctr[2200] += 1
    for k in sorted(ctr):
        print('{:>5}: {:>8}'.format(k, ctr[k]))

def err_by_count():
    model_elo_dict = defaultdict(lambda: [])
    for report in MatchReport.all('test'):
        if report.score == 0:
            continue
        model_elo_dict[abs(report.score)].append(report.score)
    total_err = {}
    for score in sorted(model_elo_dict):
        values = model_elo_dict[score]
        total = float(len(values))
        wins = len([i for i in values if i > 0])
        cl, _ = proportion_confint(wins, total)
        pct_win = wins / float(total)
        err = pct_win - cl
        try:
            if total_err[total] != err:
                print(total_err[total] - err, total)
        except KeyError:
            pass
        total_err[total] = err
    for total in sorted(total_err):
        print('{:>3}: {:>2.2f}'.format(total, total_err[total]))

def cnt_by_win_pct():
    model_elo_dict = defaultdict(lambda: [])
    for report in MatchReport.all('model'):
        if report.score == 0:
            continue
        model_elo_dict[abs(report.score)].append(report.score)
    for score in sorted(model_elo_dict):
        values = model_elo_dict[score]
        wins = len([i for i in values if i > 0])
        total = len(values)
        cl, _ = proportion_confint(wins, total)
        pct_win = wins / float(total)
        print('{:>4}: {:>5}: {:>.2f}: {:>.3f}'.format(score, total, pct_win))

def likelihood_of_win():
    wins = 0
    matches = MatchReport.all('verification')
    print(len(matches))
    total = 0
    for report in matches:
        if report.score == 0:
            continue
        if report.score > 0:
            wins += 1
        total += 1
    cl, _ = proportion_confint(wins, total)
    pct_win = wins/float(total)
    print(pct_win, total, pct_win - cl)

def nearest_20(num):
    for i in range(20):
        if not (num - i) % 20:
            return num - i

def pct_win_by_elo():
    score_results_dict = defaultdict(lambda: [])
    for report in MatchReport.all('model'):
        score_results_dict[abs(report.score)].append(report.score)
    slope_x = []
    x2 = []
    y = []
    y2 = []
    for score in sorted(score_results_dict):
        values = score_results_dict[score]

        total = len(values)
        if total < 3:
            continue
        if score == 0:
            pct_win = .5
        else:
            wins = len([i for i in values if i > 0])
            cl, _ = proportion_confint(wins, total)
            pct_win = wins / float(total)
        if True: #wins < total and pct_win - cl < .05:
            for _ in range(total):
                x2.append(score)
                y2.append(pct_win)
            slope_x.append(score)
            y.append(pct_win)
    print(len(slope_x))
    slope, intercept, r_value, p_value, std_err = stats.linregress(slope_x,y)
    slope2, intercept2, r_value, p_value, std_err = stats.linregress(x2,y2)
    print(intercept, slope)
    print(intercept2, slope2)
    z = [(slope*i + intercept) for i in slope_x]
    z2 = [(slope2*i + intercept2) for i in x2]

    plt.plot(slope_x, z)
    plt.plot(x2, z2)
    plt.show()

def rating_diff_by_rating_bucket():
    """ See how different the differences are based on rating bucket (68/95 rule) """
    ratings_raw = []
    matches = MatchReport.all('test')
    for report in matches:
        ratings_raw.append(report.rating_1)
        ratings_raw.append(report.rating_2)
    ratings = sorted(ratings_raw)
    total_cnt = len(ratings)

    # edges = [ratings[int(.025*total_cnt)] - 1,
    #              ratings[int(.16*total_cnt)] - 1,
    #              int(np.median(ratings)) - 1,
    #              ratings[int(.84*total_cnt)] - 1,
    #              ratings[int(.975*total_cnt)] -1]
    edges = [np.quantile(ratings, .1 + .1*i) for i in range(9)]
    edge_counters = defaultdict(lambda: Counter())
    for report in matches:
        found = False
        for edge in edges:
            if report.rating_1 < edge:
                found = True
                edge_counters[edge][abs(report.score)] += 1
                break
        if not found:
            edge_counters['big'][abs(report.score)] += 1
        found = False
        for edge in edges:
            if report.rating_2 < edge:
                found = True
                edge_counters[edge][abs(report.score)] += 1
                break
        if not found:
            edge_counters['big'][abs(report.score)] += 1
    fig, axs = plt.subplots(nrows=len(edges) + 1, ncols=1, sharex=True)
    hold = 0
    for idx, edge in enumerate(edges):
        ctr = edge_counters[edge]
        ax = axs[idx]
        plot_dist(ax, ctr, '{} - {}'.format(hold, edge - 1))
        hold = edge

    ctr = edge_counters['big']
    ax = axs[-1]
    plot_dist(ax, ctr, '{}+'.format(hold))
    fig.tight_layout(pad=0.3)
    plt.show()

def plot_dist(ax, ctr, title):
    ax.set_title(title)
    xs = []
    ys = []
    for x in sorted(ctr):
        if ctr[x] < 3:
            continue
        xs.append(x)
        ys.append(ctr[x])
    ax.plot(xs, ys)

def duplicate_matches():
    """ Percentage of matches between the same two players."""
    competition_counter = Counter()
    for report in  MatchReport.all('all'):
        competition_counter[report.competition_key] += 1
    dup_counter = Counter()
    for v in competition_counter.values():
        dup_counter[v] += 1
    for k in sorted(dup_counter):
        print('{:>3}: {:>7}'.format(k, dup_counter[k]))

def filtered_matches(player_matches, used_players):
    """ Returns a dictionary of player_matches without any used players """
    r = defaultdict(lambda: [])
    for report_list in player_matches.values():
        for report in report_list:
            if report.player_1 in used_players or report.player_2 in used_players:
                continue
            r[report.player_1].append(report)
            r[report.player_2].append(report)
    return r

def counts_per_player(data_set_type):
    match_reports = MatchReport.all(data_set_type)
    matches = unique_player_reports(match_reports)
    players = set()
    for r in matches:
        players.add(r.player_1)
        players.add(r.player_2)
    print(len(matches)*2 == len(players))

class Player:
    def __init__(self, player_id):
        self.player_id = player_id
        self.upper_range = 0
        self.lower_range = 10000
        self.ratings = []
        self.valid = False

    def set_bounds(self, max_std, mincount):
        """ Sets upper and lower bounds of ratings that generate
a standard deviation within max_std and that contain at least mincount ratings."""
        if len(self.ratings) < mincount:
            return
        sorted_ratings = sorted(self.ratings)
        srstd = stdev(self.ratings)
        while srstd > max_std and len(sorted_ratings) >= mincount:
            if sorted_ratings[-1] - sorted_ratings[-2] > sorted_ratings[1] - sorted_ratings[0]:
                del(sorted_ratings[-1])
            else:
                del(sorted_ratings[0])
            srstd = stdev(sorted_ratings)
        if srstd <= max_std:
            self.upper_range = max(self.ratings)
            self.lower_range = min(self.ratings)
            self.valid = True

def player_rating_stdevs(data_set_type):
    match_reports = sorted(MatchReport.all(data_set_type), key=lambda x: x.timestamp)
    players = {}
    for report in match_reports:
        if not report.player_1 in players:
            players[report.player_1] = Player(report.player_1)
        if not report.player_2 in players:
            players[report.player_2] = Player(report.player_2)
        players[report.player_1].ratings.append(report.rating_1)
        players[report.player_2].ratings.append(report.rating_2)
    stdevs = Counter()

    for player in players.values():
        l = player.ratings
        if len(l) < 10:
            continue
        sorted_ratings = sorted(l)
        best_group = sorted_ratings[:10]
        best_std = stdev(best_group)
        for i in range(len(l) - 10):
            test_group = sorted_ratings[i:i+10]
            test_std = stdev(test_group)
            if test_std < best_std:
                best_group = test_group
                best_std = test_std
        stdevs[int(best_std)] += 1
    rolling_sum = 0
    for sd in sorted(stdevs):
        rolling_sum += stdevs[sd]
        print('{:>5}: {:>5} : {:>7}'.format(sd, stdevs[sd], rolling_sum))

def players_with_decent_ratings(data_set_type, max_std, mincount):
    match_reports = sorted(MatchReport.all(data_set_type), key=lambda x: x.timestamp)
    players = {}
    player_counter = Counter()
    for report in match_reports:
        if not report.player_1 in players:
            players[report.player_1] = Player(report.player_1)
        if not report.player_2 in players:
            players[report.player_2] = Player(report.player_2)
        players[report.player_1].ratings.append(report.rating_1)
        players[report.player_2].ratings.append(report.rating_2)
    print(len(players))
    for player in players.values():
        player.set_bounds(max_std, mincount)
    good_matches = []
    for report in match_reports:
        p1 = players[report.player_1]
        p2 = players[report.player_2]
        if p1.lower_range < report.rating_1 < p1.upper_range and p2.lower_range < report.rating_2 < p2.upper_range:
            good_matches.append(report)
    print(len(good_matches))

def stddev_counts(data_set_type):
    matches = MatchReport.all(data_set_type)
    stdevs = Counter()
    players = [p for p in ModelPlayer.player_values(matches) if len(p.ratings) > 4]
    for player in players:
        stdevs[int(stdev(player.ratings))] += 1
    running_total = 0.0
    for std in sorted(stdevs):
        running_total += stdevs[std]
        print('{:>4}:{:>5}: {:>5} ({:.2f})'.format(std, stdevs[std], int(running_total), running_total/len(players)))
def best_stddev_counts(data_set_type, mincount):
    matches = MatchReport.all(data_set_type)
    stdevs = Counter()
    players = ModelPlayer.rated_players(matches, mincount)
    for player in players:
        stdevs[int(player.best_stdev(mincount))] += 1
    running_total = 0.0
    for std in sorted(stdevs):
        running_total += stdevs[std]
        print('{:>4}:{:>5}: {:>5} ({:.2f})'.format(std, stdevs[std], int(running_total), running_total/len(players)))

def ratings_counts(data_set_type):
    matches = MatchReport.all(data_set_type)
    ctr = Counter()
    players = ModelPlayer.player_values(matches)
    lp = float(len(players))
    for player in players:
        ctr[len(player.matches)] += 1
    rt = 0
    for c in sorted(ctr, reverse=True):
        rt += ctr[c]
        print('{:>4}:{:>5}: {:>5} ({:.2f})'.format(c, ctr[c], int(rt), rt/lp))

def minimum_timestamp_match_report(data_set_type):
    print(min([m.timestamp for m in MatchReport.all(data_set_type)]))

def minimum_timestamp_rating(data_set_type):
    timestamps = set()
    for player in ModelPlayer.player_values(MatchReport.all(data_set_type)):
        timestamps |= set([r.timestamp for r in Rating.all_for(player.player_id)])
    print(min(timestamps))

if __name__ == '__main__':
    file_prefix = 'matches'
    profile_pattern = re.compile(r'{}_for_([0-9]+)\.csv'.format(file_prefix))
    profiles = set()
    inout = Counter()
    ten_hours_ago = time.time() - 60*60*10
    for filename in os.listdir('{}/team-data'.format(ROOT_DIR)):
        m = profile_pattern.match(filename)
        if m:
            mtime = os.stat('{}/team-data/{}'.format(ROOT_DIR, filename)).st_mtime
            if mtime - ten_hours_ago > 0:
                inout['in'] += 1
            else:
                inout['out'] += 1
    print(inout)
