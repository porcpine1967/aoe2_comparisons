#!/usr/bin/env python

""" Looks at the elo progression of 100 random players from 1v1 ranked in order to see if there are any patterns."""
from collections import defaultdict, Counter
import csv
import pathlib

import numpy as np
from statsmodels.stats.proportion import proportion_confint

from utils.models import MatchReport
from utils.lookup import constants

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

if __name__ == '__main__':
    civs_by_snapshots('all', 29, 25)
