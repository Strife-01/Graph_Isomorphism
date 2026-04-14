"""
Permutation group utilities for automorphism counting.

Provides a lightweight Permutation class and the algebraic machinery
needed to avoid enumerating every automorphism:

  * Orbit and transversal computation   (Algorithm 10, Section 5.5.4)
  * Stabiliser chain via Schreier-Sims  (Theorem 5.19)
  * Group order via orbit-stabiliser    (Proposition 5.18)
  * Membership testing via sifting       (Proposition 5.20)

All permutations act on abstract elements (vertex objects).  Composition
follows the reader's convention: (p * q)(x) = p(q(x)).
"""

from __future__ import annotations
from collections import deque
from typing import Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Permutation
# ---------------------------------------------------------------------------

class Permutation:
    """A bijection on a finite set, stored as a dictionary.

    Only non-fixed-point mappings are stored, so the identity permutation
    is represented by an empty dict.
    """

    __slots__ = ("_map", "_hash")

    def __init__(self, mapping: Optional[Dict] = None):
        """Create a permutation from an explicit mapping dict.

        Only non-fixed-point entries are stored: if mapping[k] == k,
        that entry is dropped.  Passing ``None`` or ``{}`` gives the
        identity permutation.

        Args:
            mapping:  Dict of element → image.  ``None`` for identity.
        """
        if mapping is None:
            self._map: Dict = {}
        else:
            self._map = {k: v for k, v in mapping.items() if k != v}
        self._hash: Optional[int] = None

    def __call__(self, x):
        """Apply the permutation: return σ(x)."""
        return self._map.get(x, x)

    def __mul__(self, other: Permutation) -> Permutation:
        """Compose: (self * other)(x) = self(other(x))."""
        keys = set(self._map) | set(other._map)
        return Permutation({k: self(other(k)) for k in keys})

    def inverse(self) -> Permutation:
        """Return σ⁻¹."""
        return Permutation({v: k for k, v in self._map.items()})

    def is_identity(self) -> bool:
        return len(self._map) == 0

    @property
    def support(self) -> Set:
        """Set of elements moved by this permutation."""
        return set(self._map.keys())

    def __eq__(self, other):
        if not isinstance(other, Permutation):
            return NotImplemented
        return self._map == other._map

    def __hash__(self):
        if self._hash is None:
            self._hash = hash(frozenset(self._map.items()))
        return self._hash

    def __repr__(self):
        if self.is_identity():
            return "Permutation()"
        cycles = self._cycle_notation()
        return "".join(f"({' '.join(str(x) for x in c)})" for c in cycles)

    def _cycle_notation(self) -> List[List]:
        """Return the permutation in cycle notation as a list of cycles.

        Each cycle is a list of elements.  Fixed points are omitted.
        Cycles are sorted by their smallest element for deterministic
        output.
        """
        visited: Set = set()
        cycles: List[List] = []
        for k in sorted(self._map, key=str):
            if k in visited:
                continue
            cycle = []
            x = k
            while x not in visited:
                visited.add(x)
                cycle.append(x)
                x = self(x)
            if len(cycle) > 1:
                cycles.append(cycle)
        return cycles


IDENTITY = Permutation()


# ---------------------------------------------------------------------------
# Orbit and transversal  (Algorithm 10)
# ---------------------------------------------------------------------------

def orbit_and_transversal(generators: List[Permutation],
                          alpha) -> Tuple[Set, Dict]:
    """Compute the orbit of *alpha* under ⟨generators⟩ and an orbit
    transversal.

    Returns:
        (orbit, transversal) where transversal[β] is a permutation
        mapping alpha to β.
    """
    orbit: Set = {alpha}
    transversal: Dict = {alpha: IDENTITY}
    queue: deque = deque([alpha])

    while queue:
        beta = queue.popleft()
        for g in generators:
            gamma = g(beta)
            if gamma not in orbit:
                orbit.add(gamma)
                transversal[gamma] = g * transversal[beta]
                queue.append(gamma)

    return orbit, transversal


