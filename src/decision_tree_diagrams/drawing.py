"""Matplotlib rendering with standalone figures."""

from __future__ import annotations

from dataclasses import dataclass, field
from textwrap import fill

from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextToPath

from .model import Branch, Chance, Decision, Evaluation, Node, Terminal, evaluate


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


def _wrap_title(title: str, width_inches: float) -> str:
    font = FontProperties(size=15, weight="semibold")
    measure = TextToPath()
    limit = max(15, width_inches * 72)
    for columns in range(min(len(title), max(1, int(limit / 6))), 0, -1):
        wrapped = fill(title, columns)
        if all(measure.get_text_width_height_descent(line, font, False)[0] <= limit
               for line in wrapped.splitlines()):
            return wrapped
    return title


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
    ink = "#233341"
    accent = "#963e30" if classic else "#07665a"
    muted = "#58636b"
    neutral = "#829099"
    background = "white" if classic else "#f7fafb"
    levels = max(depth, 1)
    rows = max(leaves - 1, 1)
    automatic_size = figure_size is None
    if automatic_size:
        if vertical:
            figure_size = (max(5.8, leaves * 2.15), max(2.8, levels * 1.58 + 1.25))
        else:
            figure_size = (max(6.2, levels * 3.40 + 3.7), max(2.25, leaves * 0.75 + 0.85))
    depth_inches = figure_size[1 if vertical else 0] * 0.88 / (levels + 1.44)
    leaf_inches = figure_size[0 if vertical else 1] * 0.88 / (rows + 1.2)
    font = min(10, max(4, leaf_inches * (22 if vertical else 23)), max(4, depth_inches * 8))

    def money(value: float) -> str:
        if units and units.startswith("$"):
            number = f"{abs(value):,.2f}".rstrip("0").rstrip(".")
            sign = "-" if value < 0 else ""
            return f"{sign}${number}{units[1:]}"
        return f"{value:,.6g} {units}" if units else f"{value:,.6g}"

    def wrapped(words: str, inches: float) -> str:
        return fill(words, max(7, int(inches * 125 / font)))

    def branch_text(branch: Branch, rejected: bool) -> str:
        name = f"//  {branch.label}".rstrip() if classic and rejected else branch.label
        details = []
        if branch.probability is not None:
            percent = branch.probability * 100
            if 0 < percent < 0.01:
                details.append(f"{percent:.3g}%")
            else:
                rounded = f"{percent:.2f}".rstrip("0").rstrip(".")
                details.append("<100%" if rounded == "100" and percent < 100 else rounded + "%")
        if branch.value:
            details.append(f"{money(float(branch.value))} on edge")
        width = leaf_inches * 0.78 if vertical else depth_inches * 0.43
        return "\n".join(wrapped(part, width) for part in (name, " · ".join(details)) if part)

    def line_count(words: str) -> int:
        return words.count("\n") + 1 if words else 0

    node_width = leaf_inches * 0.82 if vertical else depth_inches * 0.56
    terminal_width = leaf_inches * 0.84 if vertical else depth_inches * 0.55
    longest_branch = longest_node = longest_terminal = 1
    pending = [placed]
    while pending:
        item = pending.pop()
        node = item.node
        if isinstance(node, Terminal):
            longest_terminal = max(longest_terminal, line_count(wrapped(node.label, terminal_width)))
        else:
            longest_node = max(longest_node, line_count(wrapped(node.label, node_width)))
            for index, branch in enumerate(node.branches):
                rejected = isinstance(node, Decision) and index not in item.result.chosen_edges
                longest_branch = max(longest_branch, line_count(branch_text(branch, rejected)))
            pending.extend(item.children)

    width, height = figure_size
    title_text = _wrap_title(title, width * 0.93) if title else ""
    top_margin = 0.10
    if title_text:
        top_margin += 0.12 + line_count(title_text) * 18 / 72
    bottom_margin = height * 0.06
    plot_height = height * 0.88
    terminal_height = longest_terminal * font * 1.15 / 72
    terminal_value_offset = max(0.36, 0.25 + terminal_height)
    if automatic_size:
        branch_height = longest_branch * font * 0.88 * 1.15 / 72
        node_height = longest_node * font * 1.15 / 72
        if vertical:
            level_span = levels + 0.94
            level_spacing = max(
                plot_height / level_span,
                (branch_height / 2 + node_height + 0.14) / 0.36,
            )
            footer = max(0.52, (terminal_value_offset + 0.12) / level_spacing)
            plot_height = (levels + 0.42 + footer) * level_spacing
            height = top_margin + plot_height + bottom_margin
        else:
            row_span = rows + 1.2
            row_spacing = max(plot_height / row_span, branch_height + 0.14, terminal_height + 0.08)
            top_margin += max(0, max(branch_height, node_height, terminal_height / 2)
                              + 0.10 - 0.62 * row_spacing)
            plot_height = row_span * row_spacing
            height = top_margin + plot_height + bottom_margin
    else:
        plot_height = max(height - top_margin - bottom_margin, height * 0.4)

    figure = Figure(figsize=(width, height), facecolor=background)
    axis = figure.add_axes((0.025, bottom_margin / height, 0.95, plot_height / height))
    axis.set_axis_off()
    if title_text:
        figure.text(
            0.033, 1 - 0.10 / height, title_text, color=ink, fontsize=15,
            weight="semibold", va="top", parse_math=False, usetex=False,
        )
    if vertical:
        axis.set_xlim(-0.54, rows + 0.54)
        axis.set_ylim(levels + (footer if automatic_size else 0.52), -0.42)
    else:
        axis.set_xlim(-0.37, levels + 1.07)
        axis.set_ylim(rows + 0.58, -0.62)

    def point(level: float, row: float) -> tuple[float, float]:
        return (row, level) if vertical else (level, row)

    def label(level, row, words, *, color=ink, weight="normal", ha="center",
              va="center", dy=0, size=1, boxed=False):
        if words:
            axis.annotate(
                words, point(level, row), xytext=(0, dy), textcoords="offset points",
                ha=ha, va=va, color=color, fontsize=font * size, fontweight=weight,
                linespacing=1.12, zorder=4, parse_math=False, usetex=False,
                bbox={"facecolor": background, "edgecolor": "none", "pad": 1.8} if boxed else None,
            )

    def draw(item: _Placed) -> None:
        node = item.node
        level, row = item.depth, item.row
        if isinstance(node, Terminal):
            level = depth
            axis.plot(*point(level, row), "o", color=accent, markersize=4, zorder=3)
            if vertical:
                label(level, row, wrapped(node.label, terminal_width), weight="semibold",
                      va="top", dy=-8)
                label(level, row, money(item.result.expected_value), color=accent,
                      weight="semibold", va="center", dy=-terminal_value_offset * 72)
            else:
                label(level + 0.05, row, wrapped(node.label, terminal_width),
                      ha="left")
                label(level + 1.02, row, money(item.result.expected_value), color=accent,
                      weight="semibold", ha="right")
            return

        edges = list(enumerate(zip(node.branches, item.children)))
        if isinstance(node, Decision):
            edges.sort(key=lambda edge: edge[0] in item.result.chosen_edges)
        max_offset = max(abs(child.row - row) for child in item.children)
        for index, (branch, child) in edges:
            selected = isinstance(node, Decision) and index in item.result.chosen_edges
            rejected = isinstance(node, Decision) and not selected
            zero = isinstance(node, Chance) and branch.probability == 0
            child_level = depth if isinstance(child.node, Terminal) else child.depth
            if classic:
                # Bend outer branches earlier so they clear inner routes.
                fraction = abs(child.row - row) / max_offset if max_offset else 0
                bend = level + 0.39 - 0.25 * fraction
                route = [(level, row), (bend, row), (bend, child.row), (child_level, child.row)]
            else:
                shoulder = level + (0.48 if vertical else 0.42)
                route = [(level, row), (shoulder, child.row), (child_level, child.row)]
            color = accent if selected else neutral if rejected or zero else ink
            axis.plot(*zip(*(point(*anchor) for anchor in route)), color=color,
                      linewidth=1.8 if selected else 0.85, linestyle="--" if zero else "-",
                      zorder=2 if selected else 1)
            edge_text = branch_text(branch, rejected)
            label(level + (0.64 if vertical else 0.76), child.row, edge_text,
                  color=accent if selected else muted if rejected or zero else ink,
                  ha="center" if vertical else "right",
                  va="center" if vertical else "bottom", dy=0 if vertical else 3,
                  size=0.88, boxed=True)
            draw(child)

        marker = "s" if isinstance(node, Decision) else "o"
        axis.plot(*point(level, row), marker=marker, markersize=6.5, markeredgecolor=ink,
                  markerfacecolor=background, markeredgewidth=1.2, zorder=3)
        label(level, row, wrapped(node.label, node_width), weight="semibold", va="bottom", dy=6, boxed=True)
        label(level, row, money(item.result.expected_value), color=accent, va="top", dy=-6,
              boxed=True)

    if not vertical and leaves > 1:
        label(depth + 1.02, -0.46, "Terminal value", color=muted, size=0.79, ha="right")
    draw(placed)
    return figure
