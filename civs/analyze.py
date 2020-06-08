#!/usr/bin/env python

""" Exploration of data related to civ and map popularity. """
from collections import defaultdict, Counter
import csv
import json
import os
import pathlib
import random
import sys

import matplotlib.pyplot as plt
import numpy as np
import requests
from scipy import stats
from statsmodels.stats.proportion import proportion_confint

ROOT_DIR = str(pathlib.Path(__file__).parent.parent.absolute())

from utils.models import Match, Rating, User, MatchReport, Player, PlayerRating
import utils.download
import utils.lookup

def pct_win_by_code():
    constants = utils.lookup.constants()
    civs = constants['civ']
    maps = constants['map_type']
    civ_ctr = Counter()
    codes = defaultdict(lambda: {'total': 0, 'wins': 0})
    for report in MatchReport.all('model'):
        if report.mirror:
            continue
        civ_ctr[report.code] += 1
        codes[report.code]['total'] += 1
        if report.winner == 1:
            codes[report.code]['wins'] += 1
    x = []
    y = []
    yerr = []
    to_print = {}
    for code, _ in civ_ctr.most_common(100):
        wins = codes[code]['wins']
        total = codes[code]['total']
        if total < 10:
            continue
        cl, cu = proportion_confint(wins, total)
        if cl < .5 and cu > .5:
            continue
        if cl >= .5:
            c1, c2, m = [int(c) for c in code.split('-')]
            low = cl*100
            high = cu*100
        if cu <= .5:
            c2, c1, m = [int(c) for c in code.split('-')]
            low = (1 - cu)*100
            high = (1 - cl)*100
        to_print[low] = '{:>10} beat {:<12} on {:15} between {:.2f}% and {:.2f}%'.format(civs[c1], civs[c2], maps[m], low, high)

    for low in sorted(to_print, reverse=True):
        print(to_print[low])

def graph_sample():
    ctr = Counter()
    for report in MatchReport.by_map('test', 9):
        ctr[report.code] += 1
    x = []
    y = []
    for k, v in ctr.most_common(50):
        x.append(k)
        y.append(v)
    plt.bar(x, y)
    plt.xticks(x, rotation="vertical")
    plt.show()

def map_details():
    map_counter = Counter()
    for report in MatchReport.by_map('all', 9):
        map_counter[report.map] += 1
    for m, v in map_counter.most_common():
        print('{:20}: {:>7}'.format(m, v))

class CivInfo():
    def __init__(self, name, results):
        self.name = name
        self.n = len(results)
        if results:
            self.cl, self.cu = proportion_confint(sum(results), self.n, .1)
            self.mean = (self.cl + self.cu)/2
        else:
            self.cl = self.cu = self.mean = 0
        self.points = 0
        self.csv_mean = '{:.1f}'.format(self.mean * 100)

    def __str__(self):
        return '{:12} {:.2f} ({:>5})'.format(self.name, self.mean, self.n)

def mean_quantiles(civs, split):
    if split < 2:
        return []
    means = [civ.mean for civ in civs]
    pct = 1.0/split
    return [np.quantile(means, pct + pct*i) for i in range(split - 1)]

def graph_civ_by_map(data_set_type, map_type, split):
    constants = utils.lookup.constants()
    civ_names = constants['civ']
    civ_qs, edges = civ_by_quantiles(data_set_type, map_type, split)
    fig, axs = plt.subplots(nrows=len(civ_qs), ncols=1, sharex=True)
    hold = 0
    for idx, edge in enumerate(edges):
        civs = civ_qs[idx]
        ax = axs[idx]
        plot_dist(ax, civs, '{} - {}'.format(hold, edge - 1))
        hold = edge
    if split > 1:
        ax = axs[-1]
    else:
        ax = axs
    plot_dist(ax, civ_qs[-1], '{}+'.format(hold))
    fig.tight_layout(pad=0.3)
    plt.show()

