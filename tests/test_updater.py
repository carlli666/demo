"""
tests/test_updater.py
~~~~~~~~~~~~~~~~~~~~~~

api_demo.updater 单元测试。

覆盖：
- 版本解析（带 v 前缀、不带前缀、缺段）
- 版本比较（包括 0.10.0 > 0.2.0 这种坑）
- find_asset / extract_sha256
- Updater.check 用 monkeypatch mock GitHub API
- file_sha256 实际计算

不依赖网络。
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from api_demo.updater import (
    NetworkError,
    ParseError,
    ReleaseInfo,
    Updater,
    UpdaterError,
    extract_sha256,
    file_sha256,
    find_asset,
    is_newer,
    make_update_bat,
    parse_version,
)


# ==================== parse_version ====================


def test_parse_version_with_v_prefix():
    assert parse_version("v0.2.1") == (0, 2, 1)
    assert parse_version("v1.0.0") == (1, 0, 0)


def test_parse_version_without_prefix():
    assert parse_version("0.10.0") == (0, 10, 0)
    assert parse_version("1.2.3") == (1, 2, 3)


def test_parse_version_short():
    """缺省段默认补 0。"""
    assert parse_version("1.2") == (1, 2, 0)
    assert parse_version("5") == (5, 0, 0)


def test_parse_version_strips_whitespace():
    assert parse_version("  v1.2.3  ") == (1, 2, 3)


def test_parse_version_invalid():
    with pytest.raises(ParseError):
        parse_version("")


def test_parse_version_garbage():
    with pytest.raises(ParseError):
        parse_version("not-a-version")


# ==================== is_newer ====================


def test_is_newer_basic():
    assert is_newer((1, 2, 3), (1, 2, 2)) is True
    assert is_newer((1, 2, 3), (1, 2, 3)) is False
    assert is_newer((1, 2, 3), (1, 2, 4)) is False
    assert is_newer((2, 0, 0), (1, 9, 9)) is True


def test_is_newer_length_mismatch():
    """元组长度不等时也能正确比较。"""
    assert is_newer((1, 2, 3), (1, 2)) is True
    assert is_newer((1, 2), (1, 2, 3)) is False


def test_is_newer_010_vs_020():
    """关键回归测试：0.10.0 > 0.2.0（字符串比较会错）。"""
    assert is_newer((0, 10, 0), (0, 2, 0)) is True
    assert is_newer((0, 2, 0), (0, 10, 0)) is False


# ==================== find_asset ====================


def test_find_asset_exists():
    release = {
        "assets": [
            {"name": "other.exe", "url": "x"},
            {"name": "intelligent assistant.exe", "url": "y"},
        ]
    }
    asset = find_asset(release, "intelligent assistant.exe")
    assert asset is not None
    assert asset["name"] == "intelligent assistant.exe"


def test_find_asset_missing():
    release = {"assets": [{"name": "other.exe"}]}
    assert find_asset(release, "missing.exe") is None


def test_find_asset_empty():
    assert find_asset({}, "anything") is None


# ==================== extract_sha256 ====================


def test_extract_sha256_found():
    notes = """
## What's New
- Bug fixes

