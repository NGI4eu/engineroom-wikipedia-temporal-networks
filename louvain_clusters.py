#!/usr/bin/env python
"""
usage: louvain_clusters.py [-h] <network>

Calculate Louvain clusters on a graph, given as an edge list

positional arguments:
  <network>   A file with the specification of the network as an edge list

optional arguments:
  -h, --help  show this help message and exit

"""

import os
import re
import csv
import json
import argparse
import logging
import igraph as ig
import louvain
import copy
import arrow
from typing import Iterable, Iterator, Mapping, NamedTuple, Optional
import itertools
import numpy as np

# needs to import optimize explicitly
# https://github.com/scipy/scipy/issues/4005
import scipy
from scipy import optimize

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

##########
Cluster = NamedTuple('Cluster', [
    ('date', arrow.arrow.Arrow),
    ('clusters', list),
])
##########


def get_args():
    description=('Calculate Louvain clusters on a graph,'
                 ' given as an edge list')
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('networks', metavar='<network>', nargs='+',
                        help='A file with the specification of the network '
                             'as an edge list')

    args = parser.parse_args()
    return args


# Sanitize filenames
# https://stackoverflow.com/questions/295135
def get_valid_filename(s):
    s = str(s).strip().replace(' ', '_')
    return re.sub(r'(?u)[^-\w.]', '', s)


# Jaccard distance:
# distance = 1 - (Jaccard similarity)
#
# http://dataconomy.com/2015/04/
#   implementing-the-five-most-popular-similarity-measures-in-python/
def jaccard_distance(s1: Iterable[set],
                       s2: Iterable[set]) -> float:
    
    intersection_cardinality = len(set.intersection(*[set(s1), set(s2)]))
    union_cardinality = len(set.union(*[set(s1), set(s2)]))

    return (1.0 - (intersection_cardinality/float(union_cardinality)))


