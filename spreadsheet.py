import re

from lark import Lark, Transformer, Visitor
from toposort import toposort, toposort_flatten

grammar = """
start: term

term: "=" part*
part: in_ | count_ | if_ | "(" part OPERATOR part ")" | DATE | NUMBER | range_query | cell
cell: /[A-Z][0-9]/
count_: "COUNT" "(" RAW_CELL ":" RAW_CELL ")"
if_: "IF" "(" part OPERATOR part ")" "THEN" cell "ELSE" cell
in_: "IN" "(" range "," part ")"
range: RAW_CELL ":" RAW_CELL
range_query: RAW_CELL ":" RAW_CELL
RAW_CELL: /[A-Z][0-9]/
OPERATOR: "+" | "-" | "*" | "/" | ">" | "<"
DATE: /\d{4}-\d{2}-\d{2}/
NUMBER: /\d+/

%import common.WS
%ignore WS
"""

parser = Lark(grammar)

# to support something like B1:B3 = A1:13, I would need to add query expansion

cells = {
    "A1": "10",
    "A2": "=A1",
    "A3": "500",
    "A4": "=A1:A3",
    "A5": "=IF(((A1+A2) > 10)) THEN A3 ELSE A1",
    "A6": "=COUNT(A1:A3)",
    "A7": "=IN(A1:A3, 10)",
}

dependency_graph = {}

operators = {
    "+": lambda x, y: x + y,
    "-": lambda x, y: x - y,
    "*": lambda x, y: x * y,
    "/": lambda x, y: x / y,
    ">": lambda x, y: x > y,
    "<": lambda x, y: x < y,
}


class GetDependencies(Visitor):
    dependencies = set()

    def cell(self, tree):
        self.dependencies.add(tree.children[0].value)


def recursively_get_cell_value(cell):
    if cell in cells.keys():
        return recursively_get_cell_value(str(cells[cell]).strip("="))

    return cell.strip("=")


def get_cells_in_range(start, end):
    cells = []

    # trim letters from start
    start_number = int(re.sub("[^0-9]", "", start))
    start_letter = re.sub("[^A-Z]", "", start)

    end_number = int(re.sub("[^0-9]", "", end))
    end_letter = re.sub("[^A-Z]", "", end)

    for i in range(start_number, end_number + 1):
        cell_reference = f"{start_letter}{i}"
        cells.append(cell_reference)

    return cells


class EvalExpressions(Transformer):
    def cell(self, args):
        return int(recursively_get_cell_value(args[0]))

    def OPERATOR(self, args):
        return args[0]

    def NUMBER(self, args):
        return int(args)

    def range_query(self, args):
        start = args[0]
        end = args[1]

        values = []

        for cell in get_cells_in_range(start, end):
            values.append(recursively_get_cell_value(cell))

        return sum([int(i) for i in values])

    def count_(self, args):
        non_zero = 0

        range_query = get_cells_in_range(args[0], args[1])

        for cell in range_query:
            if int(recursively_get_cell_value(cell)) > 0:
                non_zero += 1

        return non_zero
    
    def range(self, args):
        start = args[0]
        end = args[1]

        return [int(recursively_get_cell_value(i)) for i in get_cells_in_range(start, end)]
    
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


example = cells["A7"]

tree = parser.parse(example)

print(EvalExpressions().transform(parser.parse(example)))
exit()


for cell in cells:
    dependencies = GetDependencies()
    if cells[cell][0] == "=":
        dependencies.visit(parser.parse(cells[cell]))
        dependency_graph[cell] = dependencies.dependencies
    else:
        dependency_graph[cell] = set()

sorted = toposort(dependency_graph)
flattened = toposort_flatten(dependency_graph)

for cell in flattened:
    if cells[cell][0] == "=":
        cells[cell] = EvalExpressions().transform(parser.parse(cells[cell]))

print(cells)
