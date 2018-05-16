#!/usr/bin/env python3

import os
import re
import csv
import igraph
import logging
import argparse
import itertools
import igraph as ig
from math import sqrt
from operator import itemgetter, attrgetter


METRICS='mdrbckl'

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
formatter = logging.Formatter('[%(asctime)s][%(levelname)s]: %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)

# add the handlers to the logger
logger.addHandler(fh)
logger.addHandler(ch)
##########


#set to False to avoid displaying messages about the execution in the shell
verbose = True

# calculate the ranking of nodes according to a given metric
# (the input vector contains the value of the metric for each node)
def ranking(vector):
    nodes = {}  
    for i in range(len(vector)):
        value = vector[i]
        if value not in nodes:
            nodes[value] = []                       
        nodes[value].append(i+1)    
    ranking = {}        
    j = 1
    for k in reversed(sorted(nodes.keys())):
        for u in nodes[k]:
            ranking[u] = j
        j += len(nodes[k])  
    return ranking


def main(network, output, directed, metrics, betweenness_directed,
         closeness_mode, coreness_mode, base_node):

    # PARAMETERS - DEFAULT VALUES
    #
    # directed = False
    # set to True for the network to be considered as directed
    #
    # metrics = 'mdrbckl'
    # the metrics to be computed. By default, all are included (mdrbck)
    #   m: clusters (Louvain Modularity), d: degree, r: relevance,
    #   b: betweenness, c:closeness, k: coreness (k-index),
    #   l: distance (path length) from base_node
    #
    # betweenness_directed = True
    # set to 'False' for ignoring edges direction when computing betweenness
    # in a directed network
    #
    # closeness_mode = 'ALL'
    # set to 'IN' or 'OUT' to consider the length of incoming or outgoing
    # paths (respectively) when computing closeness in a directed network
    #
    # coreness_mode = 'ALL'
    # set to 'IN' or 'OUT' to compute in-coreness or out-coreness
    # (respectively) in a directed network.
    # By default, edge direction will not be considered when computing
    # coreness in a directed network
    #
    # base_node = 0
    # node for which the distances from all other nodes will be computed (in
    # case "l" is included in parameter "metrics"). Can be node label or id.
    # By default it is the first node appearing in the network file (node 0)
    
    #overwrite parameter values, when specified in the query
    directed_values = ['directed', 'dir', 'd', 'true', 'yes', 'y']
    undirected_values = ['false', 'no', 'n', 'undirected', 'un']
    
    logger.info('Execution parameters:')
    logger.info('metrics: {}'.format(metrics))
    logger.info('network: {}'.format(network))
    logger.info('directed: {}'.format(directed))
    logger.info('betweenness_directed (b_directed): {}'.format(betweenness_directed))
    logger.info('closeness_mode (c_mode): {}'.format(closeness_mode))
    logger.info('coreness_mode (k_mode): {}'.format(coreness_mode))
    logger.info('base node: {}'.format(base_node))
    logger.info('')
    
    # g = G.Read(network_folder_path + network, 'ncol', directed = directed)
    g = ig.Graph.Read(network, 'ncol', directed = directed)

    logger.info('network read. {} nodes and {} edges'.format(g.vcount(), 
                                                             g.ecount()))

    header = []
    header.append('node')
    # output = 'node'
    
    if metrics.find('m') >= 0:  
        if directed: 
            #create an undirected copy of the graph for computing the
            # Louvain method    
            g_und = g.copy()        
            g_und.to_undirected(mode="collapse")    
        else: g_und = g
        clustering = g_und.community_multilevel()
        node_clusters = {}
        for i in range(len(clustering)):
            for n in clustering[i]:
                node_clusters[n] = i+1

        # output += ',' +     'cluster'
        header.append('cluster')

    if metrics.find('d') >= 0:
        if directed:
            indegree = g.indegree()
            indegree_ranking = ranking(indegree)

            # output += ',' +     'indegree' + ',' + 'indegree_rank'
            header.append('indegree')
            header.append('indegree_rank')

            outdegree = g.outdegree()
            outdegree_ranking = ranking(outdegree)

            # output += ',' +     'outdegree' + ',' + 'outdegree_ranking'
            header.append('outdegree')
            header.append('outdegree_ranking')

        else:   
            degree = g.degree()     
            degree_ranking = ranking(degree)

            # output += ',' +     'degree' + ',' + 'degree_rank'
            header.append('degree')
            header.append('degree_rank')

    if metrics.find('r') >= 0:  
        # output += ',' +     'relevance' + ',' + 'relevance_rank'
        header.append('relevance')
        header.append('relevance_rank')

        if directed:
            pagerank = g.pagerank()
            pagerank_ranking = ranking(pagerank)

            #replaced by more general name "relevance"
            #~ output += ',' +  'pagerank' + ',' + 'pagerank_rank'
        else:   
            eigenvector = g.eigenvector_centrality()        
            eigenvector_ranking = ranking(eigenvector)

            #replaced by more general name "relevance"
            #~ output += ',' +  'eigenvector' + ',' + 'eigenvector_rank'

    if metrics.find('b') >= 0:
        betweenness = g.betweenness(directed=directed and betweenness_directed)     
        betweenness_ranking = ranking(betweenness)  

        # output += ',' +     'betweenness' + ',' + 'betweenness_rank'
        header.append('betweenness')
        header.append('betweenness_rank')

    if metrics.find('c') >= 0:
        closeness = g.closeness(mode=closeness_mode)        
        closeness_ranking = ranking(closeness)

        # output += ',' +     'closeness' + ',' + 'closeness_rank'
        header.append('closeness')
        header.append('closeness_rank')

    if metrics.find('k') >= 0:
        coreness = g.coreness(mode=coreness_mode)       
        coreness_ranking = ranking(coreness)

        # output += ',' +     'coreness' + ',' + 'coreness_rank'
        header.append('coreness')
        header.append('coreness_rank')

    if metrics.find('l') >= 0:
        shortest_paths = g.get_shortest_paths(base_node, to=None, weights=None,
                                              mode='ALL', output="vpath")

        # output += ',' +     'distance_from_node'
        header.append('distance_from_node')

    csvfile = open(output, 'w+')
    writer = csv.writer(csvfile, delimiter='\t')

    logger.info('Writing results to {}'.format(output))

    writer.writerow(header)

    for v in range(g.vcount()):
        data = []

        # output += '"' + g.vs[v]['name'] + '"'
        data.append(g.vs[v]['name'])

        if 'm' in metrics: 
            # output += ',' + str(node_clusters[v])
            data.append(node_clusters[v])

        if 'd' in metrics: 

            if directed:
                # output += ',' + str(indegree[v]) + ',' + str(indegree_ranking[v+1])
                # output += ',' + str(outdegree[v]) + ',' + str(outdegree_ranking[v+1])
                data.append(indegree[v])
                data.append(indegree_ranking[v+1])
                data.append(outdegree[v])
                data.append(outdegree_ranking[v+1])

            else:
                # output += ',' + str(degree[v]) + ',' + str(degree_ranking[v+1])
                data.append(degree[v])
                data.append(degree_ranking[v+1])

        if 'r' in metrics: 
            if directed:
                # output += ',' + str(pagerank[v]) + ',' + str(pagerank_ranking[v+1])
                data.append(pagerank[v])
                data.append(pagerank_ranking[v+1])

            else:
                # output += ',' + str(eigenvector[v]) + ',' + str(eigenvector_ranking[v+1])
                data.append(eigenvector[v])
                data.append(eigenvector_ranking[v+1])

        if 'b' in metrics: 
            # output += ',' + str(betweenness[v]) + ',' + str(betweenness_ranking[v+1])
            data.append(betweenness[v])
            data.append(betweenness_ranking[v+1])

        if 'c' in metrics: 
            # output += ',' + str(closeness[v]) + ',' + str(closeness_ranking[v+1])
            data.append(closeness[v])
            data.append(closeness_ranking[v+1])

        if 'k' in metrics: 
            # output += ',' + str(coreness[v]) + ',' + str(coreness_ranking[v+1])
            data.append(coreness[v])
            data.append(coreness_ranking[v+1])

        if 'l' in metrics: 
            # output += ',' + str(len(shortest_paths[v])-1)
            data.append(len(shortest_paths[v])-1)

        writer.writerow(data)

    csvfile.close()


def cli_args():

    def nonnegative_int(value):
        errmsg = "Invalid non-negative integer value: {}".format(value)

        try:
            ivalue = int(value)
        except ValueError:
            raise argparse.ArgumentTypeError(errmsg)

        if ivalue < 0:
            raise argparse.ArgumentTypeError(errmsg)

        return ivalue

    def string_choices(astring):

        combinations = list()
        for l in range(1,len(astring)+1):
            combinations += [''.join(el)
                             for el in itertools.combinations(astring,l)]

        return combinations


    parser = argparse.ArgumentParser()

    parser.add_argument("network",
                        metavar='<network>',
                        help="Input file.",
                        )
    parser.add_argument("--verbose",
                        help="Set verbose output.",
                        action='store_true'
                        )
    parser.add_argument("--output",
                        help="Output filename.",
                        )
    parser.add_argument("--directed",
                        help="The input network is directed.",
                        action='store_true'
                        )
    parser.add_argument("--metrics",
                        help="The metrics to be computed. "
                             "By default, all are included. "
                             "Acceptable values are 'mdrbck'.",
                        metavar='',
                        default=METRICS,
                        choices=string_choices(METRICS)
                        )
    parser.add_argument("--no-betweenness-directed",
                        dest='betweenness_directed',
                        help="Ignores edges direction when computing "
                             "betweenness in a directed network.",
                        action='store_false')
    parser.add_argument("--closeness-mode",
                        help="Set to 'IN' or 'OUT' to consider the length of "
                             "incoming or outgoing  paths (respectively) when "
                             " computing closeness in a directed network.",
                        choices=['IN', 'OUT', 'ALL'],
                        default='ALL'
                        )
    parser.add_argument("--coreness-mode",
                        help="Set to 'IN' or 'OUT' to compute in-coreness or "
                             "out-coreness (respectively) in a directed "
                             "network."
                             "By default, edge direction will not be considered "
                             "when computing coreness in a directed network.",
                        choices=['IN', 'OUT', 'ALL'],
                        default='ALL'
                        )
    parser.add_argument("--base-node",
                        help="Node for which the distances from all other nodes "
                             "will be computed (in case 'l' is included in "
                             " parameter 'metrics'). Can be node label or id. "
                             "Must be a nonnegative integer. "
                             "By default it is the first node appearing in the "
                             "network file (node 0)",
                        type=nonnegative_int,
                        default=0
                        )

    args = parser.parse_args()

    return args



if __name__ == '__main__':

    args = cli_args()

    csvfilename = args.output
    if args.output is None:
        network_basename = os.path.basename(args.network)
        csvfilename = '{}.metrics.csv'.format(os.path.splitext(network_basename)[0])

    main(args.network,
         output=csvfilename,
         directed=args.directed,
         metrics=args.metrics,
         betweenness_directed=args.betweenness_directed,
         closeness_mode=args.closeness_mode,
         coreness_mode=args.coreness_mode,
         base_node=args.base_node)
