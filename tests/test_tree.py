import unittest

from decision_tree_diagrams import Branch, Chance, Decision, Terminal, evaluate


class EvaluationTests(unittest.TestCase):
    def test_rolls_back_nested_tree_with_fees_ties_and_zero_probability(self):
        gamble = Chance("Demand", (
            Branch(Terminal("High", 10), probability=0.25, value=2),
            Branch(Terminal("Low", 4), probability=0.75),
            Branch(Terminal("Impossible", 100), probability=0),
        ))
        root = Decision("Choose", (
            Branch(gamble, value=2),
            Branch(Terminal("Fixed", 8)),
            Branch(Terminal("Expensive", 9)),
        ))

        lowest = evaluate(root)
        self.assertEqual(lowest.expected_value, 8)
        self.assertEqual(lowest.chosen_edges, (0, 1))
        self.assertEqual(lowest.children[0].expected_value, 6)
        self.assertEqual(lowest.children[0].children[2].expected_value, 100)

        highest = evaluate(root, objective="max")
        self.assertEqual(highest.expected_value, 9)
        self.assertEqual(highest.chosen_edges, (2,))

    def test_rejects_invalid_tree_or_objective(self):
        leaf = Terminal("End", 1)
        for tree, error in (
            (Decision("Start", (Branch(leaf, probability=1),)), "decision branch"),
            (Chance("Start", (Branch(leaf, probability=-1),)), "between 0 and 1"),
            (Chance("Start", (Branch(leaf, probability=0.9),)), "sum to 1"),
            (Chance("Start", (Branch(leaf),)), "probability"),
            (Decision("Start", ()), "at least one"),
            (Terminal("End", float("nan")), "finite"),
            (Decision("Start", (Branch(leaf, value=float("inf")),)), "finite"),
        ):
            with self.subTest(tree=tree), self.assertRaisesRegex(ValueError, error):
                evaluate(tree)
        with self.assertRaisesRegex(ValueError, "objective"):
            evaluate(leaf, "median")
