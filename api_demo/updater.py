"""
api_demo.updater
~~~~~~~~~~~~~~~~

通过 GitHub Releases 实现在线升级。

主要能力：
- parse_version / is_newer：版本字符串解析与比较
- Updater.check()：调 GitHub API 检查最新版
- Updater.download()：流式下载 + 进度回调
- Updater.verify()：SHA256 校验
- Updater.install_and_restart()：生成 .bat 等主进程退出 → 替换 → 重启

零新增运行时依赖（仅用标准库）。
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Tuple


# ==================== 异常 ====================


class UpdaterError(Exception):
    """升级相关的错误基类。"""


class NetworkError(UpdaterError):
    """网络请求失败（DNS / 连接 / 超时等）。"""


class ParseError(UpdaterError):
    """GitHub 返回的数据格式不符合预期。"""


# ==================== 数据结构 ====================


@dataclass
class ReleaseInfo:
    """解析后的 GitHub Release 信息。"""

    version: str                # "0.2.0"
    tag: str                    # "v0.2.0"
    download_url: str            # GitHub asset 的浏览器下载地址
    size_bytes: int             # asset 大小
    release_notes: str          # release body（markdown）
    sha256: Optional[str]       # 从 release notes 提取的 SHA256
    asset_name: str             # asset 文件名


# ==================== 版本解析 / 比较 ====================


_VERSION_RE = re.compile(r"v?(\d+)(?:\.(\d+))?(?:\.(\d+))?")


def parse_version(tag: str) -> Tuple[int, ...]:
    """
    把版本字符串解析成可比较的元组。

    支持：
        "v0.2.1"     -> (0, 2, 1)
        "0.10.0"     -> (0, 10, 0)
        "1.2"        -> (1, 2, 0)
        "1"          -> (1, 0, 0)

    不支持预发布版本（alpha/beta/rc 等），当作同等正式版本处理。

    :raises ParseError: tag 完全无法解析
    """
    if not tag:
        raise ParseError("version tag 为空")
    m = _VERSION_RE.match(tag.strip())
    if not m:
        raise ParseError(f"无法解析版本号：{tag!r}")
    parts = []
    for g in m.groups():
        parts.append(int(g) if g is not None else 0)
    return tuple(parts)


def is_newer(latest: Tuple[int, ...], current: Tuple[int, ...]) -> bool:
    """
    判断 latest 是否比 current 新。

    用 zip + 默认 0 补齐长度，所以 (0, 10, 0) > (0, 2, 0) 正确。
    """
    # 补到等长
    n = max(len(latest), len(current))
    a = latest + (0,) * (n - len(latest))
    b = current + (0,) * (n - len(current))
    return a > b


# ==================== GitHub API ====================


def fetch_latest_release(repo: str, timeout: float = 15.0) -> dict:
    """
    GET https://api.github.com/repos/{repo}/releases/latest

    :raises NetworkError: 网络相关失败
    :raises ParseError: 返回的不是合法 JSON
    :raises UpdaterError: GitHub 返回 4xx/5xx（限流 / 仓库不存在等）
    """
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "intelligent-assistant-updater",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
    except urllib.error.HTTPError as exc:
        # 403 是限流；其他 4xx/5xx 走兜底
        raise UpdaterError(f"GitHub API 返回 HTTP {exc.code} {exc.reason}")
    except urllib.error.URLError as exc:
        raise NetworkError(f"网络请求失败：{exc.reason}")
    except TimeoutError as exc:
        raise NetworkError(f"网络超时：{exc}")

    try:
        return json.loads(data)
    except json.JSONDecodeError as exc:
        raise ParseError(f"GitHub 返回的不是合法 JSON：{exc}")


def find_asset(release: dict, name: str) -> Optional[dict]:
    """在 release 的 assets 列表里找指定文件名。找不到返回 None。"""
    for asset in release.get("assets", []):
        if asset.get("name") == name:
            return asset
    return None


_SHA256_RE = re.compile(r"SHA256[:\s]+([a-fA-F0-9]{64})", re.IGNORECASE)


def extract_sha256(notes: str) -> Optional[str]:
    """
    从 release notes 里正则提取 SHA256。

    约定：在 release body 里写一行 `SHA256: <64位hex>` 即可。
    """
    if not notes:
        return None
    m = _SHA256_RE.search(notes)
    return m.group(1).lower() if m else None


def file_sha256(path: Path, chunk: int = 1024 * 1024) -> str:
    """计算文件的 SHA256（hex 字符串）。"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            data = f.read(chunk)
            if not data:
                break
            h.update(data)
    return h.hexdigest()


