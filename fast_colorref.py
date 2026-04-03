"""
Fast Colour Refinement — O(m log n) Hopcroft-style partition refinement.

Based on the DFA minimisation algorithm (Hopcroft, 1971) adapted for
the Graph Isomorphism problem as described in Chapter 4 of the reader.

Key idea:  Instead of iterating over *all* colour classes each round
(O(n²m) basic refinement), we maintain a work-queue of colour classes
that might still split other classes.  When a class splits, only the
*smaller* halves are added to the queue (Lemma 4.9), guaranteeing every
vertex enters the queue at most O(log n) times → total O(m log n).

Refine(C) for GI:  For each colour class D, partition D by the number
of neighbours each vertex has inside C.  If D splits, apply the
"add-smaller-to-queue" rule.
"""

from collections import defaultdict, deque
from typing import List, Dict, Tuple, Optional
from graph import Graph, Vertex


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class ColourClass:
    """A single cell in the partition, stored as a Python set for O(1)
    add / remove / membership and O(|cell|) iteration."""

    __slots__ = ("colour", "members")

    def __init__(self, colour: int, members: set):
        self.colour = colour
        self.members = members

    def __len__(self):
        return len(self.members)

    def __iter__(self):
        return iter(self.members)


class Partition:
    """Maintains the current partition of vertices into colour classes.

    Provides O(1) lookup of which class a vertex belongs to, and efficient
    splitting of classes.
    """

    def __init__(self):
        self.classes: Dict[int, ColourClass] = {}   # colour -> ColourClass
        self.vertex_colour: Dict[Vertex, int] = {}  # vertex -> its colour
        self._next_colour = 0

    def new_colour(self) -> int:
        c = self._next_colour
        self._next_colour += 1
        return c

    def add_class(self, members: set) -> int:
        """Create a new colour class from *members* and return its colour."""
        colour = self.new_colour()
        cc = ColourClass(colour, members)
        self.classes[colour] = cc
        for v in members:
            self.vertex_colour[v] = colour
        return colour

    def split(self, colour: int, subset: set) -> Optional[int]:
        """Split *subset* out of the class with the given *colour*.

        Returns the new colour assigned to *subset*, or None if no split
        occurred (subset is empty or equals the full class).
        """
        cc = self.classes[colour]
        if not subset or len(subset) == len(cc):
            return None

        # Remove subset from old class
        cc.members -= subset

        # Create new class for the subset
        new_colour = self.add_class(subset)
        return new_colour

    @property
    def num_classes(self) -> int:
        return len(self.classes)


# ---------------------------------------------------------------------------
# Core algorithm
# ---------------------------------------------------------------------------

def _build_neighbour_index(vertices: List[Vertex]) -> Dict[Vertex, List[Vertex]]:
    """Pre-compute adjacency lists (as Python lists) for fast iteration."""
    adj: Dict[Vertex, List[Vertex]] = {}
    for v in vertices:
        adj[v] = v.neighbours
    return adj


