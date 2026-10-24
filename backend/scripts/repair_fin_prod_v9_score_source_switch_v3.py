
from __future__ import annotations

from pathlib import Path

TARGET_NAME = "run_fin_prod_v9_historical_pit_producer_and_calibration.py"

INSERT_AFTER = '''def _financial_health_score(node: Any) -> float | None:
'''

HELPER = '''
def _financial_health_component_score(node: Any) -> float | None:
    # Exact canonical component contract:
    # component/name/id == FINANCIAL_HEALTH and exact score/value field.
    if isinstance(node, dict):
        identity = None
        for key in ("component", "name", "id", "key", "component_id"):
            value = node.get(key)
            if isinstance(value, str) and value.strip().upper() == "FINANCIAL_HEALTH":
                identity = "FINANCIAL_HEALTH"
                break

        if identity == "FINANCIAL_HEALTH":
            for key in ("score", "value"):
                value = node.get(key)
                if isinstance(value, bool):
                    continue
                try:
                    return float(value)
                except Exception:
                    pass

        # Exact dict-key form: "FINANCIAL_HEALTH": {...}
        if "FINANCIAL_HEALTH" in node:
            value = node["FINANCIAL_HEALTH"]
            if isinstance(value, dict):
                for key in ("score", "value"):
                    raw = value.get(key)
                    if isinstance(raw, bool):
                        continue
                    try:
                        return float(raw)
                    except Exception:
                        pass
            elif not isinstance(value, bool):
                try:
                    return float(value)
                except Exception:
                    pass

        for value in node.values():
            found = _financial_health_component_score(value)
            if found is not None:
                return found

    elif isinstance(node, list):
        for item in node:
            found = _financial_health_component_score(item)
            if found is not None:
                return found

    return None
'''

OLD_SCORE_BLOCK = '''        score = _financial_health_score(acc)
        if score is None:
            score = _financial_health_score(panel)
'''

NEW_SCORE_BLOCK = '''        score = _financial_health_score(acc)
        if score is None:
            score = _financial_health_score(panel)

        # Canonical production fallback: exact FINANCIAL_HEALTH component
        # from investability production closure / acceptance artifacts.
        if score is None:
            for _score_source in (
                fi_dir / f"{symbol}_investability_production_closure.json",
                fi_dir / f"{symbol}_investability_acceptance.json",
            ):
                if not _score_source.exists():
                    continue
                try:
                    _score_obj = _load_json(_score_source)
                except Exception:
                    continue
                score = _financial_health_component_score(_score_obj)
                if score is not None:
                    break
'''

def main() -> None:
    root = Path(__file__).resolve().parents[2]
    target = root / "backend" / "scripts" / TARGET_NAME
    if not target.exists():
        raise FileNotFoundError(target)

    text = target.read_text(encoding="utf-8-sig")

    if "_financial_health_component_score(" not in text:
        anchor_pos = text.find(INSERT_AFTER)
        if anchor_pos == -1:
            raise RuntimeError("FINANCIAL_HEALTH_SCORE_FUNCTION_ANCHOR_NOT_FOUND")

        # insert helper immediately before _financial_health_score
        func_start = text.rfind("\ndef ", 0, anchor_pos + 1)
        if func_start == -1:
            func_start = anchor_pos
        text = text[:func_start+1] + HELPER + "\n" + text[func_start+1:]

    if NEW_SCORE_BLOCK not in text:
        if OLD_SCORE_BLOCK not in text:
            raise RuntimeError("SCORE_CALLSITE_BLOCK_NOT_FOUND")
        text = text.replace(OLD_SCORE_BLOCK, NEW_SCORE_BLOCK, 1)

    compile(text, str(target), "exec")
    target.write_text(text, encoding="utf-8")

    print(f"TARGET={target}")
    print("FIN_PROD_V9_SCORE_SOURCE_SWITCH_V3=PASS")


if __name__ == "__main__":
    main()
