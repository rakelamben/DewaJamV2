import math


RI = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}


def build_matrix(pairs: dict[tuple[int, int], float], size: int) -> list[list[float]]:
    if size < 1:
        raise ValueError("Ukuran matriks AHP tidak valid.")
    matrix = [[1.0 if row == col else 0.0 for col in range(size)] for row in range(size)]
    for row in range(size):
        for col in range(row + 1, size):
            value = pairs.get((row, col))
            if value is None:
                raise ValueError(f"Pairwise ({row}, {col}) belum diisi.")
            if not math.isfinite(value) or value <= 0:
                raise ValueError("Nilai pairwise harus berupa angka positif.")
            matrix[row][col] = float(value)
            matrix[col][row] = 1.0 / float(value)
    return matrix


def compute_weights(matrix: list[list[float]]) -> list[float]:
    size = len(matrix)
    if size == 0 or any(len(row) != size for row in matrix):
        raise ValueError("Matriks AHP harus persegi dan tidak kosong.")
    column_totals = [sum(matrix[row][col] for row in range(size)) for col in range(size)]
    if any(total <= 0 for total in column_totals):
        raise ValueError("Jumlah kolom matriks AHP harus positif.")
    weights = [
        sum(matrix[row][col] / column_totals[col] for col in range(size)) / size
        for row in range(size)
    ]
    total = sum(weights)
    return [weight / total for weight in weights]


def consistency(matrix: list[list[float]], weights: list[float]) -> tuple[float, float, float]:
    size = len(matrix)
    if len(weights) != size or not weights or any(weight <= 0 for weight in weights):
        raise ValueError("Bobot AHP tidak valid.")
    weighted_sum = [sum(matrix[row][col] * weights[col] for col in range(size)) for row in range(size)]
    lambda_max = sum(weighted_sum[row] / weights[row] for row in range(size)) / size
    ci = 0.0 if size <= 2 else (lambda_max - size) / (size - 1)
    ri = RI.get(size)
    cr = 0.0 if size <= 2 or not ri else ci / ri
    return lambda_max, ci, cr
