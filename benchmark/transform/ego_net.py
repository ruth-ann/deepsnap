import copy
import time
import torch
import argparse
import numpy as np

from torch.utils.data import DataLoader
from deepsnap.batch import Batch
from deepsnap.dataset import GraphDataset
from torch_geometric.datasets import TUDataset

def arg_parse():
    parser = argparse.ArgumentParser(description='Pagerank arguments.')
    parser.add_argument('--device', type=str,
                        help='CPU / GPU device.')
    parser.add_argument('--netlib', type=str,
                        help='Backend network library, nx or sx.')
    parser.add_argument('--batch_size', type=int,
                        help='Batch size.')
    parser.add_argument('--num_runs', type=int,
                        help='Number of runs averaged on.')
    parser.add_argument('--dataset', type=str,
                        help='Dataset.')
    parser.add_argument('--print_run', action='store_true',
                        help='Print out current run.')

    parser.set_defaults(
        device='cuda:0',
        netlib="nx",
        batch_size=1,
        num_runs=100,
        dataset='COX2',
        print_run=False,
    )
    return parser.parse_args()

def ego_nets(graph, radius=2):
    egos = []
#    time_1 = time.time()

    for i in range(graph.num_nodes):
        if radius > 4:
            egos.append(graph.G) #what is graph.G
        else:
            egos.append(netlib.ego_graph(graph.G, i, radius=radius)) #  """Returns induced subgraph of neighbors centered at node n within a given radius.
 #   time_2 = time.time() #0.0007936954498291016

    G = graph.G.__class__()
    id_bias = graph.num_nodes
    for i in range(len(egos)):
        G.add_node(i, **egos[i].nodes(data=True)[i])
  #  time_3 = time.time() #0.0017819404602050781

    for i in range(len(egos)):
   #     time_1 = time.time()
        keys = list(egos[i].nodes)
    #    time_2 = time.time()
        keys.remove(i)
     #   time_3 = time.time()
        id_cur = egos[i].number_of_nodes() - 1
      #  time_4 = time.time()
        vals = range(id_bias, id_bias + id_cur)
       # time_5 = time.time()
        id_bias += id_cur
        mapping = dict(zip(keys, vals))
        #time_6 = time.time()
        ego = netlib.relabel_nodes(egos[i], mapping, copy=True) #10 seconds
        #time_7 = time.time()
        #G.add_nodes_from(range(2))
        G.add_nodes_from(ego.nodes(data=True)) #3 seconds
        #time_8 = time.time()
        #G.add_edges_from([[0, 1]])
        G.add_edges_from(ego.edges(data=True))  #10 seconds
        #time_9 = time.time()
   # print("For loop time")
   # print("Ego Net 2: ", time_2 - time_1)
   # print("Ego Net 3: ", time_3 - time_2)
   # print("Ego Net 4: ", time_4 - time_3)
   # print("Ego Net 5: ", time_5 - time_4)
   # print("Ego Net 6: ", time_6 - time_5)
   # print("Ego Net 7: ", time_7 - time_6)
   # print("Ego Net 8: ", time_8 - time_7)
   # print("Ego Net 9: ", time_9 - time_8)

    #print("For loop times")

    graph.G = G
   # time_4 = time.time()#0.05971074104309082

    graph.node_id_index = torch.arange(len(egos))

    #time_5 = time.time()


    # print("Ego Net Time 1: ", time_1)
    # print("Ego Net 2: ", time_2 - time_1)
    # print("Ego Net 3: ", time_3 - time_2)
    # print("Ego Net 4: ", time_4 - time_3)
    # print("Ego Net 5: ", time_5 - time_4)

def ego_graph(edge_index, num_nodes, node, radius=2):
    edge_list = {}
    for i in range(edge_index.shape[1]):
        if edge_index[0][i].item() in edge_list:
            edge_list[edge_index[0][i].item()].add(edge_index[1][i].item())
        else:
            edge_list[edge_index[0][i].item()] = set([edge_index[1][i].item()])
    if radius > 4:
        return set(range(num_nodes)), edge_list
    neighbors = set([node])
    for i in range(radius):
        neighbors_temp = copy.copy(neighbors)
        for neighbor in neighbors:
            neighbor_neighbors = edge_list[neighbor]
            for nn in neighbor_neighbors:
                neighbors_temp.add(nn)
        neighbors = neighbors_temp
    ego_edge_list = {}
    for neighbor in neighbors:
        if neighbor in edge_list:
            neighbor_neighbors = edge_list[neighbor]
            for nn in neighbor_neighbors:
                if nn in neighbors:
                    if neighbor in ego_edge_list:
                        ego_edge_list[neighbor].append(nn)
                    else:
                        ego_edge_list[neighbor] = [nn]
    return list(neighbors), ego_edge_list

