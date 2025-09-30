"""Matplotlib rendering with standalone figures."""

from __future__ import annotations

from dataclasses import dataclass, field
from textwrap import fill

from matplotlib import patheffects
from matplotlib.figure import Figure

from .model import Chance, Decision, Evaluation, Node, Terminal, evaluate


@dataclass
class _Placed:
    node: Node
    result: Evaluation
    depth: int
    row: float
    children: list[_Placed] = field(default_factory=list)


def _layout(root: Node, result: Evaluation) -> tuple[_Placed, int, int]:
    leaves = 0
    max_depth = 0

    def place(node: Node, evaluation: Evaluation, depth: int) -> _Placed:
        nonlocal leaves, max_depth
        max_depth = max(max_depth, depth)
        if isinstance(node, Terminal):
            leaf = _Placed(node, evaluation, depth, leaves)
            leaves += 1
            return leaf
        children = [place(branch.child, child, depth + 1)
                    for branch, child in zip(node.branches, evaluation.children)]
        middle = (children[0].row + children[-1].row) / 2
        return _Placed(node, evaluation, depth, middle, children)

    placed = place(root, result, 0)
    return placed, leaves, max_depth


def render(
    root: Node,
    *,
    objective: str = "min",
    style: str = "classic",
    title: str | None = None,
    units: str | None = None,
    figure_size: tuple[float, float] | None = None,
) -> Figure:
    """Draw a tree and return a Figure ready for savefig."""
    if style not in ("classic", "modern", "top-down"):
        raise ValueError("style must be 'classic', 'modern', or 'top-down'")
    result = evaluate(root, objective)
    placed, leaves, depth = _layout(root, result)
    vertical = style == "top-down"
    classic = style == "classic"
    ink = "#242829" if classic else "#183044"
    accent = "#9e4d41" if classic else "#17695f"
    muted = "#767e82"
    background = "white" if classic else "#f8fafb"
    if figure_size is None:
        if vertical:
            figure_size = (max(7, leaves * 1.45), max(3.2, depth * 1.25 + 1.3))
        else:
            figure_size = (max(7, depth * 2.25 + 2.8), max(2.5, leaves * 0.43 + 0.8))

    figure = Figure(figsize=figure_size, facecolor=background)
    axis = figure.add_axes((0.035, 0.055, 0.93, 0.83 if title else 0.90))
    axis.set_axis_off()
    if title:
        figure.text(
            0.035, 0.953, title, color=ink, fontsize=13, weight="semibold", va="top",
            parse_math=False, usetex=False,
        )

    columns = max(depth, 1)
    rows = max(leaves - 1, 1)
    depth_inches = figure_size[1 if vertical else 0] / (columns + 1)
    leaf_inches = figure_size[0 if vertical else 1] / (rows + 1)
    font = min(9, max(4, (leaf_inches * (30 if vertical else 32))))
    font = min(font, max(4, depth_inches * 9))
    row_padding = 0.75 if vertical else 0.65
    terminal_padding = 0.75 if vertical else 1.22
    axis.set_xlim((-row_padding, rows + row_padding) if vertical else (-0.66, columns + terminal_padding))
    axis.set_ylim((columns + terminal_padding, -0.45) if vertical else (rows + row_padding, -row_padding))

    def point(level: float, row: float) -> tuple[float, float]:
        return (row, level) if vertical else (level, row)

    def label(level, row, words, *, color=ink, weight="normal", align="center", above=False, below=False, clearance=3):
        if not words:
            return
        vertical_alignment = "bottom" if above else "top" if below else "center"
        axis.annotate(
            words, point(level, row), xytext=(0, clearance if above else -clearance if below else 0),
            textcoords="offset points", ha=align, va=vertical_alignment, color=color,
            fontsize=font, fontweight=weight, linespacing=1.05, zorder=4,
            parse_math=False, usetex=False,
            path_effects=[patheffects.withStroke(linewidth=1.4, foreground=background)],
        )

    def money(value: float) -> str:
        if units and units.startswith("$"):
            number = f"{abs(value):,.2f}".rstrip("0").rstrip(".")
            sign = "-" if value < 0 else ""
            return f"{sign}${number}{units[1:]}"
        return f"{value:,.6g} {units}" if units else f"{value:,.6g}"

    def wrapped(words: str, width: float = 1) -> str:
        if vertical:
            inches = leaf_inches
        else:
            inches = figure_size[0] * 0.93 / (columns + terminal_padding + 0.66)
        return fill(words, max(6, int(inches * width * 124 / font)))

    def node_level(item: _Placed) -> int:
        if not vertical and isinstance(item.node, Terminal):
            return depth
        return item.depth

    def draw(item: _Placed) -> None:
        node, level, row = item.node, node_level(item), item.row
        for i, (branch, child) in enumerate(zip(getattr(node, "branches", ()), item.children)):
            selected = isinstance(node, Decision) and i in item.result.chosen_edges
            rejected = isinstance(node, Decision) and not selected
            zero = isinstance(node, Chance) and branch.probability == 0
            bend = level + 0.19
            child_level = node_level(child)
            if classic:
                route = [point(level, row), point(bend, row), point(bend, child.row),
                         point(child_level, child.row)]
            else:
                route = [point(level, row), point(child_level, child.row)]
            edge_color = muted if rejected or zero else ink if classic else accent
            axis.plot(*zip(*route), color=edge_color, linewidth=1.25 if selected else 0.8,
                      linestyle="--" if zero else "-", zorder=1)
            edge_fraction = 0.64 if vertical else 0.53
            if classic:
                edge_level = child_level - 0.48 if isinstance(child.node, Terminal) else level + 0.43
            else:
                edge_level = level + (child_level - level) * edge_fraction
            fraction = (edge_level - level) / (child_level - level)
            edge_row = child.row if classic else row + fraction * (child.row - row)
            details = []
            if branch.label:
                details.append(branch.label)
            if branch.probability is not None:
                percent = branch.probability * 100
                if 0 < percent < 0.005:
                    details.append(f"{percent:.2g}%")
                else:
                    details.append(f"{percent:.2f}".rstrip("0").rstrip(".") + "%")
            if branch.value:
                details.append(f"{money(float(branch.value))} on edge")
            edge_text = " · ".join(details)
            if rejected and classic:
                edge_text = f"∕∕  {edge_text}".rstrip()
            text_color = accent if rejected and classic else edge_color
            label(edge_level, edge_row, wrapped(edge_text, 0.75 if classic or vertical else 1),
                  color=text_color, above=True, clearance=1.5)
            draw(child)

        terminal = isinstance(node, Terminal)
        marker = "o" if terminal or isinstance(node, Chance) else "s"
        axis.plot(*point(level, row), marker=marker, markersize=max(2.4, font * (0.50 if terminal else 0.8)),
                  markeredgecolor=accent if terminal else ink,
                  markerfacecolor=accent if terminal else background, zorder=3)
        if terminal and not vertical:
            label(level + 0.075, row, wrapped(f"{node.label} · {money(item.result.expected_value)}"),
                  color=accent, align="left")
        else:
            label(level, row, wrapped(node.label, 0.82 if classic else 1), weight="semibold", above=True)
            label(level, row, money(item.result.expected_value), color=accent, below=True)

    draw(placed)
    return figure
