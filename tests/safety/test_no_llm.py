import ast
import os

def check_no_llm_imports(filepath):
    with open(filepath, "r") as f:
        tree = ast.parse(f.read(), filename=filepath)
        
    banned_modules = {"openai", "httpx", "requests", "aiohttp", "urllib"}
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                root_module = name.name.split('.')[0]
                assert root_module not in banned_modules, f"Banned module {root_module} imported in {filepath}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root_module = node.module.split('.')[0]
                assert root_module not in banned_modules, f"Banned module {root_module} imported in {filepath}"

def test_no_llm_clients_in_drugs_and_grounding():
    """Static analysis test asserting the module never imports an LLM client."""
    src_dir = os.path.join(os.path.dirname(__file__), "..", "..", "services", "safety", "src")
    drugs_file = os.path.join(src_dir, "drugs.py")
    grounding_file = os.path.join(src_dir, "grounding.py")
    
    assert os.path.exists(drugs_file)
    assert os.path.exists(grounding_file)
    
    check_no_llm_imports(drugs_file)
    check_no_llm_imports(grounding_file)