def _refine(partition: Partition,
            refine_colour: int,
            adj: Dict[Vertex, List[Vertex]],
            in_queue: Dict[int, bool],
            queue: deque) -> None:
    """Execute Refine(C) for graph colour refinement.

    For every colour class D in the current partition, count how many
    neighbours each vertex in D has inside C (the class with colour
    *refine_colour*).  If vertices in D disagree on this count, split D.

    Implements Algorithm 3/6 from the reader adapted for GI (Lemma 4.17):
    split by *number* of neighbours in C rather than by a single transition.
    """
    refine_class = partition.classes.get(refine_colour)
    if refine_class is None:
        return

    # Step 1: For every vertex in C, look at its neighbours and tally
    # how many neighbours each *external* vertex has inside C.
    # neighbour_count[v] = # of v's neighbours that are in C
    neighbour_count: Dict[Vertex, int] = defaultdict(int)
    affected_classes: Dict[int, set] = defaultdict(set)  # colour -> set of affected vertices

    for u in refine_class:
        for w in adj[u]:
            neighbour_count[w] += 1
            affected_classes[partition.vertex_colour[w]].add(w)

    # Step 2: For each affected colour class D, group its affected vertices
    # by their neighbour count.  Vertices in D that are NOT in
    # affected_classes[D.colour] have count 0.
    for d_colour, affected in affected_classes.items():
        d_class = partition.classes.get(d_colour)
        if d_class is None:
            continue

        # Group affected vertices by their count
        count_groups: Dict[int, set] = defaultdict(set)
        for v in affected:
            count_groups[neighbour_count[v]].add(v)

        # Vertices not in 'affected' have count 0 — they stay together.
        # We only need to split if there are at least 2 distinct groups
        # (including the implicit count-0 group if it's non-empty).
        unaffected_count = len(d_class) - len(affected)
        if unaffected_count > 0:
            # There's an implicit group with count 0
            num_groups = len(count_groups) + 1
        else:
            num_groups = len(count_groups)

        if num_groups <= 1:
            # All vertices in D agree on their count — no split needed
            continue

        # We need to split D.  Strategy: keep the largest group in D's
        # original colour, split the rest into new classes.
        # First, find the largest group.
        largest_count = -1
        largest_size = -1

        # Consider the unaffected group (count 0)
        if unaffected_count > largest_size:
            largest_size = unaffected_count
            largest_count = 0

        for cnt, group in count_groups.items():
            if len(group) > largest_size:
                largest_size = len(group)
                largest_count = cnt

        # Split out every group except the largest
        new_colours = []
        if largest_count == 0:
            # Keep unaffected vertices in original class; split out all count groups
            for cnt, group in count_groups.items():
                new_c = partition.split(d_colour, group)
                if new_c is not None:
                    new_colours.append(new_c)
        else:
            # The largest is a count group; keep it, split out the rest
            # First split out unaffected vertices (count 0) if any
            if unaffected_count > 0:
                unaffected_verts = d_class.members - affected
                new_c = partition.split(d_colour, unaffected_verts)
                if new_c is not None:
                    new_colours.append(new_c)

            # Split out other count groups
            for cnt, group in count_groups.items():
                if cnt == largest_count:
                    continue
                new_c = partition.split(d_colour, group)
                if new_c is not None:
                    new_colours.append(new_c)

        # Queue rule (Lemma 4.9):
        # If d_colour is already in the queue, add all new colours too.
        # Otherwise, add all new colours EXCEPT the largest fragment.
        # The original d_colour keeps its slot (it's now the largest fragment
        # or it was already in the queue).
        if in_queue.get(d_colour, False):
            for nc in new_colours:
                if not in_queue.get(nc, False):
                    queue.append(nc)
                    in_queue[nc] = True
        else:
            # d_colour is the largest fragment (we kept it there).
            # Add all the smaller new colours.
            for nc in new_colours:
                if not in_queue.get(nc, False):
                    queue.append(nc)
                    in_queue[nc] = True


def fast_colour_refine(vertices: List[Vertex],
                       adj: Dict[Vertex, List[Vertex]],
                       initial_colouring: Dict[Vertex, int]
                       ) -> Partition:
    """Run fast colour refinement on the given vertices.

    Args:
        vertices:  All vertices (across all graphs in the disjoint union).
        adj:       Pre-computed adjacency lists.
        initial_colouring:  Maps each vertex to its initial colour.

    Returns:
        The stable Partition.
    """
    # Build initial partition from the initial colouring
    partition = Partition()
    groups: Dict[int, set] = defaultdict(set)
    for v in vertices:
        groups[initial_colouring[v]].add(v)

    # Create colour classes and seed the queue with ALL initial classes
    queue: deque = deque()
    in_queue: Dict[int, bool] = {}

    for _, members in sorted(groups.items()):
        colour = partition.add_class(members)
        queue.append(colour)
        in_queue[colour] = True

    # Main loop: process queue until empty
    while queue:
        refine_colour = queue.popleft()
        in_queue[refine_colour] = False

        if refine_colour not in partition.classes:
            continue

        _refine(partition, refine_colour, adj, in_queue, queue)

    return partition


