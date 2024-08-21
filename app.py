from spreadsheet.spreadsheet import evaluate_spreadsheet, pretty_print_results

spreadsheet = {"A1": "1", "A2": "94", "A3": "2", "B1": "", "B4": "=SUM(A1:A2)", "D1": "1", "F1": "=A2"}

result = evaluate_spreadsheet(spreadsheet)

print(result)

pretty_print_results(result)