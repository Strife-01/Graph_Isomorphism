#!/usr/bin/env python3
"""Generate threepaths benchmark instances.

A threepaths graph of size n consists of 3 disjoint paths, each of
length approximately n/3. The total number of vertices is n.

These are the standard benchmark for demonstrating linear-time
performance of Hopcroft-style fast partition refinement.
"""

import os
from graph import Graph, Edge
from graph_io import save_graph

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
SIZES = [5, 10, 20, 40, 80, 160, 320, 640, 1280, 2560, 5120, 10240]


def make_threepaths(n: int) -> Graph:
    """Create a graph with 3 disjoint paths totalling n vertices."""
    g = Graph(directed=False, n=n)
    verts = list(g.vertices)

    # Split n vertices into 3 roughly equal paths
    path_lens = [n // 3, n // 3, n - 2 * (n // 3)]
    offset = 0
    for plen in path_lens:
        for i in range(plen - 1):
            g.add_edge(Edge(verts[offset + i], verts[offset + i + 1]))
        offset += plen

    return g


def main():
    for size in SIZES:
        filename = os.path.join(OUTPUT_DIR, f"threepaths{size}.gr")
        g = make_threepaths(size)
        with open(filename, "w") as f:
            save_graph(g, f)
        print(f"Generated threepaths{size}.gr ({size} vertices, {len(g.edges)} edges)")


if __name__ == "__main__":
    main()