# ---------------------------------------------------------------------------
# Stabiliser chain  (Schreier-Sims)
# ---------------------------------------------------------------------------

class _StabiliserLevel:
    """One level of a stabiliser chain.

    Stores the base point, orbit, transversal and generators for the
    stabiliser subgroup at this level.
    """
    __slots__ = ("alpha", "orbit", "transversal", "generators")

    def __init__(self, alpha, generators: List[Permutation]):
        """Build one level of the stabiliser chain.

        Computes the orbit and transversal of *alpha* under
        *generators* immediately on construction.

        Args:
            alpha:       The base point for this level.
            generators:  Generating set for the group at this level.
        """
        self.alpha = alpha
        self.generators = list(generators)
        self.orbit, self.transversal = orbit_and_transversal(
            self.generators, alpha
        )


def _build_chain(generators: List[Permutation],
                 base: List) -> List[_StabiliserLevel]:
    """Build a stabiliser chain for ⟨generators⟩ using the given base.

    Each level i represents G^(i) = Stab(base[0], ..., base[i-1]),
    with G^(0) = G.

    Uses Schreier generators with sifting to keep generator lists small.
    """
    chain: List[_StabiliserLevel] = []
    current_gens = list(generators)

    for alpha in base:
        if not current_gens:
            break

        level = _StabiliserLevel(alpha, current_gens)
        chain.append(level)

        # Compute Schreier generators for the stabiliser of alpha,
        # but sift them through deeper levels to avoid redundancy
        next_gens: List[Permutation] = []
        seen: Set[Permutation] = set()

        for beta in level.orbit:
            u_beta = level.transversal[beta]
            for g in level.generators:
                gamma = g(beta)
                u_gamma = level.transversal[gamma]
                schreier = u_gamma.inverse() * g * u_beta
                if not schreier.is_identity() and schreier not in seen:
                    seen.add(schreier)
                    next_gens.append(schreier)

        current_gens = next_gens

    return chain


def _choose_base(generators: List[Permutation],
                 elements: List) -> List:
    """Choose a base — a sequence of elements whose pointwise stabiliser
    is trivial.  We pick elements that are moved by the generators."""
    base = []
    moved = set()
    for g in generators:
        moved |= g.support

    # Order by elements list, taking only moved elements
    for e in elements:
        if e in moved:
            base.append(e)

    return base


# ---------------------------------------------------------------------------
# Group order  (Proposition 5.18)
# ---------------------------------------------------------------------------

def group_order(generators: List[Permutation],
                elements: List) -> int:
    """Compute |⟨generators⟩| using a stabiliser chain.

    The order is the product of orbit sizes at each level of the chain:
    |G| = |orbit_1| × |orbit_2| × ... × |orbit_k|

    Args:
        generators:  Generating set of the group.
        elements:    The elements the group acts on (vertices).

    Returns:
        The order of the group.
    """
    if not generators:
        return 1

    base = _choose_base(generators, elements)
    if not base:
        return 1

    chain = _build_chain(generators, base)

    order = 1
    for level in chain:
        order *= len(level.orbit)

    return order


# ---------------------------------------------------------------------------
# Membership testing  (Proposition 5.20 — Sifting)
# ---------------------------------------------------------------------------

def is_member(perm: Permutation,
              generators: List[Permutation],
              elements: List) -> bool:
    """Test whether *perm* ∈ ⟨generators⟩ by sifting through a
    stabiliser chain.

    Args:
        perm:        The permutation to test.
        generators:  Generating set of the group.
        elements:    Elements the group acts on.

    Returns:
        True iff *perm* belongs to the group.
    """
    if perm.is_identity():
        return True
    if not generators:
        return False

    base = _choose_base(generators, elements)
    chain = _build_chain(generators, base)

    current = perm
    for level in chain:
        beta = current(level.alpha)
        if beta not in level.orbit:
            return False
        u_beta = level.transversal[beta]
        current = u_beta.inverse() * current
        if current.is_identity():
            return True

    return current.is_identity()
