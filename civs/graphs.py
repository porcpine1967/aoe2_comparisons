#!/usr/bin/env

""" Creates graphs of civ popularity. """
from collections import defaultdict, Counter
import csv
from math import sqrt
import pathlib
import pickle
import os

import matplotlib.pyplot as plt

from civs.flourish import CIVILIZATIONS
ROOT_DIR = str(pathlib.Path(__file__).parent.parent.absolute())

CACHED_TEMPLATE = '{}/team-data/cached_civ_popularity_map_for_{{}}.pickle'.format(ROOT_DIR)

from utils.models import MatchReport, CachedPlayer, PlayerRating

MAPS = [
    'Arabia',
    'Arena',
    'MegaRandom',
    'Nomad',
    'Hideout',
    'Lombardia',
    'Black Forest',
    'Scandinavia',
    'Golden Swamp',
    'Hill Fort',
    'Oasis',
    'Gold Rush',
    'Steppe',
    'Team Islands',
    'Golden Pit',
    'Mediterranean',
    'Wolf Hill',
]
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
        self.totals = civ.totals

class Rankable:
    """ Derived supercalss from Civ so get similar functionality for Map."""
    def __init__(self, name):
        self.name = name
        self.rankings = defaultdict(default_ranking)
        self.popularity = defaultdict(default_popularity)
        self.totals = defaultdict(default_popularity)

class Map(Rankable):
    """ Simple object for holding rankable data for maps. """
    pass

class Civ(Rankable):
    """ Holds rankable data for a civ. """
    def from_cache(cached_civ):
        civ = Civ(cached_civ.name)
        civ.rankings = cached_civ.rankings
        civ.popularity = cached_civ.popularity
        civ.totals = cached_civ.totals
        return civ

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
    start = 0
    counters = []
    for edge in edges:
        civ_ctr = Counter()
        counters.append(civ_ctr)
        snapshot_players = [p for p in players if start < p.best_rating <= edge]
        for player in snapshot_players:
            player.add_civ_percentages(civ_ctr, map_name, start, edge)
        start = edge - 50
    return counters

def loaded_civs(data_set_type, max_maps=len(MAPS)):
    """ Calculates civ popularities overall, by map, by rating bucket, and by map-rating combination.
    returns civs, the maps that have data, and the rating keys available in the civs."""
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
    players = CachedPlayer.rated_players(data_set_type)

    # Calculate overall popularity
    for ctr in civ_popularity_counters_for_map_bucketed_by_rating(players, 'all', [10000]):
        total = sum(ctr.values())
        for idx, civ in enumerate(sorted(ctr, key=lambda x: ctr[x], reverse=True)):
            civs[civ].rankings['Overall'] = idx + 1
            civs[civ].popularity['Overall'] = ctr[civ]/total
            civs[civ].totals['Overall'] = total
    # # Calculate overall popularity per rating bucket
    for ctr_idx, ctr in enumerate(civ_popularity_counters_for_map_bucketed_by_rating(players, 'all', edges)):
        total = sum(ctr.values())
        for idx, civ in enumerate(sorted(ctr, key=lambda x: ctr[x], reverse=True)):
            civs[civ].rankings[rating_keys[ctr_idx]] = idx + 1
            civs[civ].popularity[rating_keys[ctr_idx]] = ctr[civ]/total
            civs[civ].totals[rating_keys[ctr_idx]] = total

    # Calculate overall popularity by map
    maps_with_data = []
    for map_name in MAPS:
        for ctr in civ_popularity_counters_for_map_bucketed_by_rating(players, map_name, [10000]):
            if ctr:
                maps_with_data.append(map_name)
                total = sum(ctr.values())
            for idx, civ in enumerate(sorted(ctr, key=lambda x: ctr[x], reverse=True)):
                civs[civ].rankings[map_name] = idx + 1
                civs[civ].popularity[map_name] = ctr[civ]/total
                civs[civ].totals[map_name] = total

        if len(maps_with_data) > max_maps:
            break
    # Calculate overall popularity by map by rating bucket
    for map_name in maps_with_data:
        for ctr_idx, ctr in enumerate(civ_popularity_counters_for_map_bucketed_by_rating(players, map_name, edges)):
            total = sum(ctr.values())
            for idx, civ in enumerate(sorted(ctr, key=lambda x: ctr[x], reverse=True)):
                civs[civ].rankings['{}-{}'.format(map_name, rating_keys[ctr_idx])] = idx + 1
                civs[civ].popularity['{}-{}'.format(map_name, rating_keys[ctr_idx])] = ctr[civ]/total
                civs[civ].totals['{}-{}'.format(map_name, rating_keys[ctr_idx])] = total
    return civs, maps_with_data, rating_keys

def civs_x_maps_heatmap_table(civs, maps, normalize):
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
    def new_normalize(x):
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
    html_rows.append(to_heatmap_table(data, xlabels, ylabels, 'Map Name', new_normalize))
    return '\n'.join(html_rows)

def civs_x_maps_heatmap_tables_per_rating_bucket(civs, maps, rating_keys, normalize):
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
        max_value = sorted(civ_popularities, reverse=True)[len(maps)-1]
        def new_normalize(x):
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
        html_rows.append(to_heatmap_table(data, xlabels, ylabels, 'Map Name', new_normalize))
    return '\n'.join(html_rows)