def plot_dist(ax, civs, title):
    for mean in mean_quantiles(civs, 5):
        ax.axhline(mean)
    ax.set_title(title)
    x = []
    y = []
    yerr = []
    for civ in civs:
        x.append(civ.name)
        y.append(civ.mean)
        yerr.append(civ.mean - civ.cl)
    ax.errorbar(x, y, yerr=yerr, fmt='_')
    ax.set_xticklabels(x, rotation="vertical")

class MatchExperience():
    """ What happened in a match from a single player's point of view."""
    def __init__(self, rating, civ, enemy_civ, score, won):
        self.rating = rating
        self.civ = civ
        self.enemy_civ = enemy_civ
        self.score = score
        self.won = won
        if won:
            self.value = 1 - score*0.0011
        else:
            self.value = 0

def civs_by_snapshots(data_set_type, map_type, snapshot_count):
    # No mirrors
    matches = [match for match in MatchReport.by_map(data_set_type, map_type) if not match.mirror]
    experiences_raw = []
    for match in matches:
        experiences_raw.append(MatchExperience(match.rating_1, match.civ_1, match.civ_2, match.score, match.winner == 1))
        experiences_raw.append(MatchExperience(match.rating_2, match.civ_2, match.civ_1, match.score, match.winner == 2))
    experiences = sorted(experiences_raw, key=lambda x: x.rating)

    # Each match has two players, each of which will be counted somewhere
    total_records = len(experiences)
    # we want to advance a third of a snapshot for each record set, so...
    offset = int(total_records/(snapshot_count + 2))
    hold = 0
    civs = defaultdict(lambda: [])
    snapshots = []
    civ_names = set()
    row_header = ['Civilization']
    for _ in range(snapshot_count):
        rating_max = 0
        rating_min = 30000
        for experience in experiences[hold: offset*3 + hold]:
            rating_max = max(rating_max, experience.rating)
            rating_min = min(rating_min, experience.rating)
            civs[experience.civ].append(experience.value)
        hold += offset
        row_header.append('{} - {}'.format(rating_min, rating_max))
        civ_infos = defaultdict(lambda:CivInfo('', []))
        for name, results in civs.items():
            civ_names.add(name)
            civ_infos[name] = CivInfo(name, results)
        snapshots.append(civ_infos)
    rows = [row_header]
    for name in sorted(civ_names):
        row = [name]
        for snapshot in snapshots:
            row.append(snapshot[name].csv_mean)
        rows.append(row)
    with open('flourish.csv', 'w') as f:
        writer = csv.writer(f)
        writer.writerows(rows)

def flourish(data_set_type, map_type, split):
    civ_qs, edges = civ_by_quantiles(data_set_type, map_type, split)
    rows = []
    hold = 0
    header_row = ['Civilization']
    rows.append(header_row)
    for edge in edges:
        header_row.append('{} - {}'.format(hold, edge - 1))
        hold = edge
    header_row.append('{}+'.format(edges[-1]))
    civ_infos = defaultdict(lambda: [])
    for qs in civ_qs:
        for civ in qs:
            civ_infos[civ.name].append(civ.mean)
    for civ in sorted(civ_infos):
        row = [civ]
        for mean in civ_infos[civ]:
            row.append(mean)
        rows.append(row)
    with open('flourish.csv', 'w') as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    print(rows)

def civ_by_quantiles(data_set_type, map_type, split):
    quantile_civs = []
    hold = 0
    edges =  MatchReport.rating_edges(data_set_type, map_type, split)
    for edge in edges:
        quantile_civs.append(civ_ranks(MatchReport.by_map_and_rating(data_set_type, map_type, hold, edge), hold, edge))
        hold = edge
    quantile_civs.append(civ_ranks(MatchReport.by_map_and_rating(data_set_type, map_type, hold, 10000), hold, 10000))
    template = ' '.join(['{:26}' for _ in range(split)])
    if edges:
        print(template.format(*['< {}'.format(e) for e in edges], '{}+'.format(edges[-1])))
    for i in range(len(quantile_civs[0])):
        row = [str(civ_list[i]) for civ_list in quantile_civs]
        print(template.format(*row))
    return quantile_civs, edges