def pyg_ego_nets(graph, radius=2):
    x = []
    edges = []
    egos = []
    for i in range(graph.num_nodes):
        egos.append(ego_graph(graph.edge_index, graph.num_nodes, i, radius=radius))
    id_bias = graph.num_nodes
    for i in range(len(egos)):
        x.append(graph.x[i])
    for i in range(len(egos)):
        for neighbor in egos[i][0]:
            if neighbor != i:
                x.append(graph.x[neighbor])
        keys = list(egos[i][0])
        keys.remove(i)
        id_cur = len(egos[i][0])
        vals = range(id_bias, id_bias + id_cur)
        id_bias += id_cur
        mapping = dict(zip(keys, vals))
        ego_edge_list = egos[i][1]
        for node in ego_edge_list:
            neighbors = ego_edge_list[node]
            for neighbor in neighbors:
                if node == i:
                    src = node 
                else:
                    src = mapping[node]
                if neighbor == i:
                    dst = neighbor 
                else:
                    dst = mapping[neighbor]
                edges.append([src, dst])
    edge_index = torch.tensor(edges, dtype=torch.long).t()
    x = torch.stack(x)
    return x, edge_index

def pyg_ego(args, pyg_dataset):
    avg_time = 0
    for i in range(args.num_runs):
        if args.print_run:
            print("Run {}".format(i + 1))
        graphs = []
        ds = pyg_dataset[:373]
        from torch_geometric.data import DataLoader
        loader = DataLoader(ds, batch_size=1)
        s = time.time()
        for batch in loader:
            x, edge_index = pyg_ego_nets(batch)
        avg_time += (time.time() - s)
    print("Tensor has average time: {}".format(avg_time / args.num_runs))

def deepsnap_ego(args, pyg_dataset):
    avg_time = 0
    task = "graph"
    for i in range(args.num_runs):
        if args.print_run:
            print("Run {}".format(i + 1))
     #   time_1 = time.time()

        graphs = GraphDataset.pyg_to_graphs(pyg_dataset, verbose=True, netlib=netlib)
      #  time_2 = time.time()

        dataset = GraphDataset(graphs, task=task)
        datasets = {}
        datasets['train'], datasets['val'], datasets['test'] = dataset.split(transductive=False, split_ratio = [0.8, 0.1, 0.1], shuffle=False)
       # time_3 = time.time()

        dataloaders = {
            split: DataLoader(
                dataset, collate_fn=Batch.collate(), 
                batch_size=1, shuffle=False
            ) for split, dataset in datasets.items()
        }
        #time_4 = time.time()

        s = time.time()
        for batch in dataloaders['train']:
            batch = batch.apply_transform(ego_nets, update_tensor=True)
       # time_5 = time.time()
       # print("Deepsnap Ego")
       # print("Time 1: ", time_1)
       # print("Time 2: ", time_2 - time_1)
       # print("Time 3: ", time_3 - time_2)
       # print("Time 4: ", time_4 - time_3)
       # print("Time 5: ", time_5 - time_4)
       # print("Deepsnap Ego")

        avg_time += (time.time() - s)
    print("DeepSNAP has average time: {}".format(avg_time / args.num_runs))

if __name__ == '__main__':
    args = arg_parse()

    if args.netlib == "nx":
        print("Use NetworkX as the DeepSNAP backend network library.")
        import networkx as netlib
    elif args.netlib == "sx":
        print("Use SnapX as the DeepSNAP backend network library.")
        import snap
        import snapx as netlib
    else:
        import networkx as netlib
        print("Use NetworkX as the DeepSNAP backend network library.")

    if args.dataset == 'COX2':
        pyg_dataset = TUDataset('./tu', args.dataset)

    print("Start benchmark DeepSNAP:")
    deepsnap_ego(args, pyg_dataset)
    print("Start benchmark Tensor:")
    pyg_ego(args, pyg_dataset)
