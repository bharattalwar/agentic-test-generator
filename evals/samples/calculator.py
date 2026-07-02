"""A tiny sample module for the agent to generate tests against.

It deliberately includes an edge case (division by zero raises an error) so we
can see whether the generated tests are thorough.
"""


def add(a, b):
    return a + b


def subtract(a, b):
    return a - b


def multiply(a, b):
    return a * b


def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
