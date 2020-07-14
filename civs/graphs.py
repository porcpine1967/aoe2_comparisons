#!/usr/bin/env

""" Creates graphs of civ popularity. """
import argparse
from collections import defaultdict, Counter
import csv
from math import sqrt
import pathlib
import pickle
import os

import matplotlib.pyplot as plt

from utils.lookup import CIVILIZATIONS

CACHED_TEMPLATE = '{}/cached_civ_popularity_map_for_{}.pickle'

import utils.solo_models
import utils.team_models

MAP_ORDER = [
    'Steppe',
    'Mountain Pass',
    'Scandinavia',
    'Oasis',
    'Wolf Hill',
    'Hill Fort',
    'Hideout',
    'Arena',
    'Black Forest',
    'Golden Pit',
    'Gold Rush',
    'All Maps',
    'Acropolis',
    'Arabia',
    'Serengeti',
    'Kilimanjaro',
    'MegaRandom',
    'Four Lakes',
    'Golden Swamp',
    'Lombardia',
    'Alpine Lakes',
    'Nomad',
    'Bog Islands',
    'Mediterranean',
    'Continental',
    'Team Islands',
    'Islands',
]

def default_ranking():
    return 35
def default_popularity():
    return 0

def to_heatmap_table(data, xlabels, ylabels, row_label_header, normalize):
    """ Formats data into an html table with heatmap colors. Returns a string
    data: 2-dimensional array of heatmap number (0.0-1.0) and text
    xlabels: labels for headers
    ylabels: labels for rows. """

    html_rows = ['<table>',]
    # Add header
    html_rows.append(''.join(['<tr><th>{}</th>'.format(row_label_header)] + ['<th class="xlabel">{}</th>'.format(l) for l in xlabels] + ['</tr>']))
    # Rows
    for idx, row in enumerate(data):
        html_rows.append(to_heatmap_row(row, ylabels[idx], normalize))
    html_rows.append('</table>')
    return '\n'.join(html_rows)

def to_heatmap_row(row, ylabel, normalize):
    row_info = ['<tr><td class="ylabel">{}</td>'.format(ylabel),]
    for heatmap, value in row:
        row_info.append('<td class="data" style="background-color: hsl({}, 100%, 60%)">{}</td>'.format((1 - normalize(heatmap))*240, value))
    row_info.append('</tr>')
    return ''.join(row_info)

class CachedCiv:
    """ To avoid serialization problems, same as civ but no functions. """
    def __init__(self, civ):
        self.name = civ.name
        self.rankings = civ.rankings
        self.popularity = civ.popularity
        self.win_rates = civ.win_rates
        self.win_rate_rankings = civ.win_rate_rankings
        self.totals = civ.totals

    @property
    def civ(self):
        civ = Civ(self.name)
        civ.rankings = self.rankings
        civ.popularity = self.popularity
        civ.win_rates = self.win_rates
        civ.win_rate_rankings = self.win_rate_rankings
        civ.totals = self.totals
        return civ

class Rankable:
    """ Derived supercalss from Civ so get similar functionality for Map."""
    def __init__(self, name):
        self.name = name
        self.rankings = defaultdict(default_ranking)
        self.popularity = defaultdict(default_popularity)
        self.totals = defaultdict(default_popularity)
        self.win_rates = defaultdict(default_popularity)
        self.win_rate_rankings = defaultdict(default_ranking)

class Rating(Rankable):
    """ Simple object for holding rankable data for ratings."""
    pass
class Map(Rankable):
    """ Simple object for holding rankable data for maps. """
    pass