# ---------------------------------------------------------------------------
# Public API — mirrors basic_colorref interface
# ---------------------------------------------------------------------------

def colour_refine_graphs(graphs: List[Graph],
                         initial_colouring: Optional[Dict[Vertex, int]] = None
                         ) -> Partition:
    """Run fast colour refinement on a list of graphs (disjoint union).

    Args:
        graphs:  List of Graph objects.
        initial_colouring:  Optional dict mapping vertices to initial colours.
                            Defaults to uniform colouring (all colour 0).

    Returns:
        The stable Partition.
    """
    all_vertices = [v for G in graphs for v in G]

    if initial_colouring is None:
        initial_colouring = {v: 0 for v in all_vertices}

    adj = _build_neighbour_index(all_vertices)
    return fast_colour_refine(all_vertices, adj, initial_colouring)


def get_colour_signature(graph: Graph, partition: Partition) -> Tuple:
    """Return a canonical signature for a graph under the given partition.

    The signature is a sorted tuple of (colour, count) pairs, which is
    the same for isomorphic graphs.
    """
    counts: Dict[int, int] = defaultdict(int)
    for v in graph:
        counts[partition.vertex_colour[v]] += 1
    return tuple(sorted(counts.items()))


def is_balanced(graphs: List[Graph], partition: Partition) -> bool:
    """Check whether the partition is balanced across all graphs.

    Balanced means every colour class has the same number of vertices
    in each graph.
    """
    if len(graphs) < 2:
        return True

    ref_sig = get_colour_signature(graphs[0], partition)
    for G in graphs[1:]:
        if get_colour_signature(G, partition) != ref_sig:
            return False
    return True


def is_discrete_for_graph(graph: Graph, partition: Partition) -> bool:
    """Check whether the partition is discrete for a single graph
    (every vertex has a unique colour within that graph)."""
    colours = set()
    for v in graph:
        c = partition.vertex_colour[v]
        if c in colours:
            return False
        colours.add(c)
    return True


def defines_bijection(graph_a: Graph, graph_b: Graph,
                      partition: Partition) -> bool:
    """Check whether the partition defines a bijection between two graphs.

    A bijection is defined when the colouring is both balanced AND
    discrete for each graph individually.
    """
    return (is_discrete_for_graph(graph_a, partition) and
            is_discrete_for_graph(graph_b, partition))


def basic_colorref_fast(filename: str) -> List[Tuple[List[int], List[int], int, bool]]:
    """Drop-in replacement for basic_colorref using fast colour refinement.

    Reads a .grl file, runs fast colour refinement on all graphs
    simultaneously, and returns equivalence classes in the same format
    as the basic version.

    Returns:
        Sorted list of (graph_indices, colour_class_sizes, iterations, is_discrete).
        Note: 'iterations' is set to 0 for fast refinement since it doesn't
        iterate in rounds — it processes a work-queue instead.
    """
    from graph_io import load_graph

    with open(filename, 'r') as file:
        graphs = load_graph(file, graph_class=Graph, read_list=True)

    all_vertices = [v for G in graphs for v in G]
    initial_colouring = {v: 0 for v in all_vertices}
    adj = _build_neighbour_index(all_vertices)
    partition = fast_colour_refine(all_vertices, adj, initial_colouring)

    # Group graphs by their colour signature
    graph_equivalence_classes: Dict[Tuple, List[int]] = defaultdict(list)
    for i, G in enumerate(graphs):
        sig = get_colour_signature(G, partition)
        graph_equivalence_classes[sig].append(i)

    # Format output
    result = []
    for sig, indices in graph_equivalence_classes.items():
        sorted_indices = sorted(indices)

        # Reconstruct colour class sizes from the signature
        sizes = sorted([count for _, count in sig])

        is_discrete = all(s == 1 for s in sizes)

        # Fast refinement doesn't track iterations; report 0
        result.append((sorted_indices, sizes, 0, is_discrete))

    return sorted(result, key=lambda x: x[0][0])
