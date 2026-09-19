import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_category_module():
    path = ROOT / "category.py"
    spec = importlib.util.spec_from_file_location("category_entry", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


category_entry = _load_category_module()


def test_category_entry_errors_when_ms_bearer_token_path_undefined(monkeypatch, capsys):
    monkeypatch.delenv("MS_BEARER_TOKEN_PATH", raising=False)
    monkeypatch.setattr(sys, "argv", ["category.py"])
    assert category_entry.main() == 2
    err = capsys.readouterr().err
    assert "MS_BEARER_TOKEN_PATH is not defined" in err


def test_category_entry_errors_when_token_file_missing(monkeypatch, tmp_path, capsys):
    missing = tmp_path / "missing.token"
    monkeypatch.setenv("MS_BEARER_TOKEN_PATH", str(missing))
    monkeypatch.setattr(sys, "argv", ["category.py"])
    assert category_entry.main() == 2
    err = capsys.readouterr().err
    assert "token file not found" in err


def test_category_entry_errors_when_token_file_empty(monkeypatch, tmp_path, capsys):
    empty = tmp_path / "empty.token"
    empty.write_text("", encoding="utf-8")
    monkeypatch.setenv("MS_BEARER_TOKEN_PATH", str(empty))
    monkeypatch.setattr(sys, "argv", ["category.py"])
    assert category_entry.main() == 2
    err = capsys.readouterr().err
    assert "token file is empty" in err


def test_category_entry_downloads_with_token_file(monkeypatch, tmp_path):
    token_file = tmp_path / "morningstar.token"
    token_file.write_text("tok-from-file", encoding="utf-8")
    monkeypatch.setenv("MS_BEARER_TOKEN_PATH", str(token_file))
    monkeypatch.setattr(sys, "argv", ["category.py", "--limit", "1"])

    called = {}

    def fake_download(token, **kwargs):
        called["token"] = token
        called["kwargs"] = kwargs
        return {"ok": 1, "skipped": 0, "failed": 0}

    monkeypatch.setattr(category_entry, "download_category_monthly_data", fake_download)
    assert category_entry.main() == 0
    assert called["token"] == "tok-from-file"
    assert called["kwargs"]["limit"] == 1
