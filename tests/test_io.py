import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from decision_tree_diagrams import Branch, Chance, Terminal, evaluate, load_json, render


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


class FileTests(unittest.TestCase):
    def test_loads_example(self):
        result = evaluate(load_json(EXAMPLES / "inspect-or-replace.json"))
        self.assertEqual(result.expected_value, 131)
        self.assertEqual(result.chosen_edges, (1,))

    def test_rejects_unknown_json_fields(self):
        with tempfile.TemporaryDirectory() as work:
            source = Path(work) / "tree.json"
            source.write_text('{"type": "terminal", "label": "End", "value": 1, "extra": 0}',
                              encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unknown fields: extra"):
                load_json(source)

    def test_styles_export(self):
        root = load_json(EXAMPLES / "delivery-cost.json")
        with tempfile.TemporaryDirectory() as work:
            for style, ext, signature in (
                ("classic", "svg", b"<svg"),
                ("modern", "pdf", b"%PDF"),
                ("top-down", "png", b"\x89PNG"),
            ):
                with self.subTest(style=style):
                    destination = Path(work) / f"tree.{ext}"
                    render(root, style=style).savefig(destination)
                    self.assertIn(signature, destination.read_bytes()[:2048])

    def test_render_treats_labels_and_title_as_literal_text(self):
        literal = r"$\not_a_math_command$"
        figure = render(Terminal(literal, 5), title=literal)
        with tempfile.TemporaryDirectory() as work:
            target = Path(work) / "literal.svg"
            figure.savefig(target)
            self.assertIn(literal, target.read_text(encoding="utf-8"))

    def test_rare_positive_probability_is_distinct_from_zero(self):
        root = Chance("Risks", (
            Branch(Terminal("Rare", 8), probability=0.000001),
            Branch(Terminal("Common", 2), probability=0.999999),
        ))
        labels = {label.get_text() for label in render(root).axes[0].texts}
        self.assertIn("0.0001%", labels)
        self.assertNotIn("0%", labels)

    def test_command_evaluates_and_renders(self):
        source = EXAMPLES / "market-payoff.json"
        output = subprocess.check_output([
            sys.executable, "-m", "decision_tree_diagrams", "evaluate", str(source),
            "--objective", "max",
        ])
        self.assertEqual(json.loads(output)["expected_value"], 208.5)
        with tempfile.TemporaryDirectory() as work:
            target = Path(work) / "market.svg"
            subprocess.run([
                sys.executable, "-m", "decision_tree_diagrams", "render", str(source),
                str(target), "--objective", "max",
            ], check=True)
            self.assertIn("<svg", target.read_text(encoding="utf-8"))
