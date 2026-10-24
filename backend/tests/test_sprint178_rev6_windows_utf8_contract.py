from pathlib import Path


VERIFY = Path("backend/scripts/verify_news_center_v1.py")


def test_v1_verifier_utf8_console_kilidi_var():
    text = VERIFY.read_text(encoding="utf-8")
    assert "def _force_utf8_console()" in text
    assert 'reconfigure(encoding="utf-8", errors="replace")' in text


def test_v1_verifier_sys_stdout_stderr_ikisini_kilitler():
    text = VERIFY.read_text(encoding="utf-8")
    assert "for stream in (sys.stdout, sys.stderr)" in text


def test_v1_verifier_windows_charmap_hatasini_tetikleyecek_ascii_zorlamasi_yok():
    text = VERIFY.read_text(encoding="utf-8")
    assert 'encoding="ascii"' not in text