# ==================== 下载 ====================


def download_to(
    url: str,
    dest: Path,
    progress_cb: Optional[Callable[[int, int], None]] = None,
    timeout: float = 60.0,
) -> None:
    """
    流式下载 url 到 dest。进度回调签名：cb(bytes_done, total_bytes)。
    total_bytes 可能为 0（服务器没给 Content-Length）。

    :raises NetworkError: 网络失败
    """
    req = urllib.request.Request(url, headers={"User-Agent": "intelligent-assistant-updater"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            done = 0
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as f:
                while True:
                    chunk = resp.read(64 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
                    done += len(chunk)
                    if progress_cb is not None:
                        try:
                            progress_cb(done, total)
                        except Exception:  # noqa: BLE001 —— 回调异常不应阻塞下载
                            pass
    except urllib.error.URLError as exc:
        raise NetworkError(f"下载失败：{exc.reason}")
    except TimeoutError as exc:
        raise NetworkError(f"下载超时：{exc}")


# ==================== 安装（批处理脚本）====================


def make_update_bat(new_exe: Path, target_exe: Path, log_path: Path) -> str:
    """
    生成替换用的 .bat 脚本内容。

    流程：
      1. 等主进程退出（轮询 tasklist，最多 30 秒）
      2. 把 new_exe move 到 target_exe（同磁盘是改名，跨磁盘是复制+删）
      3. 启动新版本
      4. 清理 .bat 自己
    """
    target_name = target_exe.name
    bat = f"""@echo off
chcp 65001 >nul
setlocal

REM 重定向日志，方便排查
echo [%date% %time%] 开始替换 {target_name} > "{log_path}"

REM 等待主进程退出（最多 30 秒）
set /a count=0
:wait_loop
tasklist /FI "IMAGENAME eq {target_name}" 2>NUL | find /I "{target_name}" >NUL
if "%ERRORLEVEL%"=="0" (
    set /a count+=1
    if %count% GTR 30 (
        echo [%date% %time%] 等待超时，强制继续 >> "{log_path}"
        goto do_replace
    )
    timeout /t 1 /nobreak >nul
    goto wait_loop
)

:do_replace
echo [%date% %time%] 主进程已退出，开始替换 >> "{log_path}"

REM 先删旧的（同磁盘 rename 不需要；move /y 跨磁盘会先复制再删）
if exist "{target_exe}" del /f /q "{target_exe}"

REM 移动新 exe 到位
move /y "{new_exe}" "{target_exe}"
if errorlevel 1 (
    echo [%date% %time%] 移动失败 >> "{log_path}"
    exit /b 1
)

echo [%date% %time%] 替换完成，启动新版本 >> "{log_path}"

REM 启动新版本
start "" "{target_exe}"

REM 清理自己
del /f /q "%~f0"
endlocal
"""
    return bat


def write_update_bat(new_exe: Path, target_exe: Path, log_path: Path) -> Path:
    """写 .bat 到 new_exe 同级目录，返回 bat 路径。"""
    bat_path = new_exe.parent / "update.bat"
    bat_path.write_text(make_update_bat(new_exe, target_exe, log_path), encoding="utf-8")
    return bat_path


def launch_update_bat(bat_path: Path) -> None:
    """异步启动 .bat（不阻塞当前进程）。"""
    # 用 cmd /c start 触发 bat，start 会让 bat 在新窗口里跑
    # 当前进程退出后 bat 才能删/替换目标 exe
    subprocess.Popen(
        ["cmd", "/c", "start", "/min", "", str(bat_path)],
        shell=False,
        close_fds=True,
    )


# ==================== 主类 ====================


class Updater:
    """
    升级器门面类。

    用法：
        updater = Updater()
        release = updater.check(force=True)
        if release:
            path = updater.download(release, progress_cb=...)
            updater.install_and_restart(path, target_exe)
    """

    def __init__(
        self,
        repo: str = "carlli666/demo",
        current_version: str = "0.1.0",
        asset_name: str = "intelligent assistant.exe",
    ):
        self.repo = repo
        self.current_version = current_version
        self.asset_name = asset_name

    def check(self, force: bool = False) -> Optional[ReleaseInfo]:
        """
        检查 GitHub 最新 release。

        - force=False：可能跳过（由调用方根据 last_check 时间决定）
        - force=True：无条件检查

        返回 ReleaseInfo（如果最新版比当前新）或 None（无更新 / 错误 / 已跳过）。

        失败全部静默（返回 None），不抛异常给 UI。
        """
        try:
            data = fetch_latest_release(self.repo)
        except UpdaterError:
            return None

        return self._parse_release(data)

    def _parse_release(self, data: dict) -> Optional[ReleaseInfo]:
        """从 GitHub 返回的 JSON 解析出 ReleaseInfo。"""
        try:
            tag = data["tag_name"]
            version_str = tag.lstrip("v")
            asset = find_asset(data, self.asset_name)
            if asset is None:
                return None  # asset 不存在，新版本无对应 exe

            current = parse_version(self.current_version)
            latest = parse_version(version_str)

            # 已跳过的版本直接跳过
            # （调用方在 check 前应用 skipped_version 过滤；这里只做基本比较）

            if not is_newer(latest, current):
                return None

            return ReleaseInfo(
                version=version_str,
                tag=tag,
                download_url=asset["browser_download_url"],
                size_bytes=int(asset.get("size", 0)),
                release_notes=data.get("body", "") or "",
                sha256=extract_sha256(data.get("body", "") or ""),
                asset_name=self.asset_name,
            )
        except (KeyError, ValueError, ParseError):
            return None

    def download(
        self,
        release: ReleaseInfo,
        progress_cb: Optional[Callable[[int, int], None]] = None,
        dest_dir: Optional[Path] = None,
    ) -> Path:
        """
        下载新版本到临时目录，返回本地路径。

        :param release: ReleaseInfo
        :param progress_cb: 进度回调 cb(bytes_done, total_bytes)
        :param dest_dir: 目标目录；默认用系统 temp
        :raises NetworkError: 下载失败
        """
        if dest_dir is None:
            dest_dir = Path(tempfile.gettempdir()) / "intelligent-assistant-updates"
        # 文件名加版本号和时间戳，避免覆盖旧文件
        filename = f"{self.asset_name.replace(' ', '_')}_v{release.version}_{int(time.time())}.exe"
        dest = dest_dir / filename
        download_to(release.download_url, dest, progress_cb=progress_cb)
        return dest

    def verify(self, path: Path, expected_sha256: Optional[str]) -> bool:
        """SHA256 校验。expected=None 时跳过校验返回 True。"""
        if expected_sha256 is None:
            return True
        try:
            return file_sha256(path) == expected_sha256.lower()
        except OSError:
            return False

    def install_and_restart(self, new_exe: Path, target_exe: Path) -> None:
        """
        触发替换流程（写 .bat + 起 bat + 关主程序）。

        调用后本进程应该尽快退出，bat 会在后台等待 + 替换 + 重启。
        """
        log_path = new_exe.parent / "update.log"
        bat_path = write_update_bat(new_exe, target_exe, log_path)
        launch_update_bat(bat_path)