from __future__ import annotations

from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    path = root / "backend/scripts/run_financial_intelligence_v1_2_bank_real_data_intake_gate.py"

    text = path.read_text(encoding="utf-8-sig")

    start = text.find("def _iter_candidate_records(fi_dir: Path):")
    if start < 0:
        raise RuntimeError("BANK_GATE_ITERATOR_NOT_FOUND")

    next_def = text.find("\ndef ", start + 1)
    if next_def < 0:
        raise RuntimeError("BANK_GATE_NEXT_FUNCTION_NOT_FOUND")

    new_func = '''def _iter_candidate_records(fi_dir: Path):
    excluded_name_tokens = (
        "_intake_gate",
        "_readiness",
        "_registry",
        "_acceptance",
        "_handoff",
        "_closure",
        "_manifest",
        "_resolution",
        "_selector",
        "_contract",
    )

    for path in sorted(fi_dir.rglob("*.json")):
        lower_name = path.name.lower()

        if any(token in lower_name for token in excluded_name_tokens):
            continue

        try:
            data = _load_json(path)
        except Exception:
            continue

        records = []

        if isinstance(data, dict):
            records.append(data)

            for key in ("data", "records", "items", "results"):
                value = data.get(key)

                if isinstance(value, list):
                    records.extend(
                        item
                        for item in value
                        if isinstance(item, dict)
                    )

        elif isinstance(data, list):
            records.extend(
                item
                for item in data
                if isinstance(item, dict)
            )

        for record in records:
            if str(record.get("sector_model") or "").strip().upper() != "BANK":
                continue

            if not isinstance(record.get("canonical_facts"), dict):
                continue

            if not str(record.get("as_of") or "").strip():
                continue

            if not str(record.get("publication_date") or "").strip():
                continue

            yield path, record
'''

    new_text = text[:start] + new_func + text[next_def + 1:]

    compile(new_text, str(path), "exec")

    backup = root / "_backup" / "FIN_INTEL_V1_2_BANK_REAL_DATA_GATE_HARDENING_V2"
    backup.mkdir(parents=True, exist_ok=True)

    dst = backup / path.name
    if not dst.exists():
        dst.write_bytes(path.read_bytes())

    path.write_text(new_text, encoding="utf-8")

    print(f"TARGET={path}")
    print(f"BACKUP={backup}")
    print("CONTROL_ARTIFACTS_EXCLUDED=True")
    print("REAL_CANDIDATE_REQUIRES=sector_model=BANK+canonical_facts+as_of+publication_date")
    print("FINANCIAL_INTELLIGENCE_V1_2_BANK_REAL_DATA_GATE_HARDENING_V2=PASS")


if __name__ == "__main__":
    main()