class Civ(Rankable):
    """ Holds rankable data for a civ. """
    def print_info(self, maps_with_data, rating_keys):
        mt_array = ['{:18}', '{:^9s}'] + ['{:^9s}' for _ in rating_keys]
        map_template = ' '.join(mt_array)

        print('*'*(len(self.name)))
        print(self.name)
        print('*'*(len(self.name)))
        print('Overall:', self.rankings['Overall'])
        print(map_template.format('Map Name', 'Overall', *[rk for rk in rating_keys]))
        print(map_template.format('All', str(round(self.popularity['Overall'], 2)), *[str(round(self.popularity[rk], 2)) for rk in rating_keys]))
        for map_name in sorted(maps_with_data):
            print(map_template.format(map_name, str(round(self.rankings[map_name], 3)), *[str(round(self.rankings['{}-{}'.format(map_name,rk)], 3)) for rk in rating_keys]))
            print(map_template.format(map_name, str(round(self.popularity[map_name], 3)), *[str(round(self.popularity['{}-{}'.format(map_name,rk)], 3)) for rk in rating_keys]))
    def map_x_rating_heatmap_table(self, maps, rating_keys, normalize):
        html = ['\n<h3>{}</h3>'.format(self.name)]
        map_dict = {}

        xlabels = rating_keys
        ylabels = []
        data = []
        for map_name in sorted(set(maps), key=lambda x: MAP_ORDER.index(x)):
            ylabels.append(map_name)
            data.append([(self.popularity['{}-{}'.format(map_name, rk)], self.rankings['{}-{}'.format(map_name, rk)],) for rk in rating_keys])
        html.append(to_heatmap_table(data, xlabels, ylabels, 'Map Name', normalize))
        return '\n'.join(html)

    def heatmap_rating_data(self, map_name, rating_keys):
        if map_name == 'all':
            row = [(self.popularity[rk],
                    self.rankings[rk]) for rk in rating_keys]
        else:
            row = [(self.popularity['{}-{}'.format(map_name, rk)],
                    self.rankings['{}-{}'.format(map_name, rk)]) for rk in rating_keys]
        return row

def civ_popularity_counters_for_map_bucketed_by_rating(players, map_name, edges):
    """ Returns an array of counters, each of which represents the cumulative proportional popularity of a civilization
    for every rated player for matches played when holding a rating between the edges. Note, a player is only checked
    if the player's "best rating" falls within the edges.
    players: the list of players to evaluate
    map_name: which map to build the counters for. 'all' will ignore map as a filter
    edges: an array of edges in which to delineate ratings. First edge should be greater than zero, so first "bucket"
    will be from 1 to edges[0], second edge from edges[0] to edges[1], finishing at edges[-2] to edges[-1]."""
    print('calculating civ_popularity_counters_for_map_bucketed_by_rating for map {} for {} edges'.format(map_name, len(edges)))
    start = 0
    counters = []
    for edge in edges:
        civ_ctr = Counter()
        counters.append(civ_ctr)
        snapshot_players = [p for p in players if start < p.best_rating() <= edge]
        for player in snapshot_players:
            player.add_civ_percentages(civ_ctr, map_name, start, edge)
        start = edge - 50
    return counters

def civ_winrate_counters_for_map_bucketed_by_rating(players, map_name, edges):
    """ Returns an array of tuples, each of which represents the winrate of a civilization
    for every rated player for matches played when holding a rating between the edges. Note, a player is only checked
    if the player's "best rating" falls within the edges.
    players: the list of players to evaluate
    map_name: which map to build the counters for. 'all' will ignore map as a filter
    edges: an array of edges in which to delineate ratings. First edge should be greater than zero, so first "bucket"
    will be from 1 to edges[0], second edge from edges[0] to edges[1], finishing at edges[-2] to edges[-1]."""
    print('calculating civ_winrate_counters_for_map_bucketed_by_rating for map {} for {} edges'.format(map_name, len(edges)))
    start = 0
    counters = []
    for edge in edges:
        win_ctr = Counter()
        total_ctr = Counter()
        snapshot_players = [p for p in players if start < p.best_rating() <= edge]
        for player in snapshot_players:
            player.add_win_percentages(win_ctr, total_ctr, map_name, start, edge)
        civ_ctr = Counter()
        counters.append(civ_ctr)
        for civ_name in total_ctr:
            civ_ctr[civ_name] = win_ctr[civ_name]/total_ctr[civ_name]
        start = edge - 50
    return counters

