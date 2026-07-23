"""Verify all cross-thread signal connections use QueuedConnection."""
import ast
import inspect
import textwrap

def test_handler_worker_signals_are_queued():
    from logic.handler import Handler
    source = inspect.getsource(Handler._connect_worker_signals)
    source = textwrap.dedent(source)
    tree = ast.parse(source)
    
    connect_calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == 'connect':
                connect_calls.append(node)
    
    for call in connect_calls:
        has_queued = any(
            'QueuedConnection' in ast.dump(kw.value)
            for kw in call.keywords
            if kw.arg == 'type'
        )
        if not has_queued and len(call.args) >= 2:
            has_queued = 'QueuedConnection' in ast.dump(call.args[1])
        assert has_queued, f"Worker signal connection missing QueuedConnection at line {call.lineno}"
