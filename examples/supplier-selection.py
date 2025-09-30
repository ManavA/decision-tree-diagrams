"""Rank suppliers on a 0–100 scale and save a printable decision table."""

from decision_tree_diagrams import Alternative, Criterion, render_table, score_table

criteria = [
    Criterion("Delivery reliability", 3),
    Criterion("Service coverage", 2),
    Criterion("Unit cost rating", 1),
]
suppliers = [
    Alternative("Regional supplier", [90, 75, 60]),
    Alternative("National distributor", [85, 80, 65]),
    Alternative("Local wholesaler", [70, 85, 85]),
    Alternative("Direct import", [95, 95, 90], feasible=False),
]

if __name__ == "__main__":
    for result in score_table(criteria, suppliers):
        rank = result.rank if result.rank is not None else "infeasible"
        print(f"{result.alternative.label}: {result.score:.2f} ({rank})")
    figure = render_table(criteria, suppliers, title="Supplier selection")
    figure.savefig("supplier-selection.pdf")
