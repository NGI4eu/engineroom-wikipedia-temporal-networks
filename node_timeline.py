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
import collections
from itertools import tee

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
    description=('Create a timeline for each node')
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('evonodes', metavar='<node_evolution>', nargs='+',
                        help='A file with node evolution')

    args = parser.parse_args()
    return args

# https://docs.python.org/3/library/itertools.html
def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)

# https://docs.python.org/3/library/itertools.html
def sextuples(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    it1, it2, it3, it4, it5, it6 = tee(iterable, 6)

    next(it2, None)
    next(it3, None)
    next(it4, None)
    next(it5, None)
    next(it6, None)

    next(it3, None)
    next(it4, None)
    next(it5, None)
    next(it6, None)

    next(it4, None)
    next(it5, None)
    next(it6, None)

    next(it5, None)
    next(it6, None)

    next(it6, None)

    return zip(it1, it2, it3, it4, it5, it6)


def all_equal(lst):
    return not lst or lst.count(lst[0]) == len(lst)


def main():
    args = get_args()
    logger.info('Start')


    nodes_evolution = dict()
    for evonode in args.evonodes:
        node = (os.path.basename(evonode)
                       .replace('node_evolution_','')
                       .replace('.csv','')
                       )
        node_data = {'different_clusters': 0,
                     'changes_of_cluster': 0,
                     'stable_changes_of_cluster': 0,
                     }
        nodes_evolution[node] = node_data

        with open(evonode, 'r') as evonode_file:
            reader = csv.reader(evonode_file, delimiter='\t')

            next(reader)

            cl_nodes = collections.OrderedDict([r for r in reader])

        dates = cl_nodes.keys()

        count_diff_cl = collections.Counter(cl_nodes.values())
        ndiff_cl = len(count_diff_cl)

        nchanges_cl = 0
        for e1, e2 in pairwise(cl_nodes.values()):
            if e1 != e2:
                nchanges_cl += 1

        stable_period = False
        count_stable = 0
        for sels in sextuples(cl_nodes.values()):
            if all_equal(sels):
              if not stable_period:
                count_stable += 1
                stable_period = True
            else:
                stable_period = False

        nodes_evolution[node]['different_clusters'] = ndiff_cl
        nodes_evolution[node]['changes_of_cluster'] = nchanges_cl
        nodes_evolution[node]['stable_changes_of_cluster'] = count_stable

    evo_path = os.path.join('data', 'nodes-evolution.timeline.csv')
    with open(evo_path, 'w+') as evo_file:
        writer = csv.writer(evo_file, delimiter=',')
        writer.writerow(
            ('page',
             'different_clusters',
             'changes_of_cluster',
             'stable_changes_of_cluster',
             )
            )
        for node in nodes_evolution:
            writer.writerow(
                (node,
                 nodes_evolution[node]['different_clusters'],
                 nodes_evolution[node]['changes_of_cluster'],
                 nodes_evolution[node]['stable_changes_of_cluster'],
                 )
                )

    logger.info('Done!')


if __name__ == '__main__':
    main()
