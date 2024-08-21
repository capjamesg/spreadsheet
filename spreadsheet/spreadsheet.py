import re
from collections import OrderedDict

from lark import Lark, Transformer, Visitor
from tabulate import tabulate
from toposort import toposort_flatten
import string

grammar = """
start: term

term: "=" part*
part: in_ | count_ | if_ | "(" part OPERATOR part ")" | DATE | NUMBER | range_substitution | cell | sum
cell: /[A-Z][0-9]/
count_: "COUNT" "(" RAW_CELL ":" RAW_CELL ")"
if_: "IF" "(" part OPERATOR part ")" "THEN" cell "ELSE" cell
in_: "IN" "(" range "," part ")"
range: RAW_CELL ":" RAW_CELL
range_substitution: RAW_CELL ":" RAW_CELL
sum: "SUM" "(" range ")"
RAW_CELL: /[A-Z][0-9]/
OPERATOR: "+" | "-" | "*" | "/" | ">" | "<"
DATE: /\d{4}-\d{2}-\d{2}/
NUMBER: /\d+/

%import common.WS
%ignore WS
"""

parser = Lark(grammar)

dependency_graph = {}

operators = {
    "+": lambda x, y: x + y,
    "-": lambda x, y: x - y,
    "*": lambda x, y: x * y,
    "/": lambda x, y: x / y,
    ">": lambda x, y: x > y,
    "<": lambda x, y: x < y,
}


def get_cell_start_number(cell):
    return int(re.sub("[^0-9]", "", cell))


def get_cell_start_letter(cell):
    return re.sub("[^A-Z]", "", cell)


class GetDependencies(Visitor):
    dependencies = set()

    def cell(self, tree):
        self.dependencies.add(tree.children[0].value)


def get_cells_in_range(start, end):
    cells = []

    # trim letters from start
    start_number = get_cell_start_number(start)
    start_letter = get_cell_start_letter(start)

    end_number = get_cell_start_number(end)
    end_letter = get_cell_start_letter(end)

    for i in range(start_number, end_number + 1):
        cell_reference = f"{start_letter}{i}"
        cells.append(cell_reference)

    return cells


class EvalExpressions(Transformer):
    def __init__(self, cells, active_cell=None):
        self.cells = cells
        self.active_cell = active_cell

    def recursively_get_cell_value(self, cell, depth=0):
        if depth > 100:
            raise Exception("Nested too deep.")

        if cell in self.cells.keys():
            return self.recursively_get_cell_value(
                str(self.cells[cell]).strip("="), depth + 1
            )

        return str(cell).strip("=")

    def cell(self, args):
        return float(self.recursively_get_cell_value(args[0]))

    def OPERATOR(self, args):
        return args[0]

    def NUMBER(self, args):
        return float(args)

    def range_substitution(self, args):
        start = args[0]
        end = args[1]

        column_of_active_cell = get_cell_start_letter(self.active_cell)

        for cell in get_cells_in_range(start, end):
            cell_num = get_cell_start_number(cell)
            new_cell = f"{column_of_active_cell}{cell_num}"

            self.cells[new_cell] = self.recursively_get_cell_value(cell)

        return self.cells[self.active_cell]

        # return sum([float(i) for i in values])

    def count_(self, args):
        non_zero = 0

        cells_in_range = get_cells_in_range(args[0], args[1])

        for cell in cells_in_range:
            if float(self.recursively_get_cell_value(cell)) > 0:
                non_zero += 1

        return non_zero

    def range(self, args):
        start = args[0]
        end = args[1]

        return [
            float(self.recursively_get_cell_value(i))
            for i in get_cells_in_range(start, end)
        ]

    def sum(self, args):
        count = 0

        for cell in args[0]:
            count += float(self.recursively_get_cell_value(cell))

        return count

    def in_(self, args):
        range = args[0]
        value = args[1]

        return value in range

    def if_(self, args):
        expression = args[0]
        operator = args[1]
        value = args[2]
        true_value = args[3]
        false_value = args[4]

        condition = operators[operator](expression, value)

        if condition:
            return true_value
        else:
            return false_value

    def part(self, args):
        if len(args) == 1:
            return args[0]

        left = args[0]
        operator = args[1]
        right = args[2]

        return operators[operator](left, right)

    def term(self, args):
        return args[0]

    def start(self, args):
        return args[0]

def starts_with_equals(cell):
    if len(cell) == 0:
        return False
    
    return cell[0] == "="

def evaluate_spreadsheet(cells):
    for cell in cells:
        dependencies = GetDependencies()

        if starts_with_equals(cells[cell]):
            dependencies.visit(parser.parse(cells[cell]))
            dependency_graph[cell] = dependencies.dependencies

            if cell in dependency_graph[cell]:
                raise Exception("Circular dependency")
        else:
            dependency_graph[cell] = set()

    flattened = toposort_flatten(dependency_graph)

    for cell in flattened:
        if starts_with_equals(cells[cell]):
            computed_result = EvalExpressions(cells, cell).transform(
                parser.parse(cells[cell])
            )

            cells[cell] = computed_result

        if isinstance(cells[cell], str) and cells[cell].isdigit():
            cells[cell] = int(cells[cell])

        try:
            cells[cell] = float(cells[cell])
        except:
            pass

    return cells


def pretty_print_results(result):
    rows = {}

    result = OrderedDict(sorted(result.items()))

    for cell, value in result.items():
        cell_letter = re.sub(r"\d", "", cell)
        cell_number = re.sub(r"\D", "", cell)
        if cell_letter not in rows:
            rows[cell_letter] = OrderedDict()

        rows[cell_letter][int(cell_number)] = value

    # fill in blank rows
    for letter in rows:
        for i in range(1, max(rows[letter].keys())):
            if i not in rows[letter]:
                rows[letter][i] = ""

    # if missing any rows
    first_letter_in_sheet = list(rows.keys())[0]
    last_letter_in_sheet = list(rows.keys())[-1]

    for letter in string.ascii_uppercase:
        if letter > first_letter_in_sheet and letter < last_letter_in_sheet and letter not in rows:
            rows[letter] = OrderedDict()

    for letter in rows:
        rows[letter] = OrderedDict(sorted(rows[letter].items()))
        rows[letter] = [str(i) + "    " for i in rows[letter].values()]

    # longest row
    longest_row = max([len(i) for i in rows.values()])
    rows[""] = [str(i) + "    " for i in range(1, longest_row + 1)]

    rows = OrderedDict(sorted(rows.items()))

    table = tabulate(rows, headers="keys")

    print(table)