def write_civs_x_maps_heatmaps_to_html(civs, maps, rating_keys, normalize):
    """ Generates html representation of each rating's popularity by map and civ. """
    with open('{}/civs/rating_popularity_data.html'.format(ROOT_DIR), 'w') as f:
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
      td.data { text-align: center; }
      th { width: 4em; }
  </style>
</head>
<body>
""")
        f.write(civs_x_maps_heatmap_table(civs, maps, None))
        f.write(civs_x_maps_heatmap_tables_per_rating_bucket(civs, maps, rating_keys, normalize))

def write_maps_x_ratings_heatmaps_to_html(civs, maps, rating_keys, normalize, data_set_type):
    """ Generates html representation of each civ's popularity by map and rating. """
    with open('{}/civs/civ_popularity_data.html'.format(ROOT_DIR), 'w') as f:
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
      td.data { text-align: center; }
      th { width: 4em; }
  </style>
</head>
<body>
""")
        f.write(all_civs_map_x_rating_heatmap_table(data_set_type, rating_keys))
        f.write('<h2>Popularity of Each Civ Segmented by Map and Ranking</h2>')
        for civ_name in sorted(civs):
            f.write(civs[civ_name].map_x_rating_heatmap_table(maps, rating_keys, normalize))

def write_civs_x_ratings_heatmaps_to_html(civs, maps, rating_keys, normalize):
    """ Generates html representation of each map's civ popularity by rating. """
    with open('{}/civs/map_popularity_data.html'.format(ROOT_DIR), 'w') as f:
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
        for map_name in sorted(maps, key=lambda x: total_civ.totals[x], reverse=True):
            civ_popularities = [civ.popularity['{}-{}'.format(map_name, rk)] for rk in rating_keys for civ in civs.values()]
            max_value = sorted(civ_popularities, reverse=True)[len(rating_keys)-1]
            def new_normalize(x):
                if max_value == 0:
                    return 0
                if x > max_value:
                    return 1
                return x/max_value
            total = int(sum([total_civ.totals['{}-{}'.format(map_name, rk)] for rk in rating_keys]))
            f.write('<h3>{} (n={:,})</h3>\n'.format(map_name, total))
            data = []
            for civ_name in civ_names:
                data.append(civs[civ_name].heatmap_rating_data(map_name, rating_keys))
            f.write(to_heatmap_table(data, rating_keys, civ_names, 'Civilization', new_normalize))
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
        print('{1[0][0]:15} ({1[0][1]:5.2f})  {1[1][0]:15} ({1[1][1]:5.2f}) - {0:15}'.format(map_name, match))

def cache_results(data_set_type):
    """ Pickles results so can do analysis without rerunning everything."""
    civs, maps_with_data, rating_keys = loaded_civs(data_set_type)
    with open(CACHED_TEMPLATE.format(data_set_type), 'wb') as f:
        pickle.dump([[CachedCiv(civ) for civ in civs.values()], maps_with_data, rating_keys], f)

def cached_results(data_set_type):
    """ Returns pickled results. Will generate pickle if not present. """
    cache_file = CACHED_TEMPLATE.format(data_set_type)
    if not os.path.exists(cache_file):
        cache_results(data_set_type)
    with open(CACHED_TEMPLATE.format(data_set_type), 'rb') as f:
        cached_civs, maps_with_data, rating_keys = pickle.load(f)
        civs = {}
        for cc in cached_civs:
            civs[cc.name] = Civ.from_cache(cc)
    return civs, maps_with_data, rating_keys

def popularity_cdf(civs):
    """ CDF of popularities to emphasize minor differences and flatten major ones. """
    ctr = Counter()
    for civ in civs:
        for popularity in civ.popularity.values():
            ctr[round(popularity, 3)] += 1
    rt = 0
    total = float(sum(ctr.values()))
    mapping = {0:0}
    for popularity in sorted(ctr):
        rt += ctr[popularity]
        mapping[round(popularity, 3)] = rt/total
    return mapping

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
        snapshot_players = [p for p in players if start < p.best_rating <= edge]
        for player in snapshot_players:
            player.add_map_percentages(map_ctr, start, edge)
        start = edge - 50
    return counters

def all_civs_map_x_rating_heatmap_table(data_set_type, viz_rating_keys=None):
    """ Returns a single heatmap html table of maps x ratings """
    maps = {}
    for k in MAPS:
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
    players = CachedPlayer.rated_players(data_set_type)
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

def rebuild_cache():
    """ For use after resampling data (elo.sample). """
    for data_set_type in ('test', 'model', 'verification',):
        PlayerRating.ratings_for(data_set_type, update=True)
        cache_results(data_set_type)

def write_all():
    """ Write out all the tables to all the files. """
    data_set_type = 'model'
    civs, maps_with_data, rating_keys = cached_results(data_set_type)
    half_keys = [k for i, k in enumerate(rating_keys) if not i % 2]
    mapping = popularity_cdf(civs.values())
    def normalized(x):
        return mapping[round(x, 3)]
    write_maps_x_ratings_heatmaps_to_html(civs, maps_with_data, half_keys, normalized, data_set_type)
    write_civs_x_maps_heatmaps_to_html(civs, maps_with_data, half_keys, normalized)
    write_civs_x_ratings_heatmaps_to_html(civs, maps_with_data, half_keys, normalized)

def run():
    data_set_type = 'test'
    civs, maps_with_data, rating_keys = cached_results(data_set_type)
    map_similarity(civs, maps_with_data, rating_keys)
if __name__ == '__main__':
    write_all()
