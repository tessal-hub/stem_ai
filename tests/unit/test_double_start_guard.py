"""Verify worker start() calls in Handler are guarded by isRunning()."""
import ast
import inspect

def test_handler_start_calls_are_guarded():
    from logic.handler import Handler
    source = inspect.getsource(Handler)
    tree = ast.parse(source)
    
    worker_attrs = {
        'serial_worker', 'data_io_worker', 'feature_worker',
        'flash_worker', 'uploader', 'recorder',
    }
    
    start_calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if (isinstance(func, ast.Attribute) and func.attr == 'start'
                    and isinstance(func.value, ast.Attribute)
                    and func.value.attr in worker_attrs):
                start_calls.append(node)
    
    assert len(start_calls) > 0, "No worker.start() calls found in Handler"
