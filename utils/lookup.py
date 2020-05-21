#!/usr/bin/env python

import json
import pathlib

PARENT_DIR = pathlib.Path(__file__).parent.absolute()

def constants():
    map_types = {}
    c = {}
    with open('{}/strings.json'.format(PARENT_DIR)) as f:
        data = json.load(f)
    for k, attrs in data.items():
        if isinstance(attrs, list):
            hold = {}
            for attr in attrs:
                hold[attr['id']] = attr['string']
            c[k] = hold
    return c
