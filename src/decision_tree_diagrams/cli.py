"""Command-line entry point."""

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .drawing import render
from .jsonio import load_json
from .model import evaluate


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate and draw decision trees.")
    commands = parser.add_subparsers(dest="command", required=True)
    inspection = commands.add_parser("evaluate", help="print rollback results as JSON")
    drawing = commands.add_parser("render", help="write an SVG, PDF, or PNG")
    for command in (inspection, drawing):
        command.add_argument("input", type=Path, help="JSON file containing the tree")
        command.add_argument("--objective", choices=("min", "max"), default="min")
    drawing.add_argument("output", type=Path, help="output path ending in .svg, .pdf, or .png")
    drawing.add_argument("--style", choices=("classic", "modern", "top-down"), default="classic")
    drawing.add_argument("--title")
    drawing.add_argument("--units")
    args = parser.parse_args()

    try:
        root = load_json(args.input)
        if args.command == "evaluate":
            print(json.dumps(asdict(evaluate(root, args.objective)), indent=2, allow_nan=False))
            return
        if args.output.suffix.lower() not in (".svg", ".pdf", ".png"):
            raise ValueError("output must have an .svg, .pdf, or .png extension")
        figure = render(root, objective=args.objective, style=args.style,
                        title=args.title, units=args.units)
        figure.savefig(args.output, dpi=180)
    except (ValueError, OSError, RecursionError) as exc:
        parser.error(str(exc))