def loaded_civs(data_set_type, module, players=None):
    """ Calculates civ popularities overall, by map, by rating bucket, and by map-rating combination.
    returns civs, the maps that have data, and the rating keys available in the civs."""
    print('loading civs for', data_set_type)
    # Setup
    civs = {}
    for k in CIVILIZATIONS:
        civs[k] = Civ(k)
    edges = [i for i in range(650, 1701, 50)]
    start = 0
    rating_keys = []
    for edge in edges:
        rating_keys.append('{}-{}'.format(start + 1, edge))
        start = edge - 50
    rating_keys.append('{}+'.format(edges[-1] - 49))
    edges.append(10000)
    if not players:
        print('building players')
        players = [p for p in module.Player.player_values(module.MatchReport.all(data_set_type), data_set_type) if p.best_rating()]

    # Calculate overall popularity
    for ctr in civ_popularity_counters_for_map_bucketed_by_rating(players, 'all', [10000]):
        total = sum(ctr.values())
        for idx, civ in enumerate(sorted(ctr, key=lambda x: ctr[x], reverse=True)):
            civs[civ].rankings['Overall'] = idx + 1
            civs[civ].popularity['Overall'] = ctr[civ]/total
            civs[civ].totals['Overall'] = total
    # Calculate overall win rate
    for ctr in civ_winrate_counters_for_map_bucketed_by_rating(players, 'all', [10000]):
        for idx, civ in enumerate(sorted(ctr, key=lambda x: ctr[x], reverse=True)):
            civs[civ].win_rate_rankings['Overall'] = idx + 1
            civs[civ].win_rates['Overall'] = ctr[civ]

    # Calculate overall popularity per rating bucket
    for ctr_idx, ctr in enumerate(civ_popularity_counters_for_map_bucketed_by_rating(players, 'all', edges)):
        total = sum(ctr.values())
        for idx, civ in enumerate(sorted(ctr, key=lambda x: ctr[x], reverse=True)):
            civs[civ].rankings[rating_keys[ctr_idx]] = idx + 1
            civs[civ].popularity[rating_keys[ctr_idx]] = ctr[civ]/total
            civs[civ].totals[rating_keys[ctr_idx]] = total

    # Calculate overall win rate per rating bucket
    for ctr_idx, ctr in enumerate(civ_winrate_counters_for_map_bucketed_by_rating(players, 'all', edges)):
        for idx, civ in enumerate(sorted(ctr, key=lambda x: ctr[x], reverse=True)):
            civs[civ].win_rate_rankings[rating_keys[ctr_idx]] = idx + 1
            civs[civ].win_rates[rating_keys[ctr_idx]] = ctr[civ]

    # Calculate overall popularity by map
    maps_with_data = []
    for map_name in module.MAPS:
        for ctr in civ_popularity_counters_for_map_bucketed_by_rating(players, map_name, [10000]):
            if ctr:
                maps_with_data.append(map_name)
                total = sum(ctr.values())
            for idx, civ in enumerate(sorted(ctr, key=lambda x: ctr[x], reverse=True)):
                civs[civ].rankings[map_name] = idx + 1
                civs[civ].popularity[map_name] = ctr[civ]/total
                civs[civ].totals[map_name] = total

    # Calculate overall win rate by map
    for map_name in maps_with_data:
        for ctr in civ_winrate_counters_for_map_bucketed_by_rating(players, map_name, [10000]):
            for idx, civ in enumerate(sorted(ctr, key=lambda x: ctr[x], reverse=True)):
                civs[civ].win_rate_rankings[map_name] = idx + 1
                civs[civ].win_rates[map_name] = ctr[civ]

    # Calculate overall popularity by map by rating bucket
    for map_name in maps_with_data:
        for ctr_idx, ctr in enumerate(civ_popularity_counters_for_map_bucketed_by_rating(players, map_name, edges)):
            total = sum(ctr.values())
            for idx, civ in enumerate(sorted(ctr, key=lambda x: ctr[x], reverse=True)):
                civs[civ].rankings['{}-{}'.format(map_name, rating_keys[ctr_idx])] = idx + 1
                civs[civ].popularity['{}-{}'.format(map_name, rating_keys[ctr_idx])] = ctr[civ]/total
                civs[civ].totals['{}-{}'.format(map_name, rating_keys[ctr_idx])] = total

    # Calculate overall win rate by map by rating bucket
    for map_name in maps_with_data:
        for ctr_idx, ctr in enumerate(civ_winrate_counters_for_map_bucketed_by_rating(players, map_name, edges)):
            for idx, civ in enumerate(sorted(ctr, key=lambda x: ctr[x], reverse=True)):
                civs[civ].win_rate_rankings['{}-{}'.format(map_name, rating_keys[ctr_idx])] = idx + 1
                civs[civ].win_rates['{}-{}'.format(map_name, rating_keys[ctr_idx])] = ctr[civ]

    return civs, maps_with_data, rating_keys

