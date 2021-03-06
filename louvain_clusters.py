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
import pickle
from collections import defaultdict

# needs to import optimize explicitly
# https://github.com/scipy/scipy/issues/4005
import scipy
from scipy import optimize

########## logging
# create logger with 'spam_application'
logger = logging.getLogger(__file__)
logger.setLevel(logging.DEBUG)

# create file handler which logs even debug messages
fh = logging.FileHandler(__file__.replace('.py','.log'))
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

    logger.info('Preparing to drop empty graphs')
    graphs_copy = copy.deepcopy(graphs)
    for graph_date, G in graphs_copy.items():
        if G.vcount() == 0:
            logger.debug('Dropping empty graph {}'.format(graph_date))
            del graphs[graph_date]
    del graphs_copy
    logger.info('Dropped empty graphs')

    global_vset = set()
    for graph_date, G in graphs.items():
         vertices = [v.attributes()['name'] for v in G.vs]
         global_vset.update(vertices)

    logger.info('Building global index of vertices')
    global_vlist = sorted(global_vset)
    del global_vset
    global_vtoid = dict((vname, vid) 
                        for vid, vname in enumerate(global_vlist))
    global_idtov = dict((vid, vname) 
                        for vid, vname in enumerate(global_vlist))
    with open(os.path.join('data','vertex.json'), 'w+') as vertexfile:
        json.dump(global_idtov, vertexfile)
    logger.info('Global index of vertices built')


    logger.info('Calculating partitions for all snapshots')
    partitions = dict()
    for graph_date, G in graphs.items():
        logger.debug('Calculating partitions for graph {}...'
                      .format(graph_date))
        part = louvain.find_partition(G, louvain.ModularityVertexPartition);
        partitions[graph_date] = part

    logger.info('Calculated partitions for all snapshots')

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

                clevoname = 'graph.{0}.clusters.csv'.format(graph_date)
                clevoutfile_path = os.path.join('data', 'partitions-evolution',
                                                clevoname)

                with open(clevoutfile_path, 'w+') as clevoutfile:
                    for idx, cluster in en_clusters:

                        nodes = set([v.attributes()['name']
                                     for v in cluster.vs])


                        nodes_ids = sorted([global_vtoid[n] for n in nodes])
                        clevoutfile.write(
                            '{}\n'.format(' '.join(str(nid) 
                                                   for nid in nodes_ids
                                                   )
                                          ))

                        clname = ('graph.{0}.cluster.{1:02}.csv'
                                  .format(graph_date, idx))
                        cloutfile_path = os.path.join('data', 'partitions',
                                                      clname)

                        with open(cloutfile_path, 'w+') as cloutfile:
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

    logger.info('Compared clusters at t and t+1')
    compare_clusters = dict()
    similarity_clusters = dict()
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

        logger.debug('Compared clusters at {} and {}'.format(t1,t2))

        res = scipy.optimize.linear_sum_assignment(clmatrix)
        cluster_t1_indices = res[0].tolist()
        cluster_t2_indices = res[1].tolist()
        c1_to_c2 = dict(zip(cluster_t1_indices,cluster_t2_indices))

        compare_clusters['{}_{}'.format(t1,t2)] = c1_to_c2

        sim_c1c2 = dict()
        for c1, c2 in c1_to_c2.items():
            sim_c1c2[c1] = clmatrix[c1][c2]
        
        similarity_clusters['{}_{}'.format(t1,t2)] = sim_c1c2

    logger.info('Compared all clusters')

    clevo_filename = 'clusters_evolution.json'
    clevo_path = os.path.join('data', clevo_filename)
    with open(clevo_path, 'w') as clevo_out:
        json.dump(compare_clusters, clevo_out)

    evolved_clusters = defaultdict(dict)
    evolved_clusters_stable = defaultdict(dict)

    cl_date_prev = None
    cluster_no = 0
    cluster_no_stable = 0
    cluster_sizes = dict()
    for date, clusters in all_clusters:
        cl_date = date.format('YYYY-MM-DD')
        cluster_sizes[cl_date] = defaultdict(int)
        logger.info('Processing clusters for {}...'.format(cl_date))

        cl_dict = None
        if cl_date_prev is not None:
            key = '{}_{}'.format(cl_date_prev, cl_date)
            cl_dict = compare_clusters[key]
            inv_cl_dict = {v: k for k, v in cl_dict.items()}

            for cl in clusters:
                clid = cl[0]
                if clid in cl_dict.values():
                    evolved_clusters[cl_date][clid] = \
                        evolved_clusters[cl_date_prev][inv_cl_dict[clid]]

                    if similarity_clusters[key][inv_cl_dict[clid]] < 0.34:
                        evolved_clusters_stable[cl_date][clid] = \
                            evolved_clusters_stable[cl_date_prev][inv_cl_dict[clid]]
                    else:
                        evolved_clusters_stable[cl_date][clid] = cluster_no_stable
                        cluster_no_stable += 1
                else:
                    evolved_clusters[cl_date][clid] = cluster_no
                    evolved_clusters_stable[cl_date][clid] = cluster_no_stable

                    cluster_no += 1
                    cluster_no_stable += 1

                cluster_sizes[cl_date][evolved_clusters[cl_date][clid]] = \
                    cl[1].vcount()


        else:
            for cl in clusters:
                clid = cl[0]
                evolved_clusters[cl_date][clid] = cluster_no
                evolved_clusters_stable[cl_date][clid] = cluster_no_stable

                cluster_no += 1
                cluster_no_stable += 1

                cluster_sizes[cl_date][evolved_clusters[cl_date][clid]] = \
                    cl[1].vcount()

        cl_date_prev = cl_date

    for i in range(cluster_no):
        clsize_path = os.path.join('data',
                                   'cluster-sizes',
                                   'cluster_sizes.{:03}.csv'.format(i)) 
        with open(clsize_path, 'w+') as clsizefile:
            clsizewriter = csv.writer(clsizefile, delimiter='\t')
            for graph_date in dates:
                if graph_date in cluster_sizes:
                    cl_size = cluster_sizes[graph_date][i]
                else:
                    cl_size = 0
                
                clsizewriter.writerow((graph_date, cl_size))


    evcl_path = os.path.join('data','evolved_clusters.json')
    with open(evcl_path, 'w+') as evcl_file:
        json.dump(evolved_clusters, evcl_file)

    evclstable_path = os.path.join('data','evolved_clusters_stable.json')
    with open(evclstable_path, 'w+') as evclstable_file:
        json.dump(evolved_clusters_stable, evclstable_file)    

    cl_date_prev = None


    logger.info('Processing vertexes in clusters')
    vertex_clusters = defaultdict(dict)
    for date, clusters in all_clusters:
        cl_date = date.format('YYYY-MM-DD')
        logger.info('Processing clusters for {}...'.format(cl_date))

        for clid, cl in clusters:
            logger.debug('Processing cluster id {} for {}...'
                         .format(clid, cl_date))

            nodes = [v.attributes()['name'] for v in cl.vs]

            for node in nodes:
                vertex_clusters[node][cl_date] = evolved_clusters[cl_date][clid]


    for node in global_vlist:
        node_outfilename = get_valid_filename(
                            'node_evolution_{}.csv'.format(node))
        node_outfilepath = os.path.join('data', 'nodes-evolution',
                                        node_outfilename)

        with open(node_outfilepath, 'w+') as node_outfile:
            writer = csv.writer(node_outfile, delimiter='\t')
            writer.writerow(('date', 'cluster_id'))

        for graph_date in dates:
            clid = vertex_clusters[node].get(graph_date, -1)

            with open(node_outfilepath, 'a+') as node_outfile:
                writer = csv.writer(node_outfile, delimiter='\t')
                writer.writerow((graph_date, clid))

    logger.info('All done!')


if __name__ == '__main__':
    main()
