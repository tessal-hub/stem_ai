"""Verify security hardening: no shell injection, no path traversal."""
from constants import normalize_spell_name

def test_spell_name_strips_path_separators():
    assert '/' not in normalize_spell_name("../../etc")
    assert '\\' not in normalize_spell_name("..\\..\\windows")
    assert '..' not in normalize_spell_name("../hack")

def test_spell_name_strips_special_chars():
    result = normalize_spell_name("SPELL; rm -rf /")
    assert ';' not in result
    assert '/' not in result

def test_spell_name_preserves_valid_names():
    assert normalize_spell_name("FIRE BALL") == "FIRE BALL"
    assert normalize_spell_name("circle_cw") == "CIRCLE_CW"
    assert normalize_spell_name("STAND BY") == "STAND BY"

def test_flash_worker_no_shell_true():
    import ast, inspect, textwrap
    from logic.flash_worker import FlashWorker
    source = inspect.getsource(FlashWorker.run)
    tree = ast.parse(textwrap.dedent(source))
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg == 'shell':
            assert not (isinstance(node.value, ast.Constant) and node.value.value is True), \
                "flash_worker still uses shell=True"