def civs_x_maps_heatmap_table(civs, maps):
    """ Returns a single heatmap html table of civs x maps """
    # Build data arrays
    civ_names = [civ.name for civ in sorted(civs.values(), key=lambda x: x.rankings['Overall'])]
    map_dict = {}
    header_row = civ_names
    civ_popularities = []
    for map_name in maps:
        row = []
        map_dict[map_name] = row
        for civ_name in civ_names:
            civ = civs[civ_name]
            row.append((civ.popularity[map_name], civ.rankings[map_name],))
            civ_popularities.append(civ.popularity[map_name])
    max_value = sorted(civ_popularities, reverse=True)[len(maps)-1]
    def normalize(x):
        if x == 0: return x
        if x > max_value: return 1
        return x/max_value

    # Format data as rows of html in proper order
    html_rows = ['<h2>Overall Popularity of Civs per Map</h2>',]
    xlabels = civ_names
    ylabels = []
    data = []
    for map_name in sorted(map_dict, key=lambda x: MAP_ORDER.index(x)):
        ylabels.append(map_name)
        data.append(map_dict[map_name])
    html_rows.append(to_heatmap_table(data, xlabels, ylabels, 'Map Name', normalize))
    return '\n'.join(html_rows)

def civs_x_maps_heatmap_tables_per_rating_bucket(civs, maps, rating_keys):
    """ Returns a set of heatmap html tables of civs x maps, one table for every rating bucket."""
    html_rows = ['<h2>Popularity of Civs on Maps by Rating</h2>',]
    civ_names = [civ.name for civ in sorted(civs.values(), key=lambda x: x.rankings['Overall'])]
    for rk in rating_keys:
        map_dict = {}
        header_row = civ_names
        civ_popularities = []
        for map_name in maps:
            row = []
            map_dict[map_name] = row
            for civ_name in civ_names:
                civ = civs[civ_name]
                row.append((civ.popularity['{}-{}'.format(map_name, rk)], civ.rankings['{}-{}'.format(map_name, rk)],))
                civ_popularities.append(civ.popularity['{}-{}'.format(map_name, rk)])
        max_value = sorted(civ_popularities, reverse=True)[len(civs) - 1]
        def normalize(x):
            if x == 0: return x
            if x > max_value:
                return 1
            return x/max_value

        # Format data as rows of html in proper order
        html_rows.append('<h3>Popularity of Civs per Map for {}</h3>'.format(rk))
        xlabels = civ_names
        ylabels = []
        data = []
        for map_name in sorted(map_dict, key=lambda x: MAP_ORDER.index(x)):
            ylabels.append(map_name)
            data.append(map_dict[map_name])
        html_rows.append(to_heatmap_table(data, xlabels, ylabels, 'Map Name', normalize))
    return '\n'.join(html_rows)

def write_civs_x_maps_heatmaps_to_html(civs, maps, rating_keys, module):
    """ Generates html representation of each rating's popularity by map and civ. """
    with open('{}/rating_popularity_data.html'.format(module.GRAPH_DIR), 'w') as f:
        f.write("""<!doctype html>

<html lang="en">
<head>
  <meta charset="utf-8">

  <title>Civilization Popularity per Rating Segmented by Map</title>
  <meta name="description" content="AOE2 info">
  <meta name="author" content="porcpine1967">
  <link rel="stylesheet" href="../styles/normalize.css">
  <style>
      body {margin: 5em}
      th.xlabel { font-size: 6pt; padding: 0; width: 2.5em}
      td.data { text-align: center; width: 2.5em}
  </style>
</head>
<body>
""")
        f.write(civs_x_maps_heatmap_table(civs, maps))
        f.write(civs_x_maps_heatmap_tables_per_rating_bucket(civs, maps, rating_keys))

