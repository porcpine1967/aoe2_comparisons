#!/usr/bin/env python

""" Generates csv files for visualization in flourish """
import argparse
from collections import defaultdict, Counter
import csv
import pathlib

import numpy as np
from statsmodels.stats.proportion import proportion_confint

import utils.solo_models
import utils.team_models

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
    'Acropolis': { 'category': 'Land', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/3/3d/Acropolis_Preview.jpg'},
    'Alpine Lakes': { 'category': 'Hybrid', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/4/4b/Alpine_lakes_select_aoe2DE.png'},
    'Arabia': { 'category': 'Land', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/4/44/Imgres-0.jpg'},
    'Arena': { 'category': 'Land', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/b/b5/Rm_arena.gif'},
    'Black Forest': { 'category': 'Land', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/c/ca/Th.jpeg'},
    'Bog Islands': { 'category': 'Hybrid', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/0/02/Bog_Islands.png'},
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
    'Hill Fort': { 'category': 'Land', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/2/26/HillFortMapAoE2.png'},
    'Islands': { 'category': 'Water', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/3/3d/Islands_-_large.jpg'},
    'Kilimanjaro': { 'category': 'Land', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/5/55/Kilimanjaro.png'},
    'Lombardia': { 'category': 'Land', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/4/4c/LombardiaMapAoE2.png'},
    'Mediterranean': { 'category': 'Hybrid', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/a/ab/AoEII_Mediterranean2.png'},
    'MegaRandom': { 'category': 'Hybrid', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/b/bf/Megarandom1.png'},
    'Mongolia': { 'category': 'Land', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/9/94/Mongolia-_AoEII_4-player.png'},
    'Mountain Pass': { 'category': 'Land', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/3/39/Mountain.png'},
    'Nomad': { 'category': 'Hybrid', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/1/13/Nomad_minimap_aoe2.png'},
    'Oasis': { 'category': 'Land', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/7/7d/Oasis.png'},
    'Rivers': { 'category': 'Land', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/a/aa/Rivers_minimap.jpg'},
    'Scandinavia': { 'category': 'Land', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/8/87/Scandinavia.jpg'},
    'Serengeti': { 'category': 'Land', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/a/a9/Serengeti_map.png'},
    'Steppe': { 'category': 'Land', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/8/8c/Straitofmalacca.png'},
    'Team Islands': { 'category': 'Water', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/e/ed/Team_Islands.jpg'},
    'Valley': { 'category': 'Land', 'image': 'https://vignette.wikia.nocookie.net/ageofempires/images/f/fd/Valley_Preview.jpg'},
}

def map_popularity(players):
    m = Counter()
    for player in players:
        for map_type in player.maps:
            m[map_type] += 1
    return m

def civ_popularity_by_rating(players, map_name, module):
    print('Civ popularity by rating for {}'.format(map_name))
    edges = [i for i in range(650, 1701, 50)]
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
        snapshot_players = [p for p in players if start < p.best_rating() <= edge]
        for player in snapshot_players:
            if player.add_civ_percentages(civ_ctr, map_name, start, edge):
                total += 1
        edge_totals.append(total)
        start = edge - 50
    row_header = ['Civilization', 'Category', 'Image'] + headers
    rows = [row_header]
    for civ_name, civ_info in CIVILIZATIONS.items():
        row = [civ_name, civ_info['category'], civ_info['image'],]
        for idx, civ_ctr in enumerate(counters):
            row.append(civ_ctr[civ_name])
        rows.append(row)
    with open('{}/flourish_{}_popularity.csv'.format(module.GRAPH_DIR, map_name.lower()), 'w') as f:
        writer = csv.writer(f)
        writer.writerows(rows)

def civ_popularity_by_map(players, module):
    print('civ_popularity_by_map')
    """ Writes csv for civ popularities by ratings snapshot for every map type."""
    civ_popularity_by_rating(players, 'all', module)
    for map_name, count in map_popularity(players).most_common():
        if count < 1100:
            continue
        civ_popularity_by_rating(players, map_name, module)

def map_popularity_by_rating(players, module):
    print('map_popularity_by_rating')
    edges = [i for i in range(650, 1701, 50)]
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
        snapshot_players = [p for p in players if start < p.best_rating() <= edge]
        for player in snapshot_players:
            player.add_map_percentages(map_ctr, start, edge)
        start = edge - 50
    row_header = ['Map', 'Category', 'Image'] + headers
    rows = [row_header]
    for map_name, map_info in MAPS.items():
        row = [map_name, map_info['category'], map_info['image'],]
        for map_ctr in counters:
            row.append(map_ctr[map_name])
        rows.append(row)
    with open('{}/flourish_map_popularity.csv'.format(module.GRAPH_DIR), 'w') as f:
        writer = csv.writer(f)
        writer.writerows(rows)

def map_popularity_by_number_of_matches(players, module):
    print('map_popularity_by_number_of_matches')
    map_counters = defaultdict(lambda: Counter())
    for player in players:
        player.add_map_percentages(map_counters[len(player.matches)], 0, 10000)
    rt = 0
    hold_counter = Counter()
    start_key = None
    end_key = None
    headers = []
    counters = []
    for key in sorted(map_counters):
        end_key = key
        if not start_key:
            start_key = key
        ctr = map_counters[key]
        for k, v in ctr.items():
            hold_counter[k] += v
        if sum(hold_counter.values())/len(players) < .018:
            continue
        counters.append(hold_counter)
        if end_key > start_key:
            print_key = '{} - {}'.format(start_key, end_key)
        else:
            print_key = str(start_key)
        headers.append(print_key)
        start_key = None
        hold_counter = Counter()
    if end_key > start_key:
        print_key = '{} - {}'.format(start_key, end_key)
    else:
        print_key = str(start_key)
    headers.append(print_key)
    counters.append(hold_counter)
    row_header = ['Map', 'Category', 'Image'] + headers
    rows = [row_header]
    for map_name, map_info in MAPS.items():
        row = [map_name, map_info['category'], map_info['image'],]
        for map_ctr in counters:
            row.append(map_ctr[map_name])
        rows.append(row)
    with open('{}/flourish_map_popularity_by_num_matches.csv'.format(module.GRAPH_DIR), 'w') as f:
        writer = csv.writer(f)
        writer.writerows(rows)

def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('klass', choices=('team', 'solo',), help="team or solo")
    parser.add_argument('--source', default='model', choices=('test', 'model', 'verification',), help="which data set type to use (default model)")
    args = parser.parse_args()
    if args.klass == 'team':
        module = utils.team_models
    else:
        module = utils.solo_models
    players = [p for p in module.Player.player_values(module.MatchReport.all(args.source), args.source) if p.best_rating()]
    map_popularity_by_number_of_matches(players, module)
    map_popularity_by_rating(players, module)
    civ_popularity_by_map(players, module)

if __name__ == '__main__':
    run()
