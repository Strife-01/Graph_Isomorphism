"""
Basic Colour Refinement — O(n²m) Weisfeiler-Lehman 1D algorithm.

Iteratively refines vertex colours based on the sorted multiset of
neighbour colours until a stable colouring is reached (no colour class
splits further).  All graphs are processed simultaneously in a single
global colour space (disjoint union) so that isomorphic graphs receive
identical colour signatures.

Reference: Chapter 2 of the reader (Algorithm 1 — Colour Refinement).
"""

from collections import defaultdict
from typing import List, Dict, Tuple
from graph import Graph, Vertex
from graph_io import load_graph


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

def set_default_colouring(graph: Graph, mode: str = "uniform") -> None:
    """Assign an initial colour to every vertex in *graph*.

    Args:
        graph:  The graph whose vertices are coloured in-place.
        mode:   ``"uniform"`` sets colour 1 for all vertices.
                ``"degree"`` sets each vertex's colour to its degree.
    """
    for v in graph:
        v.colour = v.degree if mode == "degree" else 1


# ---------------------------------------------------------------------------
# Partition helpers
# ---------------------------------------------------------------------------

def partition_vertices(vertices: List[Vertex]) -> Dict[Tuple, List[Vertex]]:
    """Group vertices by their colour signature.

    A vertex's signature is the tuple
    ``(own_colour, sorted_neighbour_colour_1, …)``.
    Vertices with the same signature are structurally indistinguishable
    by 1-WL and belong to the same partition cell.

    Args:
        vertices:  All vertices across every graph (disjoint union).

    Returns:
        A dict mapping each signature to its list of vertices.
    """
    partition: Dict[Tuple, List[Vertex]] = defaultdict(list)
    for v in vertices:
        signature = (v.colour, *sorted(n.colour for n in v.neighbours))
        partition[signature].append(v)
    return partition


def get_sorted_partition(vertices: List[Vertex]) -> List[List[Vertex]]:
    """Return a deterministically sorted list of partition cells.

    Sorting by signature ensures that isomorphic graphs receive the
    exact same new colour ids in the next refinement step.

    Args:
        vertices:  All vertices across every graph.

    Returns:
        A list of vertex groups, sorted by their signature.
    """
    partition = partition_vertices(vertices)
    return [cell for _, cell in sorted(partition.items())]


# ---------------------------------------------------------------------------
# Refinement step
# ---------------------------------------------------------------------------

def assign_colours_from_partition(partition: List[List[Vertex]]) -> None:
    """Assign new integer colours based on partition position.

    Cell *i* in the sorted partition receives colour *i*.
    Modifies vertex colours in-place.

    Args:
        partition:  Sorted list of vertex groups (from ``get_sorted_partition``).
    """
    for colour, cell in enumerate(partition):
        for v in cell:
            v.colour = colour


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def basic_colorref(filename: str) -> List[Tuple[List[int], List[int], int, bool]]:
    """Run basic 1-WL colour refinement on a ``.grl`` file.

    Reads all graphs from the file, pools their vertices into a single
    disjoint union, and iteratively refines until the global colouring
    is stable.  Graphs are then grouped into equivalence classes by
    their sorted colour multiset.

    Args:
        filename:  Path to a ``.grl`` file containing one or more graphs.

    Returns:
        A sorted list of tuples, one per equivalence class:
            - ``graph_indices`` — sorted list of 0-based graph indices.
            - ``colour_class_sizes`` — sorted list of colour-class sizes.
            - ``iterations`` — number of refinement rounds to stability.
            - ``is_discrete`` — whether every colour class has size 1.
    """
    with open(filename, "r") as file:
        graphs = load_graph(file, graph_class=Graph, read_list=True)

    # 1. Pool all vertices and assign uniform initial colouring
    all_vertices: List[Vertex] = []
    for G in graphs:
        set_default_colouring(G)
        all_vertices.extend(G)

    # Per-graph colour counts (used to track individual convergence)
    num_colours_per_graph = [len({v.colour for v in G}) for G in graphs]
    iterations_to_stability = [0] * len(graphs)

    global_num_colours = len({v.colour for v in all_vertices})
    iteration = 0

    # 2. Iterative refinement loop
    while True:
        current_partition = get_sorted_partition(all_vertices)

        # Stop when the number of global colour classes no longer increases
        if global_num_colours == len(current_partition):
            break

        assign_colours_from_partition(current_partition)
        global_num_colours = len(current_partition)
        iteration += 1

        # Track the iteration at which each graph individually stabilises
        for i, G in enumerate(graphs):
            current_g_colours = len({v.colour for v in G})
            if current_g_colours > num_colours_per_graph[i]:
                num_colours_per_graph[i] = current_g_colours
                iterations_to_stability[i] = iteration

    # 3. Group graphs by their global colour signature
    graph_classes: Dict[Tuple, List[int]] = defaultdict(list)
    for i, G in enumerate(graphs):
        signature = tuple(sorted(v.colour for v in G))
        graph_classes[signature].append(i)

    # 4. Format output
    result: List[Tuple[List[int], List[int], int, bool]] = []
    for signature, indices in graph_classes.items():
        sorted_indices = sorted(indices)

        # Reconstruct colour-class sizes from the signature
        counts: Dict[int, int] = defaultdict(int)
        for colour in signature:
            counts[colour] += 1
        sizes = sorted(counts.values())

        iters = iterations_to_stability[sorted_indices[0]]
        is_discrete = len(sizes) == sum(sizes)

        result.append((sorted_indices, sizes, iters, is_discrete))

    return sorted(result, key=lambda x: x[0][0])
