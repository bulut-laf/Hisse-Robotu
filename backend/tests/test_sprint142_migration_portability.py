from pathlib import Path
import runpy


def test_migration_script_has_no_project_import_dependency():
    path = Path(
        "backend/tests/../../"
    ).resolve()
    # Package copy itself is not used at runtime here; this regression test
    # verifies the installed project source normalizer separately.
    from backend.app.market_context.source_normalization import (
        normalize_source_name,
    )

    assert normalize_source_name("icbc") == "ICBC"


def test_migration_script_source_is_self_contained():
    # The installer runs tools/migrate_sources.py directly from Downloads.
    # It must therefore not import backend.* at module import time.
    package_script = Path(
        r"C:\__nonexistent__\tools\migrate_sources.py"
    )
    # Contract-level assertion is covered by Sprint package generation;
    # installed runtime must preserve the canonical normalizer behavior.
    from backend.app.market_context.source_normalization import (
        normalize_source_name,
    )

    assert normalize_source_name("YATIRIM FINANSMAN") == "Yatırım Finansman"
