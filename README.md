# Graph Isomorphism Solver

Solves the **Graph Isomorphism (GI)** and **Automorphism Counting (#Aut)** problems.

**Requirements**: Python 3.10+ (no external dependencies)

For algorithm details, implementation notes, and performance analysis, see `documentation.pdf` (build with `pdflatex documentation.tex`).

---

## Usage

```bash
python3 branching.py <graph_file>
```

> **Note:** The files in `SampleGraphsBasicColourRefinement/` are also available as a zip archive.

The problem type is auto-detected from the filename:

| Filename pattern | What it does |
|-----------------|--------------|
| `*GI.grl` | Finds equivalence classes of isomorphic graphs |
| `*Aut.grl` | Counts automorphisms for each graph |
| `*GIAut.grl` | Both: equivalence classes + automorphism counts |
| `*.gr` | Single graph, counts automorphisms |
| Other `.grl` | Defaults to equivalence classes |

---

## Examples

### Find which graphs are isomorphic

```bash
$ python3 branching.py SampleGraphsBasicColourRefinement/colorref_smallexample_6_15.grl
Sets of isomorphic graphs:
[0, 1]
[2, 3]
[4, 5]
```

Graphs 0 and 1 are isomorphic to each other, graphs 2 and 3, and graphs 4 and 5.

### Find which graphs are isomorphic + count automorphisms

To compute both equivalence classes and automorphism counts, the filename must contain `GIAut`:

```bash
$ python3 branching.py tests_v2/test06GIAut.grl
Sets of isomorphic graphs with automorphisms:
[0, 1, 3, 4]: 384
[2]: 8
```

### Run on all sample instances

```bash
for f in SampleGraphsBasicColourRefinement/*.grl; do
    echo "=== $(basename $f) ==="
    python3 branching.py "$f"
    echo
done
```

### Time a specific instance

```bash
python3 -c "
import time
from branching import solve
t0 = time.time()
solve('SampleGraphsBasicColourRefinement/colorref_largeexample_6_960.grl')
print(f'Time: {time.time()-t0:.3f}s')
"
```

---

## Graph File Formats

### `.gr` — single graph

```
# Number of vertices:
5
# Edge list:
0,1
0,2
1,3
2,4
3,4
```

- First non-comment line: number of vertices (labelled 0 to n-1)
- Following lines: edges as `tail,head` (undirected)
- Optional edge weights: `tail,head:weight`
- Lines starting with `#` are comments

### `.grl` — list of graphs

```
4
0,1
0,2
1,3
--- Next graph:
4
0,1
0,3
1,2
```

Same format as `.gr`, but multiple graphs separated by `--- Next graph:` lines.

### Filename conventions

The filename tells the solver what to compute:

- **`GI`** in the name (e.g., `test03GI.grl`) — solve Graph Isomorphism
- **`Aut`** in the name (e.g., `test05Aut.grl`) — count automorphisms
- **`GIAut`** in the name (e.g., `test06GIAut.grl`) — both
- **`.gr` extension** — always treated as single-graph #Aut

---

## Project Files

| File | Description |
|------|------------|
| `branching.py` | **Main entry point.** Solver for GI and #Aut. Includes component decomposition for disconnected graphs and twin reduction integration |
| `fast_colorref.py` | Fast colour refinement (O(m log n), Hopcroft-style) |
| `colorref.py` | Basic colour refinement (O(n^2 m)) |
| `permutation.py` | Permutation group operations (orbits, stabiliser chains) |
| `preprocessing.py` | Tree/forest detection (AHU), twin detection & iterative reduction, component decomposition |
| `graph.py` | Graph data structure (provided by course) |
| `graph_io.py` | Graph file I/O (provided by course) |

---

## Building the Report

```bash
pdflatex documentation.tex
```
