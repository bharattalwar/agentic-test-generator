"""Sample module whose functions return 'ugly' repeating-decimal floats — a
classic tripwire for naive test assertions (floating-point equality)."""


def mean(numbers):
    """Return the arithmetic mean of a non-empty list of numbers."""
    return sum(numbers) / len(numbers)


def percentage(part, whole):
    """Return `part` as a percentage of `whole`. e.g. percentage(1, 3) -> 33.333..."""
    return part / whole * 100
