#!/usr/bin/env python

""" Generates graphs for use in elo/writeup.txt """
from collections import defaultdict
import pathlib

import matplotlib.pyplot as plt
from scipy import stats
from statsmodels.stats.proportion import proportion_confint

ROOT_DIR = str(pathlib.Path(__file__).parent.parent.absolute())
GRAPH_DIR = '{}/graphs'.format(ROOT_DIR)

from utils.models import MatchReport

def nearest_x(num, x):
    """ Returns the number rounded down to the nearest 'x'.
    example: nearest_x(25, 20) returns 20. """
    for i in range(x):
        if not (num - i) % x:
            return num - i

def pct_win_by_rating():
    score_results_dict = defaultdict(lambda: [])
    for report in MatchReport.all('model'):
        score_results_dict[abs(report.score)].append(report.score)
    # For plotting data points with confidence interval
    x = []
    y = []
    yerr = []
    # For plotting linear regression. Note: initialized to ensure
    # that the intercept is at .5
    slope_x = [0 for _ in range(100000000)]
    slope_y = [.5 for _ in range(100000000)]
    for score in sorted(score_results_dict):
        values = score_results_dict[score]
        total = len(values)
        if score == 0:
            pct_win = .5
            err = 0
        else:
            # wins defined as victory for higher-rated player
            wins = len([i for i in values if i > 0])
            # cl is lower bound of confidence interval
            cl, _ = proportion_confint(wins, total)
            pct_win = wins / float(total)
            err = pct_win - cl
        # Add the rating difference and percent win the same
        # number for the number of records with that difference
        # in order to weight the regression proportionally
        for _ in range(total):
            slope_x.append(score)
            slope_y.append(pct_win)
        # Eliminate data with minimal value from graph
        # .12 was chosen as cutoff to maximize reasonable data
        if err < .12 and pct_win < 1 and total > 3:
            # Only plot every 5th record to make graph readable
            if not score % 5:
                x.append(score)
                y.append(pct_win)
                yerr.append(err)
    slope, intercept, r_value, p_value, std_err = stats.linregress(slope_x, slope_y)
    z = [(slope*i + intercept) for i in x]
    plt.title('Percentage win by rating difference')
    plt.xlabel('Rating difference')
    plt.ylabel('Win percentage')
    plt.plot(x, z, color='k', label='Regression')
    plt.errorbar(x, y, yerr=yerr, fmt='_', label='Data Point with CI')
    ax = plt.gca()
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles, labels, loc='lower right')
    plt.savefig('{}/win_by_rating.png'.format(GRAPH_DIR), dpi=180)

if __name__ == '__main__':
    pct_win_by_rating()
