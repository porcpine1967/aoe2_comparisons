#!/usr/bin/env python

""" Generates graphs for use in elo/writeup.txt """
from collections import defaultdict, Counter
from math import log
import pathlib
from statistics import stdev

import matplotlib.pyplot as plt
from scipy import stats
from statsmodels.stats.proportion import proportion_confint

ROOT_DIR = str(pathlib.Path(__file__).parent.parent.absolute())
GRAPH_DIR = '{}/graphs'.format(ROOT_DIR)

from utils.filters import unique_player_combo_reports
from utils.models import MatchReport, Player

def nearest_x(num, x):
    """ Returns the number rounded down to the nearest 'x'.
    example: nearest_x(25, 20) returns 20. """
    for i in range(x):
        if not (num - i) % x:
            return num - i

def pct_win_by_rating(data_set_type):
    score_results_dict = defaultdict(lambda: [])
    for report in unique_player_combo_reports(MatchReport.all(data_set_type)):
        score_results_dict[abs(report.score)].append(report.score)
    # For plotting data points with confidence interval
    x = []
    y = []
    lower_yerr = []
    upper_yerr = []
    yerr = [lower_yerr, upper_yerr,]
    # For plotting linear regression. Note: initialized to ensure
    # that the intercept is at .5
    slope_x = [0 for _ in range(100000000)]
    slope_y = [.5 for _ in range(100000000)]
    for score in sorted(score_results_dict):
        values = score_results_dict[score]
        total = len(values)
        if score == 0:
            pct_win = .5
            lower_err = upper_err = 0
        else:
            # wins defined as victory for higher-rated player
            wins = len([i for i in values if i > 0])
            # cl is lower bound of confidence interval
            cl, cu = proportion_confint(wins, total, method='wilson')
            pct_win = wins / float(total)
            lower_err = pct_win - cl
            upper_err = cu - pct_win
        # Add the rating difference and percent win the same
        # number for the number of records with that difference
        # in order to weight the regression proportionally
        for _ in range(total):
            slope_x.append(score)
            slope_y.append(pct_win)
        # Eliminate data with minimal value from graph
        # .12 was chosen as cutoff to maximize reasonable data
        if lower_err < .2 and pct_win < 1 and total > 3:
            # Only plot every 5th record to make graph readable
            if not score % 5:
                x.append(score)
                y.append(pct_win)
                lower_yerr.append(lower_err)
                upper_yerr.append(upper_err)
    slope, intercept, r_value, p_value, std_err = stats.linregress(slope_x, slope_y)
    print('  Intercept: {:.3f}, Slope: {:.4f}, R value: {:.3f}, p value: {}, Std Err: {}'.format(intercept, slope, r_value, p_value, std_err))
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

def ratings_difference_distributions(data_set_type):
    ctr = Counter()
    for report in MatchReport.all(data_set_type):
        ctr[abs(report.score)] += 1
    xs = []
    ys = []
    log_ys = []
    for x in sorted(ctr)[1:]:
        if ctr[x] < 10:
            continue
        xs.append(x)
        ys.append(ctr[x])
        log_ys.append(log(ctr[x]))
    plt.figure(1)
    plt.title('Number of matches per ratings difference')
    plt.xlabel('Difference in ratings')
    plt.ylabel('Number of matches')
    plt.plot(xs, ys)
    plt.savefig('{}/ratings_difference_distribution.png'.format(GRAPH_DIR), dpi=180)
    plt.figure(2)
    plt.title('Log of number of matches per ratings difference')
    plt.xlabel('Difference in ratings')
    plt.ylabel('Log of number of matches')
    plt.plot(xs, log_ys)
    plt.savefig('{}/log_ratings_difference_distribution.png'.format(GRAPH_DIR), dpi=180)

def best_rating_distribution(data_set_type):
    mincount = 5
    matches = MatchReport.all(data_set_type)
    ctr = Counter()
    for player in Player.rated_players(matches, mincount):
        if player.best_rating(mincount) < 100:
            for m in player.matches:
                if m.player_1 == player.player_id:
                    print(m.rating_1)
                else:
                    print(m.rating_2)
        ctr[player.best_rating(mincount)] += 1
    x = []
    y = []
    for k in sorted(ctr):
        x.append(k)
        y.append(ctr[k])
    plt.title('Distribution of players "best" ratings')
    plt.xlabel('"Best" Rating')
    plt.ylabel('Number of Players')
    plt.scatter(x, y, s=1)
    plt.savefig('{}/best_ratings_distribution.png'.format(GRAPH_DIR), dpi=180)

def player_rating_trajectories(data_set_type, mincount):
    matches = MatchReport.all(data_set_type)
    for player in [p for p in Player.rated_players(matches, mincount) if p.best_stdev(mincount) > 50]:
        plt.plot(player.ordered_ratings('timestamp'), alpha=.1, c='gray')
    plt.show()

def best_rating_by_number_of_matches(data_set_type):
    players = CachedPlayer.rated_players(data_set_type)
    num_ratings = defaultdict(lambda: [])
    for player in players:
        num_ratings[len(player.matches)].append(player.best_rating)
    for play_count in sorted(num_ratings):
        values = num_ratings[play_count]
        total = len(values)
        score = np.mean(values)
        for _ in range(total):
            slope_x.append(play_count)
            slope_y.append(score)
        # Eliminate data with minimal value from graph
        # .12 was chosen as cutoff to maximize reasonable data
        if lower_err < .2 and pct_win < 1 and total > 3:
            # Only plot every 5th record to make graph readable
            if not score % 5:
                x.append(score)
                y.append(pct_win)
                lower_yerr.append(lower_err)
                upper_yerr.append(upper_err)
    slope, intercept, r_value, p_value, std_err = stats.linregress(slope_x, slope_y)
    print('  Intercept: {:.3f}, Slope: {:.4f}, R value: {:.3f}, p value: {}, Std Err: {}'.format(intercept, slope, r_value, p_value, std_err))

    

if __name__ == '__main__':
    player_rating_trajectories('test', 5)