def write_maps_x_ratings_heatmaps_to_html(civs, maps, rating_keys, data_set_type, module):
    """ Generates html representation of each civ's popularity by map and rating. """
    with open('{}/civ_popularity_data.html'.format(module.GRAPH_DIR), 'w') as f:
        f.write("""<!doctype html>

<html lang="en">
<head>
  <meta charset="utf-8">

  <title>Civilization Rankings per Map Segmented by Rating</title>
  <meta name="description" content="AOE2 info">
  <meta name="author" content="porcpine1967">
  <link rel="stylesheet" href="../styles/normalize.css">
  <style>
      body {margin: 5em}
      td.ylabel { width: 7em; }
      td.data { text-align: center; }
      th { width: 4em; }
  </style>
</head>
<body>
""")
        f.write(all_civs_map_x_rating_heatmap_table(module, data_set_type, rating_keys))
        civ_popularities = [civ.popularity['{}-{}'.format(map_name, rk)] for rk in rating_keys for civ in civs.values() for map_name in maps]
        max_value = sorted(civ_popularities, reverse=True)[len(rating_keys)*len(civs)-1]
        def normalize(x):
            if max_value == 0:
                return 0
            if x > max_value:
                return 1
            return x/max_value

        f.write('<h2>Popularity of Each Civ Segmented by Map and Ranking</h2>')
        for civ in sorted(civs.values(), key=lambda x: x.rankings['Overall']):
            f.write(civ.map_x_rating_heatmap_table(maps, rating_keys, normalize))

def civs_x_ratings_heatmap_table(civs, rating_keys, civ_names):
    civ_popularities = [civ.popularity[rk] for rk in rating_keys for civ in civs.values()]
    max_value = sorted(civ_popularities, reverse=True)[len(rating_keys)-1]
    def normalize(x):
        if max_value == 0:
            return 0
        if x > max_value:
            return 1
        return x/max_value
    data = []
    for civ_name in civ_names:
        data.append(civs[civ_name].heatmap_rating_data('all', rating_keys))
    return to_heatmap_table(data, rating_keys, civ_names, 'Civilization', normalize)

def civs_x_ratings_heatmap_tables_per_map(civs, map_name, rating_keys, civ_names):
    civ_popularities = [civ.popularity['{}-{}'.format(map_name, rk)] for rk in rating_keys for civ in civs.values()]
    max_value = sorted(civ_popularities, reverse=True)[len(rating_keys)-1]
    def normalize(x):
        if max_value == 0:
            return 0
        if x > max_value:
            return 1
        return x/max_value
    data = []
    for civ_name in civ_names:
        data.append(civs[civ_name].heatmap_rating_data(map_name, rating_keys))
    return to_heatmap_table(data, rating_keys, civ_names, 'Civilization', normalize)

def write_civs_x_ratings_heatmaps_to_html(civs, maps, rating_keys, module):
    """ Generates html representation of each map's civ popularity by rating. """
    with open('{}/map_popularity_data.html'.format(module.GRAPH_DIR), 'w') as f:
        f.write("""<!doctype html>

<html lang="en">
<head>
  <meta charset="utf-8">

  <title>Civilization Rankings per Rating for Each Map</title>
  <meta name="description" content="AOE2 info">
  <meta name="author" content="porcpine1967">
  <link rel="stylesheet" href="../styles/normalize.css">
  <style>
      body {margin: 5em}
      td.data { text-align: center; }
      th { width: 4em; }
  </style>
</head>
<body>
""")
        f.write('<h2>Popularity of Each Civ by Rating per Map</h2>\n')
        civ_names = [civ.name for civ in sorted(civs.values(), key=lambda x: x.rankings['Overall'])]
        total_civ = list(civs.values())[0]
        total = int(sum([total_civ.totals[rk] for rk in rating_keys]))
        f.write('<h3>All Maps (n={:,})</h3>\n'.format(total))
        f.write(civs_x_ratings_heatmap_table(civs, rating_keys, civ_names))
        for map_name in sorted(maps, key=lambda x: total_civ.totals[x], reverse=True):
            total = int(sum([total_civ.totals['{}-{}'.format(map_name, rk)] for rk in rating_keys]))
            f.write('\n<h3>{} (n={:,})</h3>\n'.format(map_name, total))
            f.write(civs_x_ratings_heatmap_tables_per_map(civs, map_name, rating_keys, civ_names))

