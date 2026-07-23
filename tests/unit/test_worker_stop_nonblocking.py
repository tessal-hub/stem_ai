"""Verify worker stop() methods do not block the calling thread."""
import ast
import inspect
import textwrap

def _has_sleep_in_method(cls, method_name: str) -> bool:
    """Check if a method contains time.sleep calls via AST inspection."""
    source = inspect.getsource(getattr(cls, method_name))
    source = textwrap.dedent(source)
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            if node.attr == 'sleep':
                return True
    return False

def test_udp_worker_stop_no_sleep():
    from logic.udp_worker import UdpWorker
    assert not _has_sleep_in_method(UdpWorker, 'stop'), \
        "UdpWorker.stop() contains time.sleep — blocks UI thread"

def test_data_io_worker_stop_no_sleep():
    from logic.data_io_worker import DataIOWorker
    assert not _has_sleep_in_method(DataIOWorker, 'stop'), \
        "DataIOWorker.stop() contains time.sleep — blocks UI thread"

def test_feature_worker_stop_no_sleep():
    from logic.feature_worker import FeatureWorker
    assert not _has_sleep_in_method(FeatureWorker, 'stop'), \
        "FeatureWorker.stop() contains time.sleep — blocks UI thread"
