from pathlib import Path
import re

ROOT = Path(__file__).parent
PAGES = [
    "index.html",
    "behavior.html",
    "orchestrator.html",
    "deception.html",
    "threat-intel.html",
    "system-settings.html",
    "audit-logs.html",
]

ROUTES = {
    "Sentinel": "/",
    "Behavior": "/behavior.html",
    "Orchestrator": "/orchestrator.html",
    "Deception": "/deception.html",
    "Threat Intel": "/threat-intel.html",
    "System Settings": "/system-settings.html",
    "Audit Logs": "/audit-logs.html",
}

CORE_LABELS = ["Sentinel", "Behavior", "Orchestrator", "Deception", "Threat Intel"]
OPTIONAL_LABELS = ["System Settings", "Audit Logs"]


def assert_true(cond: bool, msg: str):
    if not cond:
        raise AssertionError(msg)


def test_pages_exist():
    for page in PAGES:
        assert_true((ROOT / page).exists(), f"Missing page: {page}")


def test_scripts_injected():
    for page in PAGES:
        text = (ROOT / page).read_text(encoding="utf-8")
        assert_true('/nav.js' in text, f"nav.js missing in {page}")
        assert_true('/app.js' in text, f"app.js missing in {page}")


def test_sidebar_labels_present():
    for page in PAGES:
        text = (ROOT / page).read_text(encoding="utf-8")
        for label in CORE_LABELS:
            assert_true(label in text, f"Sidebar label '{label}' missing in {page}")


def test_optional_labels_present_in_some_pages():
    text_all = "\n".join((ROOT / p).read_text(encoding="utf-8") for p in PAGES)
    for label in OPTIONAL_LABELS:
        assert_true(label in text_all, f"Optional nav label '{label}' not found in any page")


def test_index_layout_not_stretching():
    text = (ROOT / "index.html").read_text(encoding="utf-8")
    assert_true("auto-rows-fr" not in text, "index.html still contains auto-rows-fr")
    assert_true("items-start" in text, "index.html grid missing items-start")


def test_index_routes_not_hash_only():
    text = (ROOT / "index.html").read_text(encoding="utf-8")
    must_have = [
        '/?view=sentinel',
        '/?view=behavior',
        '/?view=orchestrator',
        '/?view=deception',
        '/?view=threat-intel',
        '/?view=system-settings',
        '/?view=audit-logs',
    ]
    for route in must_have:
        assert_true(route in text, f"Main nav route missing: {route}")


def test_module_canvas_exists():
    text = (ROOT / "index.html").read_text(encoding="utf-8")
    assert_true('id="mainGrid"' in text, "mainGrid container missing")
    assert_true('id="moduleView"' in text, "moduleView container missing")
    assert_true('id="moduleTitle"' in text, "moduleTitle missing")


def run_all():
    tests = [
        test_pages_exist,
        test_scripts_injected,
        test_sidebar_labels_present,
        test_optional_labels_present_in_some_pages,
        test_index_layout_not_stretching,
        test_index_routes_not_hash_only,
        test_module_canvas_exists,
    ]
    for t in tests:
        t()
    print(f"PASS: {len(tests)} UI smoke tests")


if __name__ == "__main__":
    run_all()