class Similarity:
    def __init__(self, map_name, similarity_rating):
        self.map_name = map_name
        self.similarity_rating = similarity_rating
def map_similarity(civs, maps_with_data, rating_keys):
    """ Determines per civ which maps are similar to each other in terms of relative popularity. """
    def minus(l):
        return abs(l[0] - l[1])
    max_similarity = 0
    civ_similars = {}
    for civ_name, civ in civs.items():
        most_similars = {}
        civ_similars[civ_name] = most_similars
        map_data_lookup = {'All Maps': [civ.popularity[rk] for rk in rating_keys]}
        for map_name in maps_with_data:
            most_similar = None
            similarity_rating = 10000
            try:
                map_data = map_data_lookup[map_name]
            except KeyError:
                map_data = [civ.popularity['{}-{}'.format(map_name, rk)] for rk in rating_keys]
                map_data_lookup[map_name] = map_data
            for map_to_check in maps_with_data:
                if map_name == map_to_check:
                    continue
                try:
                    check_map_data = map_data_lookup[map_to_check]
                except KeyError:
                    check_map_data = [civ.popularity['{}-{}'.format(map_to_check, rk)] for rk in rating_keys]
                    map_data_lookup[map_to_check] = check_map_data

                map_diff = sum(map(minus, zip(map_data, check_map_data)))

                if map_diff < similarity_rating:
                    similarity_rating = map_diff
                    most_similar = Similarity(map_to_check, similarity_rating)
            most_similars[map_name] = most_similar
            max_similarity = max(max_similarity, most_similar.similarity_rating)
    best_match = {}
    for map_name in maps_with_data:
        similarity_ctr = Counter()
        for similars in civ_similars.values():
            similar = similars[map_name]
            similarity_ctr[similar.map_name] += (max_similarity - similar.similarity_rating)
        best_match[map_name] = similarity_ctr.most_common(2)
    print('{:15}  {:7} {:15}  {:7}  {}'.format('Best Match', 'Score', 'Next Best', 'Score', 'Map'))
    for map_name, match in best_match.items():
        print('{1[0][0]:15} ({1[0][1]:6.2f})  {1[1][0]:15} ({1[1][1]:5.2f}) - {0:15}'.format(map_name, match))

def cache_results(data_set_type, module):
    """ Pickles results so can do analysis without rerunning everything."""
    civs, maps_with_data, rating_keys = loaded_civs(data_set_type, module)
    with open(CACHED_TEMPLATE.format(module.DATA_DIR, data_set_type), 'wb') as f:
        pickle.dump([[CachedCiv(civ) for civ in civs.values()], maps_with_data, rating_keys], f)

def cached_results(data_set_type, module):
    """ Returns pickled results. Will generate pickle if not present. """
    cache_file = CACHED_TEMPLATE.format(module.DATA_DIR, data_set_type)
    if not os.path.exists(cache_file):
        cache_results(data_set_type, module)
    with open(cache_file, 'rb') as f:
        cached_civs, maps_with_data, rating_keys = pickle.load(f)
        civs = {}
        for cc in cached_civs:
            civs[cc.name] = cc.civ
    return civs, maps_with_data, rating_keys

def heatmap_key_table(mapping):
    """ html table of color grades of a given mapping. Assumes keys of map are .3f """
    data = []
    xlabels = ('Color',)
    ylabels = []
    for i in range(0, 241, 30):
        top = -1
        for k in sorted(mapping, reverse=True):
            hue = (1 - mapping[k]) * 240
            if hue > i - 1 and top < 0:
                top = k
                data.append(((mapping[top], '',),))
                ylabels.append('{:.3f}'.format(top))
            if hue > i + 30:
                break
    return to_heatmap_table(data, xlabels, ylabels, 'Popularity')

