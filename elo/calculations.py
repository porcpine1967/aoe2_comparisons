#!/usr/bin/env python

""" Calculates numbers for use in writeup. """
from collections import defaultdict, Counter
import csv
import json
from math import log
import os
import pathlib
import random
import sys

import matplotlib.pyplot as plt
import requests
from scipy import stats
from statsmodels.stats.proportion import proportion_confint

ROOT_DIR = str(pathlib.Path(__file__).parent.parent.absolute())

from utils.models import Match, Rating, User, MatchReport
import utils.download
import utils.lookup

def likelihood_of_win_if_higher_rank(data_set_type):
    matches = MatchReport.all(data_set_type)
    all_match_count = len(matches)
    wins = 0
    total = 0
    for report in matches:
        # win defined as victory for higher-rated player
        if report.score > 0:
            wins += 1
        # Do not add if no difference in rating
        if report.score:
            total += 1
    cl, _ = proportion_confint(wins, total)
    pct_win = wins/float(total)
    print(data_set_type)
    print('{:>7} records out of {:>7} total, win pct: {:.3f}, ci: {:.3f}'.format(total, all_match_count, pct_win, pct_win - cl))

def correlation_and_regression(data_set_type):
    matches = MatchReport.by_rating(data_set_type, 0, 10000)
    print(len(matches))
    score_results_dict = defaultdict(lambda: [])
    for report in MatchReport.all('model'):
        score_results_dict[abs(report.score)].append(report.score)
    # For deterimining linear regression. Note: initialized to ensure
    # that the intercept is at .5
    x = []#0 for _ in range(100*len(matches))]
    y = []#.5 for _ in range(100*len(matches))]
    for score in sorted(score_results_dict):
        values = score_results_dict[score]
        total = len(values)
        # Do not calculate if no difference in rating
        if score:
            # win defined as victory for higher-rated player
            wins = len([i for i in values if i > 0])
            pct_win = wins / float(total)
            # Add the rating difference and percent win the same
            # number for the number of records with that difference
            # in order to weight the regression proportionally
            for _ in range(total):
                x.append(score)
                y.append(pct_win)
    slope, intercept, r_value, p_value, stderr = stats.linregress(x, y)
    print(data_set_type)
    print('  Intercept: {:.3f}, Slope: {:.4f}, R value: {:.3f}, p value: {}, Std Err: {}'.format(intercept, slope, r_value, p_value, stderr))

def ratings_correlation_and_regression(data_set_type):
    ctr = Counter()
    for report in MatchReport.all('model'):
        ctr[abs(report.score)] += 1
    xs = []
    log_ys = []
    for x in sorted(ctr)[1:]:
        if ctr[x] < 10:
            continue
        xs.append(x)
        log_ys.append(log(ctr[x]))
    slope, intercept, r_value, _, _ = stats.linregress(xs, log_ys)
    print(data_set_type)
    print('  Intercept: {:.3f}, Slope: {:.4f}, R value: {:.3f}'.format(intercept, slope, r_value))

if __name__ == '__main__':
    for data_set_type in ('model', 'verification',):
        correlation_and_regression(data_set_type)
