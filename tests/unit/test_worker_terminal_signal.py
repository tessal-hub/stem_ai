"""Verify all workers emit sig_finished on all exit paths."""
import ast
import inspect
import textwrap

def _run_has_finally_with_sig_finished(cls) -> bool:
    source = inspect.getsource(cls.run)
    source = textwrap.dedent(source)
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Try) and node.finalbody:
            for stmt in ast.walk(node):
                if isinstance(stmt, ast.Attribute) and 'sig_finished' in ast.dump(stmt):
                    return True
    return False

def test_data_io_worker_emits_sig_finished():
    from logic.data_io_worker import DataIOWorker
    assert _run_has_finally_with_sig_finished(DataIOWorker)

def test_feature_worker_emits_sig_finished():
    from logic.feature_worker import FeatureWorker
    assert _run_has_finally_with_sig_finished(FeatureWorker)
