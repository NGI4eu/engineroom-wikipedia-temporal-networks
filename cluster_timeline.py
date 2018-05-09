#!/usr/bin/env python
"""
usage: cluster_timeline.py [-h] <evolution_dictionary>

Calculate Louvain clusters on a graph, given as an edge list

positional arguments:
  <network>   A file with the specification of the network as an edge list

optional arguments:
  -h, --help  show this help message and exit

"""

import os
import csv
import json
import argparse
import logging

########## logging
# create logger with 'spam_application'
logger = logging.getLogger(__file__)
logger.setLevel(logging.DEBUG)

# create file handler which logs even debug messages
fh = logging.FileHandler('louvain_clusters.log')
fh.setLevel(logging.DEBUG)

# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)

# add the handlers to the logger
logger.addHandler(fh)
logger.addHandler(ch)
##########


def get_args():
    description=('Create a timeline with clusters')
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('evodict', metavar='<evolution_dictionary>',
                        help='A file with the dictionary and the clusters')

    args = parser.parse_args()
    return args


def main():
    args = get_args()
    logger.info('Start')

    evodict = dict()
    with open(args.evodict, 'r') as evodict_file:
        evodict = json.load(evodict_file)

    evo_basename = os.path.basename(args.evodict).split('.')[0]
    evo_path = os.path.join('data', '{}.timeline.data'.format(evo_basename))
    with open(evo_path, 'w+') as evo_file:
        writer = csv.writer(evo_file, delimiter='\t')
        for date, compare_dict in evodict.items():
            for k, v in compare_dict.items():
                writer.writerow((date, v))

    # import ipdb; ipdb.set_trace()
    logger.info('Done!')


if __name__ == '__main__':
    main()
