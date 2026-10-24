from __future__ import annotations

from pathlib import Path
from datetime import datetime
import shutil


def main():
    root = Path(r"D:\Projects\Hisse-Robotu")

    test_path = (
        root
        / "backend"
        / "tests"
        / "test_financial_intelligence_bank_production_source_onboarding_v1.py"
    )

    if not test_path.exists():
        raise SystemExit(
            f"TEST_FILE_MISSING:{test_path}"
        )

    original = test_path.read_text(
        encoding="utf-8-sig"
    )

    text = original

    old = '"as_of": "2026-06-30",'
    new = '"as_of": "2026-08-31",'

    if old not in text:
        raise SystemExit(
            "TEST_FIXTURE_AS_OF_ANCHOR_NOT_FOUND"
        )

    text = text.replace(
        old,
        new,
        1,
    )

    # Keep explicit future-publication test semantically future.
    text = text.replace(
        'record["as_of"] = "2026-06-30"',
        'record["as_of"] = "2026-08-31"',
        1,
    )

    backup = (
        root
        / "_backup"
        / (
            "FIN_INTEL_V1_3_BANK_ONBOARDING_TEST_PIT_REPAIR_"
            + datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )
        )
    )

    backup.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        test_path,
        backup / test_path.name,
    )

    test_path.write_text(
        text,
        encoding="utf-8",
        newline="\n",
    )

    print(f"BACKUP={backup}")
    print(f"TEST={test_path}")
    print("FIXTURE_AS_OF=2026-08-31")
    print("FIXTURE_PUBLICATION_DATE=2026-08-05")
    print("FUTURE_TEST_PUBLICATION_DATE=2026-09-01")
    print("PRODUCTION_MODULE_MUTATION=NO")
    print("V1_2_PIT_CONTRACT_MUTATION=NO")
    print(
        "FINANCIAL_INTELLIGENCE_V1_3_"
        "BANK_ONBOARDING_TEST_FIXTURE_PIT_REPAIR_V1=PASS"
    )


if __name__ == "__main__":
    main()
