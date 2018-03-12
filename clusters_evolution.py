#!/usr/bin/env python
"""
FIXME
usage: clusters_evolution.py [-h] <network>

Calculate Louvain clusters on a graph, given as an edge list

positional arguments:
  <network>   A file with the specification of the network as an edge list

optional arguments:
  -h, --help  show this help message and exit

"""

def main():

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
