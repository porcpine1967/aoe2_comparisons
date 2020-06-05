#!/usr/bin/env python

import json
import pathlib

PARENT_DIR = pathlib.Path(__file__).parent.absolute()

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