def civ_ranks(reports, lower, upper):
    civ_results = defaultdict(lambda: [])
    for report in reports:
        if report.mirror:
            continue
        if lower <= report.rating_1 < upper:
            if report.winner == 1:
                civ_results[report.civ_1].append(1 - 0.0011*report.score)
            elif report.winner == 2:
                civ_results[report.civ_1].append(0)
        if lower <= report.rating_2 < upper:
            if report.winner == 1:
                civ_results[report.civ_2].append(0)
            elif report.winner == 2:
                civ_results[report.civ_2].append(1 - 0.0011*report.score)
    civs = []
    for civ in sorted(civ_results):
        civs.append(CivInfo(civ, civ_results[civ]))
    for civ1 in civs:
        for civ2 in civs:
            if civ1.cl > civ2.cu:
                civ1.points += 1

    return sorted(civs, key=lambda x: x.name, reverse=False)

class CivChain():
    def __init__(self, name):
        self.name = name
        self.code = int(name)
        self.superiors = set()

def reciprocal_check(init, to_check, chain, chains, ccs):
    for superior in ccs[to_check].superiors:
        if superior == init:
            chains.append(chain)
        if superior not in chain:
            chain.append(superior)
            return reciprocal_check(init, superior, chain[:], chains, ccs)
    return chains

def victory_chains(reports):
    check_code = '5'
    constants = utils.lookup.constants()
    civ_names = constants['civ']
    civ_ctr = Counter()
    codes = defaultdict(lambda: {'total': 0, 'wins': 0.0})
    for report in reports:
        if report.mirror:
            continue
        civ_ctr[report.code] += 1
        codes[report.code]['total'] += 1
        if report.winner == 1:
            codes[report.code]['wins'] += max((1 - 0.0011*report.score), 0)
    ccs = {}
    for code, d in codes.items():
        c1, c2, _ = code.split('-')
        if not c1 in ccs:
            ccs[c1] = CivChain(c1)
        if not c2 in ccs:
            ccs[c2] = CivChain(c2)
        civ1 = ccs[c1]
        civ2 = ccs[c2]
        cl, cu = proportion_confint(min(d['wins'], d['total']), d['total'], 0.05)
        if cl > .5:
            civ2.superiors.add(c1)
            if c2 == check_code:
                print('Vs {:12} - cl: {:.2f}, cu: {:.2f} ({:>4})'.format(civ_names[civ1.code], 1 - cu, 1 - cl, d['total']))
        elif cu < .5:
            civ1.superiors.add(c2)
            if c1 == check_code:
                print('Vs {:12} - cl: {:.2f}, cu: {:.2f} ({:>4})'.format(civ_names[civ2.code], cl, cu, d['total']))
    for civ in ccs.values():
        try:
            print(reciprocal_check(civ.name, civ.name, [], [], ccs))
        except RuntimeError as e:
            print(e)

def map_popularity(data_set_type):
    matches = MatchReport.all(data_set_type)
    players = Player.player_values(matches)
    m = Counter()
    for player in players:
        for map_type in player.maps:
            m[map_type] += 1
    for k, v in m.most_common():
        print('{:>14}: {:>7}'.format(k, v))

class CivCluster:
    def __init__(self, base_civ):
        self.base_civ = base_civ
        self.mean = base_civ.mean
        self.civs = [base_civ]
        self.color = 'k'

    def maybe_add(self, other_civ):
        """ Adds civ to civs if should; returns if added """
        should_add = self.base_civ.cl < other_civ.mean < self.base_civ.cu
        if should_add:
            self.civs.append(other_civ)
        return should_add

