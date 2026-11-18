import math


def topsis(matrix: list[list[float]], weights: list[float], benefits: list[bool]) -> tuple[list[float], list[list[float]]]:
    if not matrix:
        return [], []
    row_size = len(matrix[0])
    if any(len(row) != row_size for row in matrix) or len(weights) != row_size or len(benefits) != row_size:
        raise ValueError("Ukuran matriks TOPSIS tidak konsisten.")
    weight_total = sum(weights)
    if not math.isclose(weight_total, 1.0, rel_tol=0.0, abs_tol=1e-3):
        raise ValueError("Jumlah bobot TOPSIS harus sama dengan 1.")
    weights = [weight / weight_total for weight in weights]

    norms = [math.sqrt(sum(row[col] ** 2 for row in matrix)) for col in range(row_size)]
    normalized = [[(row[col] / norms[col]) if norms[col] else 0.0 for col in range(row_size)] for row in matrix]
    weighted = [[normalized[row][col] * weights[col] for col in range(row_size)] for row in range(len(matrix))]
    positive = []
    negative = []
    for col in range(row_size):
        values = [row[col] for row in weighted]
        positive.append(max(values) if benefits[col] else min(values))
        negative.append(min(values) if benefits[col] else max(values))

    scores: list[float] = []
    for row in weighted:
        distance_positive = math.sqrt(sum((row[col] - positive[col]) ** 2 for col in range(row_size)))
        distance_negative = math.sqrt(sum((row[col] - negative[col]) ** 2 for col in range(row_size)))
        denominator = distance_positive + distance_negative
        scores.append(0.5 if denominator == 0 else distance_negative / denominator)
    return scores, weighted
