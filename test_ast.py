import ast
import os
import sys

visited = set()

def visit(mod_name):
    if mod_name in visited or not mod_name:
        return
    visited.add(mod_name)
    parts = mod_name.split('.')
    p = os.path.join(*parts) + '.py'
    if not os.path.exists(p):
        p = os.path.join(os.path.join(*parts), '__init__.py')
    if not os.path.exists(p):
        return
    try:
        with open(p, encoding='utf-8') as f:
            tree = ast.parse(f.read())
        
        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    print(f"{mod_name} imports {alias.name}")
                    visit(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                print(f"{mod_name} imports from {node.module}")
                visit(node.module)
    except Exception as e:
        print(f'Error parsing {p}: {e}')

visit('api.main')
print('AST import scan complete.')
