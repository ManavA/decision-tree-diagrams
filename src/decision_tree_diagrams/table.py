"""Weighted comparison of alternatives against a common rating scale."""
from __future__ import annotations

from dataclasses import dataclass
from math import fsum, isclose
from textwrap import fill
from typing import Sequence

from matplotlib.figure import Figure

from .drawing import _wrap_title
from .model import _number


@dataclass(frozen=True)
class Criterion:
    """A named criterion with a nonnegative relative weight."""

    label: str
    weight: float


@dataclass(frozen=True)
class Alternative:
    """A named option with one 0–100 rating per criterion, higher is better."""

    label: str
    ratings: Sequence[float]
    feasible: bool = True


@dataclass(frozen=True)
class ScoredAlternative:
    """An alternative's weighted score and its rank among feasible options."""

    alternative: Alternative
    score: float
    rank: int | None


def _validate_labels(items: Sequence[Criterion | Alternative], field: str) -> None:
    labels = set()
    for item in items:
        label = item.label
        if not isinstance(label, str) or not label.strip():
            raise ValueError(f"each {field} needs a nonempty label")
        if label in labels:
            raise ValueError(f"duplicate {field} label: {label!r}")
        labels.add(label)


def _weights(criteria: Sequence[Criterion]) -> tuple[float, ...]:
    if not criteria or any(not isinstance(item, Criterion) for item in criteria):
        raise ValueError("provide at least one Criterion")
    _validate_labels(criteria, "criterion")
    weights = [_number(item.weight, f"{item.label!r} weight") for item in criteria]
    if min(weights) < 0 or max(weights) <= 0:
        raise ValueError("weights must be nonnegative, with at least one positive weight")
    largest = max(weights)
    scaled = [weight / largest for weight in weights]
    total = fsum(scaled)
    return tuple(weight / total for weight in scaled)


def score_table(
    criteria: Sequence[Criterion],
    alternatives: Sequence[Alternative],
) -> tuple[ScoredAlternative, ...]:
    """Rank feasible options by weighted score and append infeasible options in input order."""
    return _score_table(_weights(criteria), alternatives)


def _score_table(
    weights: tuple[float, ...],
    alternatives: Sequence[Alternative],
) -> tuple[ScoredAlternative, ...]:
    if not alternatives or any(not isinstance(item, Alternative) for item in alternatives):
        raise ValueError("provide at least one Alternative")
    _validate_labels(alternatives, "alternative")
    feasible = []
    infeasible = []
    for index, alternative in enumerate(alternatives):
        if not isinstance(alternative.feasible, bool):
            raise ValueError(f"{alternative.label!r} feasibility must be a boolean")
        if not isinstance(alternative.ratings, Sequence) or len(alternative.ratings) != len(weights):
            raise ValueError(f"{alternative.label!r} needs one rating per criterion")
        ratings = [_number(value, f"{alternative.label!r} rating") for value in alternative.ratings]
        if any(not 0 <= value <= 100 for value in ratings):
            raise ValueError(f"{alternative.label!r} ratings must be between 0 and 100")
        score = fsum(weight * rating for weight, rating in zip(weights, ratings))
        if alternative.feasible:
            feasible.append((index, score, alternative))
        else:
            infeasible.append(ScoredAlternative(alternative, score, None))

    feasible.sort(key=lambda row: -row[1])
    ranked = []
    tied_rows = []
    group_score = -1.0
    rank = 0
    for position, (index, score, alternative) in enumerate(feasible, start=1):
        if not isclose(score, group_score, rel_tol=0, abs_tol=1e-9):
            ranked.extend(result for _, result in sorted(tied_rows))
            rank, group_score, tied_rows = position, score, []
        tied_rows.append((index, ScoredAlternative(alternative, score, rank)))
    ranked.extend(result for _, result in sorted(tied_rows))
    return (*ranked, *infeasible)


def render_table(
    criteria: Sequence[Criterion],
    alternatives: Sequence[Alternative],
    *,
    title: str | None = None,
) -> Figure:
    """Print ratings, normalized weights, weighted totals and ranks in a Matplotlib figure."""
    weights = _weights(criteria)
    results = _score_table(weights, alternatives)
    headings = [
        "Alternative",
        *(f"{fill(item.label, 16)}\n{weight * 100:.5g}%"
          for item, weight in zip(criteria, weights)),
        "Weighted\nscore",
        "Rank",
        "Feasibility",
    ]
    rows = [
        [
            fill(result.alternative.label, 24),
            *(f"{float(rating):.5g}" for rating in result.alternative.ratings),
            f"{result.score:.2f}",
            str(result.rank) if result.rank is not None else "—",
            "Feasible" if result.alternative.feasible else "Infeasible",
        ]
        for result in results
    ]
    widths = [2.1, *([1.35] * len(criteria)), 1.0, 0.6, 1.15]
    heights = [max(cell.count("\n") + 1 for cell in row) * 0.16 + 0.22
               for row in [headings, *rows]]
    table_height = sum(heights)
    width = sum(widths) + 0.5
    title_text = _wrap_title(title, width - 0.5) if title else ""
    title_height = 0.6 + (title_text.count("\n") + 1) * 0.25 if title_text else 0.5
    height = table_height + title_height
    figure = Figure(figsize=(width, height), facecolor="white")
    if title_text:
        figure.text(0.25 / width, 1 - 0.21 / height, title_text, color="#233341",
                    fontsize=15, weight="semibold", va="top", parse_math=False, usetex=False)
    axis = figure.add_axes((0.25 / width, 0.25 / height, sum(widths) / width, table_height / height))
    axis.set_axis_off()
    table = axis.table(cellText=rows, colLabels=headings, cellLoc="center",
                       colWidths=[size / sum(widths) for size in widths], bbox=(0, 0, 1, 1))
    table.auto_set_font_size(False)
    for (row, column), cell in table.get_celld().items():
        cell.set_height(heights[row] / table_height)
        cell.set_edgecolor("#ccd7dc")
        cell.set_linewidth(0.5)
        cell_text = cell.get_text()
        cell_text.set_parse_math(False)
        cell_text.set_usetex(False)
        cell_text.set_fontsize(9)
        if row == 0:
            cell.set_facecolor("#233341")
            cell_text.set_color("white")
            cell_text.set_weight("semibold")
        else:
            result = results[row - 1]
            if result.rank == 1:
                cell.set_facecolor("#e3f2ed")
            elif row % 2 == 0:
                cell.set_facecolor("#f3f6f7")
            cell_text.set_color("#58636b" if result.rank is None else "#233341")
            if column in (len(widths) - 3, len(widths) - 2):
                cell_text.set_weight("semibold")
        if column == 0:
            cell_text.set_ha("left")
    return figure
