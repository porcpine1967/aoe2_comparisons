#!/usr/bin/env python

import json
import pathlib

PARENT_DIR = pathlib.Path(__file__).parent.absolute()

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

class Lookup:
    def __init__(self):
        self.data = {}
        with open('{}/strings.json'.format(PARENT_DIR)) as f:
            data_dict = json.load(f)
        for k, attrs in data_dict.items():
            if isinstance(attrs, list):
                hold = {}
                reverse = {}
                for attr in attrs:
                    hold[attr['id']] = attr['string']
                    reverse[attr['string']] = attr['id']
            self.data[k] = hold
            self.data['{}_reverse'.format(k)] = reverse

    def civ_name(self, code):
        return self.data['civ'][int(code)]

    def map_name(self, code):
        return self.data['map_type'][int(code)]
    def map_type(self, name):
        return self.data['map_type_reverse'][name]
