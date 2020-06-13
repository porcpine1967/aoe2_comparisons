#!/usr/bin/env python
""" Tool for gathering statistics on progress of download. """

import argparse
import datetime
import os
import pathlib
import re
import time

from utils.team_models import Rating

def monitor(args):
    profile_pattern = re.compile(r'matches_for_([0-9]+)\.csv$')
    start = None
    count = 0

    for filename in sorted(pathlib.Path(Rating.data_dir).iterdir(), key=os.path.getmtime):
        m = profile_pattern.search(str(filename))
        if count > 0 and m:
            count += 1
        if m and m.group(1) == args.first_profile:
            start = os.stat(Rating.data_file_template.format(m.group(1))).st_mtime
            count = 1
    now = time.time()
    time_expended = now - start
    time_expected = time_expended * args.total/count
    time_left = datetime.timedelta(seconds=int(time_expected - time_expended))
    expected_finish = (datetime.datetime.now() + time_left).strftime('%I:%M:%S')
    template = '{:18}: {:>8}'
    print(template.format('Expected finish', expected_finish))
    print(template.format('Time left', str(time_left)))
    print(template.format('Records done', count))
    print(template.format('Records left', args.total - count))
    template = '{:18}: {:>8.2f}'
    print(template.format('Users per second', count/time_expended))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('first_profile', help="id of first profile downloaded")
    parser.add_argument('total', type=int, help="number of records to process")
    args = parser.parse_args()
    monitor(args)
