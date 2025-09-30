"""Tree model and backward induction."""

from __future__ import annotations

from dataclasses import dataclass
from math import fsum, isclose, isfinite
from numbers import Real
from typing import Sequence, Union


@dataclass(frozen=True)
class Terminal:
    """An outcome with a numeric cost or payoff."""

    label: str
    value: float


@dataclass(frozen=True)
class Decision:
    """A choice among actions available at this node."""

    label: str
    branches: Sequence[Branch]


@dataclass(frozen=True)
class Chance:
    """Outcomes with conditional probabilities at this node."""

    label: str
    branches: Sequence[Branch]


Node = Union[Decision, Chance, Terminal]


@dataclass(frozen=True)
class Branch:
    """An edge with an optional probability, one-time value, and label."""

    child: Node
    probability: float | None = None
    value: float = 0.0
    label: str = ""


@dataclass(frozen=True)
class Evaluation:
    """Value from a node onward and child results in input branch order.

    Branch values include the immediate increment on that edge. Chosen edges
    are the zero-based indices of all optimal actions at a decision.
    """

    expected_value: float
    chosen_edges: tuple[int, ...] = ()
    children: tuple[Evaluation, ...] = ()
    branch_values: tuple[float, ...] = ()


def _number(value: object, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{context} must be a finite number")
    try:
        value = float(value)
    except OverflowError as exc:
        raise ValueError(f"{context} must be a finite number") from exc
    if not isfinite(value):
        raise ValueError(f"{context} must be a finite number")
    return value


def evaluate(root: Node, objective: str = "min") -> Evaluation:
    """Minimize expected cost or maximize expected payoff in a finite tree."""
    if objective not in ("min", "max"):
        raise ValueError("objective must be 'min' or 'max'")
    active = set()

    def visit(node, path: str) -> Evaluation:
        if not isinstance(node, (Decision, Chance, Terminal)):
            raise ValueError(f"{path} must be a Decision, Chance, or Terminal")
        if not isinstance(node.label, str):
            raise ValueError(f"{path} label must be a string")
        if isinstance(node, Terminal):
            return Evaluation(_number(node.value, f"{path} terminal value"))
        if id(node) in active:
            raise ValueError(f"{path} creates a cycle")
        if not isinstance(node.branches, Sequence) or not node.branches:
            raise ValueError(f"{path} must have at least one branch in a sequence")

        children, values, probabilities = [], [], []
        active.add(id(node))
        for index, branch in enumerate(node.branches):
            edge = f"{path} branch {index + 1}"
            if not isinstance(branch, Branch) or not isinstance(branch.label, str):
                raise ValueError(f"{edge} must be a Branch with a string label")
            if isinstance(node, Chance):
                probability = _number(branch.probability, f"{edge} probability")
                if not 0 <= probability <= 1:
                    raise ValueError(f"{edge} probability must be between 0 and 1")
                probabilities.append(probability)
            elif branch.probability is not None:
                raise ValueError(f"{edge}: a decision branch cannot have a probability")
            child = visit(branch.child, edge)
            increment = _number(branch.value, f"{edge} value")
            values.append(_number(increment + child.expected_value, f"{edge} total"))
            children.append(child)
        active.remove(id(node))

        chosen = ()
        if isinstance(node, Chance):
            if not isclose(fsum(probabilities), 1, rel_tol=0, abs_tol=1e-9):
                raise ValueError(f"{path} probabilities must sum to 1")
            try:
                expected = fsum(p * v for p, v in zip(probabilities, values))
            except OverflowError as exc:
                raise ValueError(f"{path} expected value must be finite") from exc
        else:
            expected = (min if objective == "min" else max)(values)
            chosen = tuple(i for i, value in enumerate(values)
                           if isclose(value, expected, rel_tol=1e-12, abs_tol=1e-12))
        return Evaluation(expected, chosen, tuple(children), tuple(values))

    return visit(root, "root")
