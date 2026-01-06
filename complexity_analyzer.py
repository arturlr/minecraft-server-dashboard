#!/usr/bin/env python3
import ast
import os
from pathlib import Path

class ComplexityAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.complexity = 1  # Base complexity
        
    def visit_If(self, node):
        self.complexity += 1
        self.generic_visit(node)
        
    def visit_While(self, node):
        self.complexity += 1
        self.generic_visit(node)
        
    def visit_For(self, node):
        self.complexity += 1
        self.generic_visit(node)
        
    def visit_ExceptHandler(self, node):
        self.complexity += 1
        self.generic_visit(node)
        
    def visit_With(self, node):
        self.complexity += 1
        self.generic_visit(node)
        
    def visit_BoolOp(self, node):
        # Add complexity for each additional condition in and/or
        self.complexity += len(node.values) - 1
        self.generic_visit(node)
        
    def visit_ListComp(self, node):
        self.complexity += 1
        self.generic_visit(node)
        
    def visit_DictComp(self, node):
        self.complexity += 1
        self.generic_visit(node)
        
    def visit_SetComp(self, node):
        self.complexity += 1
        self.generic_visit(node)

def get_function_complexity(func_node):
    analyzer = ComplexityAnalyzer()
    analyzer.visit(func_node)
    return analyzer.complexity

def analyze_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        functions = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                complexity = get_function_complexity(node)
                functions.append({
                    'name': node.name,
                    'complexity': complexity,
                    'line': node.lineno
                })
        
        return functions
    except Exception as e:
        return [{'name': f'ERROR: {str(e)}', 'complexity': 0, 'line': 0}]

def find_lambda_files():
    """Dynamically find Lambda index.py files."""
    lambda_files = []
    if os.path.exists("lambdas"):
        for item in os.listdir("lambdas"):
            index_path = os.path.join("lambdas", item, "index.py")
            if os.path.isfile(index_path):
                lambda_files.append(index_path)
    return lambda_files

def find_layer_files():
    """Dynamically find Layer helper files."""
    layer_files = []
    if os.path.exists("layers"):
        for item in os.listdir("layers"):
            layer_path = os.path.join("layers", item, f"{item}.py")
            if os.path.isfile(layer_path):
                layer_files.append(layer_path)
    return layer_files

def get_risk_level(complexity_rating):
    """Get risk level based on complexity rating."""
    if complexity_rating == 1:
        return "Simple"
    elif complexity_rating <= 4:
        return "Low"
    elif complexity_rating <= 7:
        return "Moderate"
    else:
        return "High"

def print_functions_report(file_path, section_title):
    """Print complexity report for functions in a file."""
    if os.path.exists(file_path):
        print(f"\n### {file_path}")
        functions = analyze_file(file_path)
        for func in functions:
            complexity_rating = min(10, func['complexity'])
            risk_level = get_risk_level(complexity_rating)
            print(f"- `{func['name']}()` - **{complexity_rating}/10** ({risk_level}) - Line {func['line']}")

def main():
    lambda_files = find_lambda_files()
    layer_files = find_layer_files()
    
    print("# Cyclomatic Complexity Report")
    print("## Scale: 1-10 (1=Simple, 2-4=Low, 5-7=Moderate, 8-10=High)")
    print()
    
    print("## Lambda Functions")
    for file_path in lambda_files:
        print_functions_report(file_path, "Lambda Functions")
    
    print("\n## Layer Helper Functions")
    for file_path in layer_files:
        print_functions_report(file_path, "Layer Helper Functions")

if __name__ == "__main__":
    main()