def winning_clusters(data_set_type, map_type):
    reports = MatchReport.by_map(data_set_type, map_type)
    civ_infos_raw = civ_ranks(reports, 0, 10000)
    civ_clusters = []
    current_civ_cluster = None
    in_clusters = set()
    civ_infos = sorted(civ_infos_raw, key=lambda x: x.mean - x.cl)
    for civ_info in civ_infos:
        if civ_info in in_clusters:
            continue
        current_civ_cluster = CivCluster(civ_info)
        civ_clusters.append(current_civ_cluster)
        in_clusters.add(civ_info)
        for other_ci in civ_infos:
            if other_ci in in_clusters:
                continue
            added = current_civ_cluster.maybe_add(other_ci)
            if added:
                in_clusters.add(other_ci)
    x = []
    y = []
    yerr = []
    graph_colors = []
    colors = ['dimgray', 'brown', 'peru', 'darkorange', 'gold', 'olivedrab', 'limegreen', 'darkcyan', 'dodgerblue', 'mediumpurple', 'violet', 'deeppink', 'crimson',]
    random.shuffle(colors)
    for idx, cluster in enumerate(civ_clusters):
        cluster.color = colors[idx]
    civ_clusters_s = sorted(civ_clusters, key=lambda x : x.mean, reverse=True)
    print(len(civ_clusters))
    for civ_info in civ_infos_raw:
        for idx, cluster in enumerate(civ_clusters_s):
            if civ_info in cluster.civs:
                color = cluster.color
        graph_colors.append(color)
        x.append(civ_info.name)
        y.append(civ_info.mean)
        yerr.append(civ_info.mean - civ_info.cl)
    plt.scatter(x, y, c=graph_colors)
    plt.xticks(x, rotation="vertical")
    plt.show()
def wtvr():
    reports = MatchReport.by_map_and_rating('all', 29, 1200, 100000)
    victory_chains(reports)

def maps_per_player(matches):
    mctr = Counter()
    for player in Player.player_values(matches):
        pms = [m.map for m in player.matches]
        mctr[len(set(pms))] += 1
    for k in sorted(mctr):
        print('{:>3}: {:>6}'.format(k, mctr[k]))
def bucket_edges(rating):
    for i in range(rating - 100, rating):
        if not i % 50:
            return i, i + 100, i + 50, i + 150
def min_max_rating_per_map(data_set_type):
    matches = MatchReport.all(data_set_type)
    map_data = defaultdict(lambda: Counter())
    rating_lookup = PlayerRating.ratings_for(data_set_type)
    players = [p for p in Player.player_values(matches) if p.player_id in rating_lookup]
    for player in players:
        bottom_1, top_1, bottom_2, top_2 = bucket_edges(rating_lookup[player.player_id])
        for match in player.matches:
            if match.player_1 == player.player_id:
                if bottom_1 < match.rating_1 <= top_1:
                    map_data[match.map][bottom_2] += 1
                if bottom_2 < match.rating_1 <= top_2:
                    map_data[match.map][bottom_2] += 1
            elif match.player_2 == player.player_id:
                if bottom_1 < match.rating_2 <= top_1:
                    map_data[match.map][bottom_2] += 1
                if bottom_2 < match.rating_2 <= top_2:
                    map_data[match.map][bottom_2] += 1
    for map_name, counter in map_data.items():
        bottom = None
        top = None
        for k in sorted(counter):
            if counter[k] > 99:
                if not bottom:
                    bottom = '{:>5}: ({:5})'.format(k, counter[k])
                top = '{:>5}: ({:5})'.format(k, counter[k])
        print('{:18}: {} - {}'.format(map_name, bottom, top))

    
if __name__ == '__main__':
    min_max_rating_per_map('model')
    # for i in range(188, 304):
    #     print('{:>3}: {:>3}-{:>3}, {:>3}-{:>3}'.format(i, *bucket_edges(i)))