def map_popularity_counters_bucketed_by_rating(players, edges):
    """ Returns an array of counters, each of which represents the cumulative proportional popularity of a map
    for every rated player for matches played when holding a rating between the edges. Note, a player is only checked
    if the player's "best rating" falls within the edges.
    players: the list of players to evaluate
    edges: an array of edges in which to delineate ratings. First edge should be greater than zero, so first "bucket"
    will be from 1 to edges[0], second edge from edges[0] to edges[1], finishing at edges[-2] to edges[-1]."""
    start = 0
    counters = []
    for edge in edges:
        map_ctr = Counter()
        counters.append(map_ctr)
        snapshot_players = [p for p in players if start < p.best_rating() <= edge]
        for player in snapshot_players:
            player.add_map_percentages(map_ctr, start, edge)
        start = edge - 50
    return counters

def all_civs_map_x_rating_heatmap_table(module, data_set_type, viz_rating_keys=None):
    """ Returns a single heatmap html table of maps x ratings """
    maps = {}
    for k in module.MAPS:
        maps[k] = Map(k)
    edges = [i for i in range(650, 1701, 50)]
    start = 0
    rating_keys = []
    for edge in edges:
        rating_keys.append('{}-{}'.format(start + 1, edge))
        start = edge - 50
    rating_keys.append('{}+'.format(edges[-1] - 49))
    if not viz_rating_keys:
        viz_rating_keys = rating_keys
    edges.append(10000)
    players = [p for p in module.Player.player_values(module.MatchReport.all(data_set_type), data_set_type) if p.best_rating()]
    for ctr_idx, ctr in enumerate(map_popularity_counters_bucketed_by_rating(players, edges)):
        total = sum(ctr.values())
        for idx, map_name in enumerate(sorted(ctr, key=lambda x: ctr[x], reverse=True)):
            if not map_name in maps:
                continue
            maps[map_name].rankings[rating_keys[ctr_idx]] = idx + 1
            maps[map_name].popularity[rating_keys[ctr_idx]] = ctr[map_name]/total
    modifier = max([v for m in maps.values() for v in m.popularity.values()])
    html = ['<h3>Overall Popularity of Maps per Rating</h3>',]
    xlabels = viz_rating_keys
    ylabels = []
    data = []
    for map_name in sorted(maps, key=lambda x: MAP_ORDER.index(x)):
        ylabels.append(map_name)
        map_data = maps[map_name]
        data.append([(map_data.popularity[rk]/modifier, map_data.rankings[rk],) for rk in viz_rating_keys])
    html.append(to_heatmap_table(data, xlabels, ylabels, 'Map Name', lambda x: x))
    return '\n'.join(html)

def rebuild_cache(module):
    """ For use after resampling data (elo.sample). """
    for data_set_type in ('test', 'model', 'verification',):
        print('making player rating cache for', data_set_type)
#        module.Player.cache_player_ratings(data_set_type)
        cache_results(data_set_type, module)

def base_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('klass', choices=('team', 'solo', 'all',), help="team, solo, or all")
    parser.add_argument('--source', default='model', choices=('test', 'model', 'verification',), help="which data set type to use (default model)")
    parser.add_argument('--rebuild', action='store_true', help="Rebuild cache")
    args = parser.parse_args()
    if args.klass == 'team':
        modules = (utils.team_models,)
    elif args.klass == 'solo':
        modules = (utils.solo_models,)
    elif args.klass == 'all':
        modules = (utils.solo_models, utils.team_models,)
    return modules, args.source, args.rebuild

def runner(fun):
    """ Runs a function with civs, maps_with_data, and rating_keys as arguments. """
    modules, data_set_type, rebuild = base_args()
    for module in modules:
        if rebuild:
            rebuild_cache(module)
        civs, maps_with_data, rating_keys = cached_results(data_set_type, module)
        fun(module, data_set_type, civs, maps_with_data, rating_keys)

def write_all(module, data_set_type, civs, maps_with_data, rating_keys):
    """ Write out all the tables to all the files. """
    half_keys = [k for i, k in enumerate(rating_keys) if not i % 2]
    write_maps_x_ratings_heatmaps_to_html(civs, maps_with_data, half_keys, data_set_type, module)
    write_civs_x_maps_heatmaps_to_html(civs, maps_with_data, half_keys, module)
    write_civs_x_ratings_heatmaps_to_html(civs, maps_with_data, half_keys, module)

