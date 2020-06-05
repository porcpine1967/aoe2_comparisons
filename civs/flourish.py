#!/usr/bin/env python

""" Generates csv files for visualization in flourish """
from collections import defaultdict, Counter
import csv
import pathlib

import numpy as np
from statsmodels.stats.proportion import proportion_confint

from utils.models import MatchReport, Player, CachedPlayer
from utils.lookup import Lookup

ROOT_DIR = str(pathlib.Path(__file__).parent.parent.absolute())
GRAPH_DIR = '{}/graphs'.format(ROOT_DIR)

CIVILIZATIONS = {
    'Britons': { 'category': 'The Age of Kings', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/a/ae/CivIcon-Britons.png'},
    'Byzantines': { 'category': 'The Age of Kings', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/2/27/CivIcon-Byzantines.png'},
    'Celts': { 'category': 'The Age of Kings', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/5/59/CivIcon-Celts.png'},
    'Chinese': { 'category': 'The Age of Kings', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/c/cc/CivIcon-Chinese.png'},
    'Franks': { 'category': 'The Age of Kings', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/1/1b/CivIcon-Franks.png'},
    'Goths': { 'category': 'The Age of Kings', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/2/24/CivIcon-Goths.png'},
    'Japanese': { 'category': 'The Age of Kings', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/9/9a/CivIcon-Japanese.png'},
    'Mongols': { 'category': 'The Age of Kings', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/1/10/CivIcon-Mongols.png'},
    'Persians': { 'category': 'The Age of Kings', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/a/ad/CivIcon-Persians.png'},
    'Saracens': { 'category': 'The Age of Kings', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/5/59/CivIcon-Saracens.png'},
    'Teutons': { 'category': 'The Age of Kings', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/3/3f/CivIcon-Teutons.png'},
    'Turks': { 'category': 'The Age of Kings', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/1/1c/CivIcon-Turks.png'},
    'Vikings': { 'category': 'The Age of Kings', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/c/c9/CivIcon-Vikings.png'},
    'Aztecs': { 'category': 'The Conquerors', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/0/0c/CivIcon-Aztecs.png'},
    'Huns': { 'category': 'The Conquerors', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/1/17/CivIcon-Huns.png'},
    'Koreans': { 'category': 'The Conquerors', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/7/73/CivIcon-Koreans.png'},
    'Mayans': { 'category': 'The Conquerors', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/0/05/CivIcon-Mayans.png'},
    'Spanish': { 'category': 'The Conquerors', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/0/0a/CivIcon-Spanish.png'},
    'Incas': { 'category': 'The Forgotten', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/5/5e/CivIcon-Incas.png'},
    'Indians': { 'category': 'The Forgotten', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/8/8b/CivIcon-Indians.png'},
    'Italians': { 'category': 'The Forgotten', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/e/e1/CivIcon-Italians.png'},
    'Magyars': { 'category': 'The Forgotten', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/6/68/CivIcon-Magyars.png'},
    'Slavs': { 'category': 'The Forgotten', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/1/12/CivIcon-Slavs.png'},
    'Berbers': { 'category': 'The African Kingdoms', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/7/71/CivIcon-Berbers.png'},
    'Ethiopians': { 'category': 'The African Kingdoms', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/c/cb/CivIcon-Ethiopians.png'},
    'Malians': { 'category': 'The African Kingdoms', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/8/80/CivIcon-Malians.png'},
    'Portuguese': { 'category': 'The African Kingdoms', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/6/60/CivIcon-Portuguese.png'},
    'Burmese': { 'category': 'Rise of the Rajas', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/7/79/CivIcon-Burmese.png'},
    'Khmer': { 'category': 'Rise of the Rajas', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/e/ec/CivIcon-Khmer.png'},
    'Malay': { 'category': 'Rise of the Rajas', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/c/c3/CivIcon-Malay.png'},
    'Vietnamese': { 'category': 'Rise of the Rajas', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/0/07/CivIcon-Vietnamese.png'},
    'Bulgarians': { 'category': 'Definitive Edition', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/c/ce/CivIcon-Bulgarians.png'},
    'Cumans': { 'category': 'Definitive Edition', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/c/cc/CivIcon-Cumans.png'},
    'Lithuanians': { 'category': 'Definitive Edition', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/0/0d/CivIcon-Lithuanians.png'},
    'Tatars': { 'category': 'Definitive Edition', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/f/f2/CivIcon-Tatars.png'},
}
MAPS = {
'Alpine Lakes': { 'category': 'Hybrid', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/4/4b/Alpine_lakes_select_aoe2DE.png'},
'Arabia': { 'category': 'Land', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/4/44/Imgres-0.jpg'},
'Arena': { 'category': 'Land', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/b/b5/Rm_arena.gif'},
'Black Forest': { 'category': 'Land', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/c/ca/Th.jpeg'},
'Cenotes': { 'category': 'Land', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/a/a0/Cenotes_Preview.jpg'},
'Coastal': { 'category': 'Hybrid', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/8/85/Coastal-_Age_of_Empires.png'},
'Continental': { 'category': 'Hybrid', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/4/41/Age_of_Empires_-_Continental2.jpg'},
'Four Lakes': { 'category': 'Hybrid', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/1/19/Fourlakes_selection_aoe2de.png'},
'Ghost Lake': { 'category': 'Land', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/4/4e/Ghostlake.gif'},
'Gold Rush': { 'category': 'Land', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/5/53/Gold_Rush.jpg'},
'Golden Pit': { 'category': 'Land', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/c/c0/Golden_Pit_mini_map-0.png'},
'Golden Swamp': { 'category': 'Hybrid', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/1/1e/Goldenswamp_selection_aoe2de.png'},
'Hideout': { 'category': 'Land', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/9/98/HideoutMapAoE2.png'},
'Highland': { 'category': 'Land', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/b/b4/Highland_-_AoE.jpg'},
'Islands': { 'category': 'Water', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/3/3d/Islands_-_large.jpg'},
'Lombardia': { 'category': 'Land', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/4/4c/LombardiaMapAoE2.png'},
'Mediterranean': { 'category': 'Hybrid', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/a/ab/AoEII_Mediterranean2.png'},
'MegaRandom': { 'category': 'Hybrid', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/b/bf/Megarandom1.png'},
'Mongolia': { 'category': 'Land', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/9/94/Mongolia-_AoEII_4-player.png'},
'Nomad': { 'category': 'Hybrid', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/1/13/Nomad_minimap_aoe2.png'},
'Oasis': { 'category': '', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/7/7d/Oasis.png'},
'Rivers': { 'category': 'Land', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/a/aa/Rivers_minimap.jpg'},
'Scandinavia': { 'category': 'Land', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/8/87/Scandinavia.jpg'},
'Serengeti': { 'category': 'Land', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/a/a9/Serengeti_map.png'},
'Steppe': { 'category': 'Land', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/8/8c/Straitofmalacca.png'},
'Team Islands': { 'category': 'Water', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/e/ed/Team_Islands.jpg'},
'Valley': { 'category': 'Land', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/f/fd/Valley_Preview.jpg'},
}
class MatchExperience:
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

class CivInfo:
    def __init__(self, name, results):
        self.name = name
        self.results = results
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

class CivCluster:
    def __init__(self, base_civ):
        self.base_civ = base_civ
        self.mean = base_civ.mean
        self.civs = [base_civ]

    @property
    def cluster_mean(self):
        return np.mean([i for civ in self.civs for i in civ.results])

    def maybe_add(self, other_civ):
        """ Adds civ to civs if should; returns if added """
        should_add = self.base_civ.cl < other_civ.mean < self.base_civ.cu
        if should_add:
            self.civs.append(other_civ)
        return should_add
    def set_civ_means(self):
        for civ in self.civs:
            civ.csv_mean = '{:.1f}'.format(100*self.cluster_mean)

def civs_by_snapshots(data_set_type, map_type, snapshot_count):
    maps = constants()['map_type']
    map_name = maps[map_type].lower()
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
    print('n = {}'.format(offset*3))
    hold = 0
    snapshots = []
    civ_names = set()
    row_header = ['Civilization']
    for _ in range(snapshot_count):
        civs = defaultdict(lambda: [])
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
        civ_clusters = []
        current_civ_cluster = None
        in_clusters = set()
        civ_infos_s = sorted(civ_infos.values(), key=lambda x: x.mean - x.cl)
        for civ_info in civ_infos_s:
            if civ_info in in_clusters:
                continue
            current_civ_cluster = CivCluster(civ_info)
            civ_clusters.append(current_civ_cluster)
            in_clusters.add(civ_info)
            for other_ci in civ_infos_s:
                if other_ci in in_clusters:
                    continue
                added = current_civ_cluster.maybe_add(other_ci)
                if added:
                    in_clusters.add(other_ci)

        for cluster in civ_clusters:
            cluster.set_civ_means()
        snapshots.append(civ_infos)
    rows = [row_header]
    for name in sorted(civ_names):
        row = [name, CIVILIZATIONS[name]['category'], CIVILIZATIONS[name]['image']]
        for snapshot in snapshots:
            row.append(snapshot[name].csv_mean)
        rows.append(row)

    with open('{}/flourish_{}.csv'.format(GRAPH_DIR,map_name), 'w') as f:
        writer = csv.writer(f)
        writer.writerows(rows)

# class Player:
#     def __init__(self, player_id):
#         self.player_id = player_id
#         self.civ = None
#         self.rating = None
#         self.timestamp = None

#     def maybe_update(self, civ, rating, timestamp):
#         if not self.timestamp or self.timestamp < timestamp:
#             self.civ = civ
#             self.rating = rating
#             self.timestamp = timestamp

def map_popularity(data_set_type):
    matches = MatchReport.all(data_set_type)
    players = Player.player_values(matches)
    m = Counter()
    for player in players:
        for map_type in player.maps:
            m[map_type] += 1
    return m

def civ_popularity_by_rating(players, map_name):
    print(map_name)
    edges = [i for i in range(650, 1651, 50)]
    edges.append(10000)
    start = 0
    counters = []
    headers = []
    edge_totals = []
    for edge in edges:
        total = 0.0
        if edge == edges[-1]:
            headers.append('{}+'.format(start + 1))
        else:
            headers.append('{} - {}'.format(start + 1, edge))
        civ_ctr = Counter()
        counters.append(civ_ctr)
        snapshot_players = [p for p in players if start < p.best_rating <= edge]
        for player in snapshot_players:
            if player.add_civ_percentages(civ_ctr, map_name, start, edge):
                total += 1
        edge_totals.append(total)
        start = edge
    row_header = ['Civilization', 'Category', 'Image'] + headers
    rows = [row_header]
    for civ_name, civ_info in CIVILIZATIONS.items():
        row = [civ_name, civ_info['category'], civ_info['image'],]
        for idx, civ_ctr in enumerate(counters):
            row.append(civ_ctr[civ_name])
        rows.append(row)
    with open('{}/flourish_{}_popularity.csv'.format(GRAPH_DIR, map_name.lower()), 'w') as f:
        writer = csv.writer(f)
        writer.writerows(rows)

def civ_popularity_by_map(data_set_type):
    """ Writes csv for civ popularities by ratings snapshot for every map type."""
    players = CachedPlayer.rated_players(data_set_type)
    lookup = Lookup()
    civ_popularity_by_rating(players, 'all')
    return
    for map_name, count in map_popularity(data_set_type).most_common():
        if count < 1100:
            continue
        print(map_name, count)
        civ_popularity_by_rating(players, map_name)
        break

def map_popularity_by_rating(players, mincount):
    print(len(players))
    edges = [i for i in range(650, 1651, 50)]
    edges.append(10000)
    start = 0
    counters = []
    headers = []
    for edge in edges:
        if edge == edges[-1]:
            headers.append('{}+'.format(start + 1))
        else:
            headers.append('{} - {}'.format(start + 1, edge))
        map_ctr = Counter()
        counters.append(map_ctr)
        snapshot_players = [p for p in players if start < p.best_rating <= edge]
        for player in snapshot_players:
            player.add_map_percentages(map_ctr, start, edge)
        start = edge
    row_header = ['Map', 'Category', 'Image'] + headers
    rows = [row_header]
    for map_name, map_info in MAPS.items():
        row = [map_name, map_info['category'], map_info['image'],]
        for map_ctr in counters:
            row.append(100*map_ctr[map_name]/float(sum([v for v in map_ctr.values()])))
        print(sum(row[3:]))
        rows.append(row)
    with open('{}/flourish_map_popularity.csv'.format(GRAPH_DIR), 'w') as f:
        writer = csv.writer(f)
        writer.writerows(rows)

if __name__ == '__main__':
    data_set_type = 'model'
    civ_popularity_by_map(data_set_type)
