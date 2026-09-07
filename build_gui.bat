@echo off
REM ============================================
REM intelligent assistant 桌面 GUI 打包脚本
REM ============================================
REM
REM 把 tkinter GUI 打包成单文件 .exe，方便双击启动。
REM 产物：dist\intelligent assistant.exe（约 15 MB）
REM 图标：intelligent_assistant.ico（用 make_icon.py 生成）
REM
REM 用法（在项目根目录双击或在 cmd 里执行）：
REM     build_gui.bat
REM
REM 依赖：先激活虚拟环境并安装 PyInstaller
REM     .\venv\Scripts\Activate.ps1
REM     pip install pyinstaller

echo ============================================
echo   正在打包 intelligent assistant.exe ...
echo ============================================

REM 检查虚拟环境
if not exist "venv\Scripts\python.exe" (
    echo [错误] 没找到 venv\Scripts\python.exe，请先创建虚拟环境
    pause
    exit /b 1
)

REM 检查 PyInstaller
venv\Scripts\python.exe -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo [提示] 未安装 PyInstaller，正在安装 ...
    venv\Scripts\python.exe -m pip install pyinstaller
    if errorlevel 1 (
        echo [错误] PyInstaller 安装失败
        pause
        exit /b 1
    )
)

REM 打包（--onefile 单文件，--windowed 不弹黑窗，--icon 自定义图标）
REM   --add-data 把 ico 打进 exe 数据区，让运行时能从 sys._MEIPASS 找到
venv\Scripts\python.exe -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name "intelligent assistant" ^
    --icon intelligent_assistant.ico ^
    --add-data "intelligent_assistant.ico;." ^
    --clean ^
    run_gui.py

if errorlevel 1 (
    echo [错误] 打包失败
    pause
    exit /b 1
)

echo ============================================
echo   打包完成！
echo   产物：dist\intelligent assistant.exe
echo   双击它即可启动 GUI
echo ============================================
pause