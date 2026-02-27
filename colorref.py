from graph import Vertex, Edge, Graph
from graph_io import load_graph
from typing import Literal, Dict, List, Set, Tuple
from collections import defaultdict

"""
1D Colour Refinement
Disjoint Union - Weisfeiler-Lehman Algorithm
"""


def set_default_colouring(G: Graph, initial_colouring_type: Literal['uniform', 'degree'] = 'uniform') -> None:
    """
    Initializes the colour of all vertices in a given graph.
    :param G: The Graph object whose vertices are to be coloured.
    :param initial_colouring_type: 'uniform' assigns colour 1 to all vertices. 
    :return: None. Modifies the vertices of the graph in-place.
    """
    for v in G:
        v.colour = v.degree if initial_colouring_type == 'degree' else 1


def partition_vertices(vertices: List[Vertex]) -> Dict[Tuple, List[Vertex]]:
    """
    Groups vertices based on their current colour and the colours of their neighbours.
    :param vertices: A list of all vertices across ALL graphs (disjoint union).
    :return: A dictionary where the keys are tuples representing the vertex's 
             colour signature: (vertex_colour, sorted_neighbour_colour_1, ...), 
             and the values are lists of Vertex objects sharing that signature.
    """
    partition = defaultdict(list)
    for v in vertices:
        v_nhc = (v.colour, *sorted([n_v.colour for n_v in v.neighbours]))
        partition[v_nhc].append(v)
    return partition


def get_colouring_partition(vertices: List[Vertex]) -> List[List[Vertex]]:
    """
    Generates a deterministically sorted list of vertex partitions.
    Sorting the partitions by their colour signature ensures that isomorphic 
    graphs strictly receive the exact same new colour IDs in the next step.
    :param vertices: A list of all vertices across ALL graphs.
    :return: A list of lists, where each inner list contains vertices that 
             share the same structural signature, sorted by that signature.
    """
    partition = partition_vertices(vertices)
    return list(map(lambda p: p[1], sorted(list(partition.items()), key=lambda pe: pe[0])))


def refine_graph_from_partition(partition: List[List[Vertex]]) -> None:
    """
    Assigns new integer colours to vertices based on their position in the new partition.
    :param partition: A sorted list of lists containing vertices grouped by signature.
    :return: None. Modifies the vertex colours in-place.
    """
    for i, vertices in enumerate(partition):
        for v in vertices:
            if v.colour != i:
                v.colour = i


def basic_colorref(filename: str) -> List[Tuple[List[int], List[int], int, bool]]:
    """
    Executes the 1D Colour Refinement (Weisfeiler-Lehman) algorithm on a file containing
    multiple graphs. It processes all graphs simultaneously in a global colour space 
    (disjoint union) to accurately identify equivalence classes.
    :param filename: Path to a .grl file containing the graphs.
    :return: A sorted list of tuples representing equivalence classes. Each tuple contains:
             - A sorted list of graph indices belonging to the class.
             - A sorted list of the sizes of the final colour classes.
             - The number of iterations it took for these graphs to reach stability.
             - A boolean indicating whether the final colouring is discrete.
    """
    with open(filename, 'r') as file:
        graphs = load_graph(file, graph_class=Graph, read_list=True)

    # 1. Pool all vertices to run refinement on the disjoint union
    all_vertices = []
    for G in graphs:
        set_default_colouring(G)
        for v in G:
            all_vertices.append(v)

    # Trackers for individual graph stability
    num_colours_per_graph = [len(set(v.colour for v in G)) for G in graphs]
    iterations_to_stability = [0] * len(graphs)
    
    global_num_colours = len(set(v.colour for v in all_vertices))
    iteration = 0

    # 2. Main Refinement Loop
    while True:
        curr_partition = get_colouring_partition(all_vertices)
        
        # Stop condition: The number of global colour classes stopped increasing
        if global_num_colours == len(curr_partition):
            break

        refine_graph_from_partition(curr_partition)
        global_num_colours = len(curr_partition)
        iteration += 1

        # Track exactly when each individual graph stops splitting
        for i, G in enumerate(graphs):
            current_g_colours = len(set(v.colour for v in G))
            if current_g_colours > num_colours_per_graph[i]:
                num_colours_per_graph[i] = current_g_colours
                iterations_to_stability[i] = iteration

    # 3. Group by Global Signature
    graph_equivalence_classes = defaultdict(list)
    for i, G in enumerate(graphs):
        # A graph's signature is the sorted multiset of its global vertex colours
        global_signature = tuple(sorted([v.colour for v in G]))
        graph_equivalence_classes[global_signature].append(i)

    # 4. Format Output
    result = []
    for signature, indices in graph_equivalence_classes.items():
        sorted_indices = sorted(indices)

        # Reconstruct the sizes of the colour classes from the signature
        counts = defaultdict(int)
        for colour in signature:
            counts[colour] += 1
    
        sizes = sorted(list(counts.values()))
        iters = iterations_to_stability[sorted_indices[0]]
        is_discrete = (len(sizes) == sum(sizes))
        
        result.append((sorted_indices, sizes, iters, is_discrete))

    # Return sorted by the first graph index in each equivalence class
    return sorted(result, key=lambda x: x[0][0])