SHA256: 1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef
"""
    h = extract_sha256(notes)
    assert h == "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"


def test_extract_sha256_case_insensitive():
    notes = "sha256: ABCDEF1234567890ABCDEF1234567890ABCDEF1234567890ABCDEF1234567890"
    h = extract_sha256(notes)
    assert h == "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"


def test_extract_sha256_not_found():
    assert extract_sha256("no hash here") is None
    assert extract_sha256("") is None
    # 太短的（不到 64 位）也匹配不上
    assert extract_sha256("SHA256: abc123") is None


# ==================== file_sha256 ====================


def test_file_sha256_basic(tmp_path):
    """实际计算一个临时文件的 SHA256（用 hashlib 已知的向量）。"""
    f = tmp_path / "test.bin"
    f.write_bytes(b"hello world")
    assert file_sha256(f) == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"


def test_file_sha256_empty(tmp_path):
    f = tmp_path / "empty.bin"
    f.write_bytes(b"")
    # 空文件的 SHA256
    assert file_sha256(f) == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


# ==================== Updater.check (mocked GitHub API) ====================


def _make_release_json(version: str, asset_name: str = "intelligent assistant.exe") -> dict:
    return {
        "tag_name": f"v{version}",
        "name": f"v{version}",
        "body": f"Release notes for {version}\n\nSHA256: {'a' * 64}",
        "assets": [
            {
                "name": asset_name,
                "browser_download_url": f"https://example.com/{asset_name}",
                "size": 15 * 1024 * 1024,
            }
        ],
    }


def test_check_returns_release_when_newer(monkeypatch):
    """GitHub 返回 v0.2.0，当前 0.1.0 → 应该返回 ReleaseInfo。"""
    updater = Updater(current_version="0.1.0")

    def fake_fetch(repo):
        return _make_release_json("0.2.0")

    monkeypatch.setattr("api_demo.updater.fetch_latest_release", fake_fetch)
    release = updater.check(force=True)
    assert release is not None
    assert release.version == "0.2.0"
    assert release.tag == "v0.2.0"
    assert release.size_bytes == 15 * 1024 * 1024
    assert release.sha256 == "a" * 64
    assert release.download_url.endswith("intelligent assistant.exe")


def test_check_returns_none_when_up_to_date(monkeypatch):
    """当前已是最新 → 返回 None。"""
    updater = Updater(current_version="0.1.0")

    def fake_fetch(repo):
        return _make_release_json("0.1.0")

    monkeypatch.setattr("api_demo.updater.fetch_latest_release", fake_fetch)
    assert updater.check(force=True) is None


def test_check_returns_none_when_older(monkeypatch):
    """GitHub 上的版本比当前旧（理论上不会发生）→ 返回 None。"""
    updater = Updater(current_version="0.2.0")

    def fake_fetch(repo):
        return _make_release_json("0.1.0")

    monkeypatch.setattr("api_demo.updater.fetch_latest_release", fake_fetch)
    assert updater.check(force=True) is None


def test_check_returns_none_on_network_error(monkeypatch):
    """网络异常 → 返回 None（不抛）。"""
    updater = Updater(current_version="0.1.0")

    def fake_fetch(repo):
        raise NetworkError("no internet")

    monkeypatch.setattr("api_demo.updater.fetch_latest_release", fake_fetch)
    assert updater.check(force=True) is None


def test_check_returns_none_when_asset_missing(monkeypatch):
    """新版 release 没有对应 asset → 返回 None（不能下载）。"""
    updater = Updater(current_version="0.1.0")

    def fake_fetch(repo):
        return _make_release_json("0.2.0", asset_name="other.exe")

    monkeypatch.setattr("api_demo.updater.fetch_latest_release", fake_fetch)
    assert updater.check(force=True) is None


# ==================== verify ====================


def test_verify_no_expected_skips_check(tmp_path):
    """expected_sha256=None 时直接返回 True（跳过校验）。"""
    updater = Updater()
    f = tmp_path / "x.exe"
    f.write_bytes(b"any content")
    assert updater.verify(f, None) is True


def test_verify_correct_hash(tmp_path):
    updater = Updater()
    f = tmp_path / "x.exe"
    f.write_bytes(b"hello world")
    expected = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
    assert updater.verify(f, expected) is True


def test_verify_wrong_hash(tmp_path):
    updater = Updater()
    f = tmp_path / "x.exe"
    f.write_bytes(b"hello world")
    wrong = "0" * 64
    assert updater.verify(f, wrong) is False


def test_verify_case_insensitive(tmp_path):
    updater = Updater()
    f = tmp_path / "x.exe"
    f.write_bytes(b"hello world")
    expected = "B94D27B9934D3E08A52E52D7DA7DABFAC484EFE37A5380EE9088F7ACE2EFCDE9"
    assert updater.verify(f, expected) is True


# ==================== make_update_bat ====================


def test_make_update_bat_contains_target_name(tmp_path):
    """生成的 bat 应该包含目标 exe 名和等待逻辑。"""
    new_exe = tmp_path / "new.exe"
    target_exe = tmp_path / "target.exe"
    log_path = tmp_path / "update.log"
    bat = make_update_bat(new_exe, target_exe, log_path)
    assert "target.exe" in bat
    assert "wait_loop" in bat
    assert "move /y" in bat
    assert str(new_exe) in bat
    assert str(target_exe) in bat
    assert str(log_path) in bat