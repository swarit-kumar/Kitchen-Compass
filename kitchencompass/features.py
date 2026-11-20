"""Evidence calculations. None denotes an unavailable feature."""
from collections import defaultdict
from math import fsum, sqrt


def flavor_jaccard(first, second):
    if not first or not second:
        return None
    return len(first & second) / len(first | second)


def mean_context(retained_ids, vectors):
    ids = sorted(set(retained_ids))
    totals = defaultdict(float)
    for ingredient_id in ids:
        for key, value in vectors[ingredient_id].items():
            totals[key] += value
    return {key: value / len(ids) for key, value in totals.items()}


def cosine(left, right):
    norm = sqrt(fsum(v * v for v in left.values()) * fsum(v * v for v in right.values()))
    if not norm:
        return None
    dot = fsum(value * right.get(key, 0.0) for key, value in left.items())
    return min(1.0, max(0.0, dot / norm))


def weighted_score(components, weights, selected):
    available = [key for key in selected if components[key] is not None]
    if not available:
        return None
    if len(available) == 1:
        return components[available[0]]
    return (fsum(weights[key] * components[key] for key in available)
            / fsum(weights[key] for key in available))