def cdfs(module, data_set_type, civs, maps, rating_keys):
    print(module.as_str())
    half_keys = [k for i, k in enumerate(rating_keys) if not i % 2]
    kt = '{}-{}'
    ratings_a = {}
    ratings_b = {}
    rating_a_civmap_totals = defaultdict(default_popularity)
    rating_b_civmap_totals = defaultdict(default_popularity)
    civmap_keys = set()
    for rk in half_keys:
        ratings_a[rk] = Rating(rk)
        ratings_b[rk] = Rating(rk)
    for civ_name, civ in civs.items():
        for rk in half_keys:
            rating = ratings_a[rk]
            rating.rankings[civ_name] = civ.rankings[rk]
            rating.popularity[civ_name] = civ.popularity[rk]
            rating.totals[civ_name] = civ.popularity[rk]*civ.totals[rk]
            for map_name in maps:
                key = kt.format(map_name, rk)
                cm_key = kt.format(civ_name, map_name)
                playcounts = civ.popularity[key]*civ.totals[key]
                rating.totals[cm_key] = playcounts
                rating_a_civmap_totals[rk] += playcounts

                ratings_b[rk].popularity[cm_key] = civ.popularity[key]
                rating_b_civmap_totals[rk] += civ.popularity[key]
                civmap_keys.add(cm_key)

    print('Overall Civs ({})'.format(len(civs)))
    for rk, rating in ratings_a.items():
        data = []
        rt = 0
        for popularity_key in sorted(civs, key=lambda x: rating.popularity[x], reverse=True):
            rt += rating.popularity[popularity_key]
            data.append(rt)
        print_cdf(rk, data, len(civs))

    print('Weighted Maps ({})'.format(len(civmap_keys)))
    for rk, rating in ratings_a.items():
        data = []
        rt = 0
        for popularity_key in sorted(civmap_keys, key=lambda x: rating.totals[x], reverse=True):
            rt += rating.totals[popularity_key]/rating_a_civmap_totals[rk]
            data.append(rt)
        print_cdf(rk, data, len(civmap_keys))

    print('Equal Maps ({})'.format(len(civmap_keys)))
    for rk, rating in ratings_b.items():
        data = []
        rt = 0
        for popularity_key in sorted(civmap_keys, key=lambda x: rating.popularity[x], reverse=True):
            rt += rating.popularity[popularity_key]/rating_b_civmap_totals[rk]
            data.append(rt)
        print_cdf(rk, data, len(civmap_keys))

def print_cdf(rk, data, t):
    for idx, d in enumerate(data):
        if d > 0.5:
            count = idx + d - 0.5
            print('{:>9} {:>4} ({:>4}%)'.format(rk, idx, round(100*count/t, 1)))
            break

def winrates(module, data_set_type, civs, maps_with_data, rating_keys):
    half_keys = [k for i, k in enumerate(rating_keys) if not i % 2]
    print('Arena')
    key = 'Arena'
    for civ_name in sorted(civs, key=lambda x: civs[x].win_rate_rankings[key]):
        civ = civs[civ_name]
        print(' {:15}: {:.2f} ({:>4})'.format(civ_name, civ.win_rates[key], round(civ.popularity[key]*civ.totals[key])))
    for rk in half_keys:
        key = 'Arena-{}'.format(rk)
        print('{} ({})'.format(rk, round(civ.totals[key])))
        for civ_name in sorted(civs, key=lambda x: civs[x].win_rate_rankings[key]):
            civ = civs[civ_name]
            print(' {:15}: {:.2f} ({:>4})'.format(civ_name, civ.win_rates[key], round(civ.popularity[key]*civ.totals[key])))

def runner(fun):
    """ Runs a function with civs, maps_with_data, and rating_keys as arguments. """
    modules, data_set_type = base_args()
    for module in modules:
        civs, maps_with_data, rating_keys = cached_results(data_set_type, module)
        fun(module, data_set_type, civs, maps_with_data, rating_keys)

def run():
    runner(winrates)

if __name__ == '__main__':
    run()
