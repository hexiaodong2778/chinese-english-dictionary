# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置 —— 单文件免安装 exe
========================================
把 app.py 与四个词库打进一个 exe。

说明：
  · dict.db（英语，约 240MB）较大，打进 exe 会让启动稍慢。
    这里采用「词库外置」策略：exe 只打包程序本身，词库
    放在 exe 同目录，既启动快，也方便日后单独更新词库。
  · 若想真正单文件内嵌词库，把 DATAS 里的 db 文件加进来即可。
  · 可选功能的密钥放外置的 dict_config.json（也不打包），
    这样用户改 key 不必重新打包，源码里的密钥也不会随 exe 泄露。
"""
import os

# PyInstaller 用 exec 执行 spec，不提供 __file__，需自行定位
try:
    BUILD = os.path.dirname(os.path.abspath(__file__))
except NameError:
    BUILD = os.path.abspath(os.getcwd())

# 词库默认外置（与 exe 同目录），因此不打包进 exe
DATAS = []

a = Analysis(
    [os.path.join(BUILD, "app.py")],
    pathex=[BUILD],
    binaries=[],
    datas=DATAS,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 大幅削减体积：排除用不到的重型模块
        #
        # ⚠ 注意：PySide6.QtMultimedia **不能排除**！
        #   发音功能用 QMediaPlayer 播放在线真人录音（mp3），
        #   依赖 QtMultimedia + QtMultimediaWidgets。
        #   之前这里排除过它，导致打包后发音静默失效。
        "tkinter", "matplotlib", "numpy", "pandas", "scipy",
        "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
        "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.QtCharts",
        "PySide6.QtDataVisualization",
        "PySide6.QtQuick", "PySide6.QtQml", "PySide6.QtBluetooth",
        "PySide6.QtDesigner", "PySide6.QtHelp", "PySide6.QtOpenGL",
        "PySide6.QtPdf", "PySide6.QtSql", "PySide6.QtTest",
        "PySide6.QtWebChannel", "PySide6.QtWebSockets",
        "PySide6.QtPositioning", "PySide6.QtLocation",
        "PySide6.QtNfc", "PySide6.QtRemoteObjects", "PySide6.QtSensors",
        "PySide6.QtSerialPort", "PySide6.QtStateMachine",
        "PySide6.QtSvgWidgets", "PySide6.QtUiTools",
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="查单词",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # 正式版：不弹控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(BUILD, "app_icon.ico"),   # 应用图标
    version=os.path.join(BUILD, "version_info.txt")
    if os.path.exists(os.path.join(BUILD, "version_info.txt")) else None,
)