def main():
    args = get_args()
    logger.info('Start')

    graphs = dict()
    dates = list()
    for network in args.networks:
        logger.debug('Loading file {}...'.format(network))
        with open(network, 'r') as infile:

            basefilename = os.path.basename(network)
            graph_date = basefilename.split('.')[-2]

            dates.append(graph_date)
            reader = csv.reader(infile, delimiter='\t')

            # skip header
            next(reader)

            edgelist = [edge for edge in reader]

        # collect the set of vertex names and then sort them into a list
        vertices = set()
        for edge in edgelist:
            # iterates on the list and add each element
            vertices.update(edge)
        vertices = sorted(vertices)

        # new graph
        G = ig.Graph()

        # add vertices to the graph
        G.add_vertices(vertices)

        # add edges to the graph
        G.add_edges(edgelist)

        graphs[graph_date] = G
        logger.debug('done!')

    logger.info('Loaded all graphs')

    graphs_copy = copy.deepcopy(graphs)
    for graph_date, G in graphs_copy.items():
        if G.vcount() == 0:
            logger.info('Dropping empty graph {}'.format(graph_date))
            del graphs[graph_date]
    del graphs_copy

    partitions = dict()
    for graph_date, G in graphs.items():
        logger.debug('Calculating partitions for graph {}...'
                      .format(graph_date))
        part = louvain.find_partition(G, louvain.ModularityVertexPartition);
        partitions[graph_date] = part

    logger.info('Calculated all partitions')

    all_clusters = list()
    csv_header = ('date', 'n_partitions')
    with open(os.path.join('data', 'partitions.csv'), 'w+') as outfile:
        writer = csv.writer(outfile, delimiter='\t')
        writer.writerow(csv_header)

        for graph_date in dates:
            logger.debug('Writing clusters for snapshot {}'
                          .format(graph_date))

            parts = partitions.get(graph_date, None)
            if parts is not None:
                writer.writerow((graph_date, len(parts)))
    
                en_clusters = [cl for cl in enumerate(parts.subgraphs())]
                all_clusters.append(Cluster(arrow.get(graph_date),
                                            en_clusters)
                                    )

                for idx, cluster in en_clusters:
                    nodes = set([v.attributes()['name']
                                 for v in cluster.vs])

                    clname = ('graph.{0}.cluster.{1:02}.csv'
                              .format(graph_date, idx))
                    cloutfile_name = os.path.join('data', 'partitions',
                                                  clname)

                    with open(cloutfile_name, 'w+') as cloutfile:
                        for node in nodes:
                            cloutfile.write('{}\n'.format(node))

            else:
                writer.writerow((graph_date, 0))

        logger.info('Written all clusters')
        # Iterate over all pairs of consecutive items from a given
        # list
        # https://stackoverflow.com/q/21303224/2377454
        cluster_pairs = [pair for pair 
                         in zip(all_clusters, all_clusters[1:])]

        compare_clusters = dict()
        for snap_t1, snap_t2 in cluster_pairs:
            t1 = str(snap_t1.date.format('YYYY-MM-DD'))
            t2 = str(snap_t2.date.format('YYYY-MM-DD'))

            assert snap_t1.date.replace(months=+1) == snap_t2.date

            # snap_t1.clusters and snap_t2.clusters are the clusters at
            # time t and t+1

            snap_t1_clusters_nodes = list()
            for idx1, cl1 in snap_t1.clusters:
                snap_t1_clusters_nodes.append((idx1,
                                               [v.attributes()['name'] 
                                               for v in cl1.vs]))
            del idx1, cl1

            snap_t2_clusters_nodes = list()
            for idx2, cl2 in snap_t2.clusters:
                snap_t2_clusters_nodes.append((idx2,
                                               [v.attributes()['name'] 
                                               for v in cl2.vs]))
            del idx2, cl2

            cluster_product = itertools.product(snap_t1_clusters_nodes,
                                                snap_t2_clusters_nodes)

            #  numpy.zeros(shape, dtype=float, order='C')
            n = len(snap_t1_clusters_nodes)
            m = len(snap_t2_clusters_nodes)
            clmatrix = np.zeros((n,m), dtype=float)
            for cl1, cl2 in cluster_product:
                ridx = cl1[0]
                cidx = cl2[0]
                logger.debug('Comparing clusters at {} and {}: ({},{})'
                              .format(t1,t2,ridx,cidx))

                nodes_cl1 = set(cl1[1])
                nodes_cl2 = set(cl2[1])

                sim = jaccard_distance(nodes_cl1, nodes_cl2)

                clmatrix[ridx][cidx] = sim

            logger.info('Compared clusters at {} and {}'.format(t1,t2))

            res = scipy.optimize.linear_sum_assignment(clmatrix)
            cluster_t1_indices = res[0].tolist()
            cluster_t2_indices = res[1].tolist()
            c1_to_c2 = dict(zip(cluster_t1_indices,cluster_t2_indices))

            compare_clusters['{}_{}'.format(t1,t2)] = c1_to_c2

        logger.info('Compared all clusters')

        clevo_filename = 'clusters_evolution.csv'
        clevo_path = os.join('data', clevo_filename)
        with open(clevo_path, 'w') as clevo_out:
            json.dump(compare_clusters, clevo_out)

        cl_date_prev = None
        for date, clusters in all_clusters:
            cl_date = date.format('YYYY-MM-DD')
            logger.info('Processing clusters for {}...'.format(cl_date))

            for clid, cl in clusters:
                logger.info('Processing cluster id {} for {}...'
                            .format(clid, cl_date))

                cl_dict = None
                if cl_date_prev is not None:
                    key = '{}_{}'.format(cl_date_prev, cl_date)
                    cl_dict = compare_clusters.get(key, None)

                nodes = [v.attributes()['name'] for v in cl.vs]

                for node in nodes:
                    node_outfilename = get_valid_filename(
                                        'node_evolution_{}.csv'.format(node))
                    node_outfilepath = os.path.join('data', 'nodes-evolution',
                                                    node_outfilename)

                    cl_inv_dict = None
                    if cl_dict is not None:
                        cl_inv_dict = {v: k for k, v in cl_dict.items()}

                    newclid = clid
                    if cl_inv_dict and cl_inv_dict.get(clid, None) is not None:
                        newclid = cl_inv_dict.get(clid)
                        import ipdb; ipdb.set_trace()

                    if not os.path.isfile(node_outfilepath):
                        with open(node_outfilepath, 'a+') as node_outfile:
                            writer = csv.writer(node_outfile, delimiter='\t')
                            writer.writerow(('date', 'cluster_id'))

                    with open(node_outfilepath, 'a+') as node_outfile:
                        writer = csv.writer(node_outfile, delimiter='\t')
                        writer.writerow((cl_date, newclid))

            cl_date_prev = cl_date


if __name__ == '__main__':
    main()
