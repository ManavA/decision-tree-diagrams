import unittest

from decision_tree_diagrams import Branch, Chance, Decision, Terminal, render


class DrawingTests(unittest.TestCase):
    def test_mixed_depth_aligns_terminal_values_in_each_style(self):
        demand = Chance("Demand", (
            Branch(Terminal("Busy", 30), probability=0.99999, label="Strong"),
            Branch(Terminal("Quiet", 40), probability=0.00001, label="Weak"),
        ))
        tree = Decision("Choose", (
            Branch(Terminal("Fixed", 80), value=5, label="Reserve"),
            Branch(demand, label="Wait"),
        ))
        for style in ("classic", "modern", "top-down"):
            with self.subTest(style=style):
                figure = render(tree, units="USD", style=style)
                labels = {label.get_text(): label.xy for label in figure.axes[0].texts}
                coordinate = 1 if style == "top-down" else 0
                value_positions = {labels[f"{value} USD"][coordinate] for value in (30, 40, 80)}
                self.assertEqual(len(value_positions), 1)
                text = " ".join(labels)
                self.assertIn("0.001%", text)
                self.assertIn("5 USD on edge", text)

    def test_long_labels_fit_without_overlapping_in_each_style(self):
        from matplotlib.backends.backend_agg import FigureCanvasAgg

        tree = Decision("Choose a replacement supplier", [
            Branch(
                Terminal("Maximum total acquisition and installation costs", 123456789),
                label="Purchase immediately from the preferred vendor",
            ),
            Branch(Terminal("Supplier negotiation", 200), label="Renegotiate existing terms"),
        ])
        for style in ("classic", "modern", "top-down"):
            for title in (None, "Compare options for replacing a supplier"):
                with self.subTest(style=style, title=title):
                    figure = render(tree, style=style, title=title)
                    canvas = FigureCanvasAgg(figure)
                    canvas.draw()
                    renderer = canvas.get_renderer()
                    texts = [*figure.texts, *figure.axes[0].texts]
                    boxes = [(text.get_text(), text.get_window_extent(renderer)) for text in texts]
                    for index, (label, box) in enumerate(boxes):
                        self.assertGreaterEqual(box.x0, 2, label)
                        self.assertGreaterEqual(box.y0, 2, label)
                        self.assertLessEqual(box.x1, figure.bbox.x1 - 2, label)
                        self.assertLessEqual(box.y1, figure.bbox.y1 - 2, label)
                        for other_label, other_box in boxes[index + 1:]:
                            self.assertFalse(box.overlaps(other_box), (label, other_label))
