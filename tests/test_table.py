import unittest

from decision_tree_diagrams import Alternative, Criterion, score_table


class DecisionTableTests(unittest.TestCase):
    def test_ranks_weighted_ratings_with_ties_and_excludes_infeasible_alternatives(self):
        criteria = [Criterion("Reliability", 3), Criterion("Convenience", 1)]
        result = score_table(criteria, [
            Alternative("Standard", [60, 100]),
            Alternative("Unavailable", [95, 95], feasible=False),
            Alternative("Premium", [80, 80]),
            Alternative("Compact", [90, 50]),
        ])
        self.assertEqual(
            [(row.alternative.label, row.score, row.rank) for row in result],
            [("Premium", 80, 1), ("Compact", 80, 1), ("Standard", 70, 3),
             ("Unavailable", 95, None)],
        )

    def test_rejects_unscorable_tables(self):
        for criteria, alternatives, message in (
            ([Criterion("Cost", 0)], [Alternative("One", [0])], "positive"),
            ([Criterion("Cost", 1)], [Alternative("One", [101])], "between 0 and 100"),
            ([Criterion("Cost", 1)], [Alternative("One", [])], "rating per criterion"),
            ([Criterion("Cost", 1), Criterion("Cost", 2)], [Alternative("One", [0, 0])],
             "duplicate criterion"),
            ([Criterion("Cost", 1)], [Alternative("One", [0]), Alternative("One", [10])],
             "duplicate alternative"),
        ):
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                score_table(criteria, alternatives)

    def test_no_feasible_alternative_leaves_all_rows_unranked(self):
        result = score_table([Criterion("Cost", 1)], [Alternative("One", [0], feasible=False)])
        self.assertEqual(result[0].score, 0)
        self.assertIsNone(result[0].rank)

    def test_draws_weights_scores_ranks_and_feasibility(self):
        from decision_tree_diagrams import render_table

        figure = render_table(
            [Criterion("Reliability", 3), Criterion("Convenience", 1)],
            [Alternative("Standard", [80, 80]), Alternative("Delayed", [90, 90], False)],
            title="Select a supplier",
        )
        cells = figure.axes[0].tables[0].get_celld()
        text = {cell.get_text().get_text() for cell in cells.values()}
        self.assertIn("Reliability\n75%", text)
        self.assertIn("Convenience\n25%", text)
        self.assertIn("80.00", text)
        self.assertIn("1", text)
        self.assertIn("Infeasible", text)

    def test_prints_fractional_ratings_and_keeps_long_title_in_figure(self):
        from fractions import Fraction

        from matplotlib.backends.backend_agg import FigureCanvasAgg

        from decision_tree_diagrams import render_table

        figure = render_table(
            [Criterion("Reliability", 1)], [Alternative("Option A", [Fraction(9, 2)])],
            title="Weighted decision table for replacing an unavailable supplier on short notice",
        )
        canvas = FigureCanvasAgg(figure)
        canvas.draw()
        title = figure.texts[0].get_window_extent(canvas.get_renderer())
        self.assertLess(title.x1, figure.bbox.x1)
        self.assertGreater(title.y0, figure.axes[0].bbox.y1)
        ratings = figure.axes[0].tables[0].get_celld()[1, 1].get_text()
        self.assertEqual(ratings.get_text(), "4.5")
