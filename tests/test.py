from contextlib import ExitStack as DoesNotRaise

import pytest

from spreadsheet.spreadsheet import evaluate_spreadsheet


@pytest.mark.parametrize(
    "spreadsheet, result, raises_exception",
    [
        (
            {
                "A1": "5",
            },
            {
                "A1": 5,
            },
            DoesNotRaise(),
        ),  # identity and integer conversion
        (
            {
                "A1": "5",
                "A2": "=A1",
            },
            {
                "A1": 5,
                "A2": 5,
            },
            DoesNotRaise(),
        ),  # reference to another cell
        (
            {
                "A1": "5",
                "A2": "A1",
            },
            {"A1": 5, "A2": "A1"},
            DoesNotRaise(),
        ),  # missing equals sign
        (
            {
                "A1": "5",
                "A2": "=(A1 * A1)",
            },
            {"A1": 5, "A2": 25},
            DoesNotRaise(),
        ),  # multiplication
        (
            {
                "A1": "10",
                "A2": "=(A1 / 5)",
            },
            {"A1": 10, "A2": 2},
            DoesNotRaise(),
        ),  # integer division
        (
            {
                "A1": "2.1",
                "A2": "=(A1 / 2)",
            },
            {"A1": 2.1, "A2": 1.05},
            DoesNotRaise(),
        ),  # integer division
        (
            {
                "A1": "10",
                "A2": "=(A1 + 5)",
            },
            {"A1": 10, "A2": 15},
            DoesNotRaise(),
        ),  # addition
        (
            {
                "A1": "10",
                "A2": "=(A1 - 5)",
            },
            {"A1": 10, "A2": 5},
            DoesNotRaise(),
        ),  # subtraction
        (
            {
                "A1": "10",
                "A2": "=(A1 - (2 + 2))",
            },
            {"A1": 10, "A2": 6},
            DoesNotRaise(),
        ),  # nested query
        (
            {
                "A1": "10",
                "A2": "=((A1 * 2) - (2 + 2))",
            },
            {"A1": 10, "A2": 16},
            DoesNotRaise(),
        ),  # query with two nested terms
    ],
)
def test_get_cell(spreadsheet, result, raises_exception):
    with raises_exception:
        computed_spreadsheet = evaluate_spreadsheet(spreadsheet)

        for cell in spreadsheet:
            assert computed_spreadsheet[cell] == result[cell]
