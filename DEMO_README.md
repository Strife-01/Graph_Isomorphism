# Demo Instructions — Graph Isomorphism Project

## Setup

No external dependencies. Only Python 3.10+ and the standard library are needed.

```
cd /path/to/Graph_Isomorphism
```

## Running the Solver

The main entry point is `branching.py`. It auto-detects the problem type from the filename:

```bash
# GI only (filename contains "GI")
python3 branching.py path/to/instanceGI.grl

# #Aut only (filename contains "Aut")
python3 branching.py path/to/instanceAut.grl

# Both GI and #Aut (filename contains "GIAut")
python3 branching.py path/to/instanceGIAut.grl

# Single graph .gr file (defaults to #Aut)
python3 branching.py path/to/instance.gr
```

## Running on a Folder of Instances

```bash
for f in SampleGraphsBasicColourRefinement/*.grl; do
    echo "=== $f ==="
    python3 branching.py "$f"
    echo
done
```

## Step-by-Step Demo for Delivery Session

### 1. Basic Instances (Category 6 — Pass)

Run each of the 10 basic instances. They should all produce correct output.

```bash
for f in test01GI.grl test02GI.grl test03GI.grl test04GI.grl \
         test05Aut.grl test06GIAut.grl test07GIAut.grl; do
    echo "=== $f ==="
    python3 branching.py "$f"
    echo
done
```

Expected output for each is in `test_solutions.txt`.

### 2. Fast Colour Refinement (+1 point)

Show linear scaling on threepaths instances:

```bash
python3 -c "
import time
from graph_io import load_graph
from graph import Graph
from fast_colorref import colour_refine_graphs

for size in [5, 10, 20, 40, 80, 160, 320, 640, 1280, 2560, 5120, 10240]:
    with open(f'threepaths{size}.gr') as f:
        G = load_graph(f, graph_class=Graph)
    t0 = time.time()
    colour_refine_graphs([G])
    print(f'threepaths{size:>5}: {time.time()-t0:.4f}s')
"
```

Scaling should be roughly linear (doubling size ~ doubling time).

### 3. Generating Sets + Pruning for #Aut (+1 point)

Show large automorphism counts computed quickly:

```bash
python3 branching.py bigtrees3.grl
# Expected: [0, 2]: 2772351862699137701073289910157312
#           [1, 3]: 462058643783189616845548318359552
# Should complete in seconds, not years.

python3 branching.py cubes6.grl
# Expected: [0, 1]: 96   [2, 3]: 46080

python3 branching.py wheelstar12.grl
# Expected: [0, 3]: 1935360   [1, 2]: 6718464
```

### 4. Tree/Forest Preprocessing (+1 point)

Show instant results on tree instances:

```bash
python3 branching.py trees11.grl
python3 branching.py trees90.grl
python3 branching.py bigtrees1.grl
python3 branching.py bigtrees2.grl
python3 branching.py bigtrees3.grl
python3 branching.py "small forest.gr"
```

All should complete in under 0.01s.

### 5. Bonus Instances

Run any provided bonus instances:

```bash
for f in *.grl *.gr; do
    echo "=== $f ==="
    timeout 180 python3 branching.py "$f"
    echo
done
```

## Timing a Specific Instance

```bash
python3 -c "
import time
from branching import solve
t0 = time.time()
solve('INSTANCE_FILE')
print(f'Time: {time.time()-t0:.2f}s')
"
```

## Module Overview

| File | Algorithm | Complexity |
|------|-----------|------------|
| `colorref.py` | Basic 1-WL colour refinement | O(n^2 m) |
| `fast_colorref.py` | Hopcroft-style partition refinement | O(m log n) |
| `branching.py` | Individualization-refinement + generating sets | Varies |
| `permutation.py` | Schreier-Sims, orbit-stabiliser, sifting | Polynomial |
| `preprocessing.py` | AHU trees, twins, components | O(n) for trees |
| `graph.py` | Graph data structure (provided) | — |
| `graph_io.py` | Graph I/O (provided) | — |
