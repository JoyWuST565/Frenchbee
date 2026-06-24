# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import os
import sys


python_home = Path(sys.base_prefix)
python_dlls = python_home / "DLLs"
python_lib = python_home / "Lib"
os.environ["TCL_LIBRARY"] = str(python_home / "tcl" / "tcl8.6")
os.environ["TK_LIBRARY"] = str(python_home / "tcl" / "tk8.6")

a = Analysis(
    ["flight_manager.py"],
    pathex=[],
    binaries=[
        (str(python_dlls / "_tkinter.pyd"), "."),
        (str(python_dlls / "tcl86t.dll"), "."),
        (str(python_dlls / "tk86t.dll"), "."),
    ],
    datas=[
        ("flight_schedule.db", "."),
        ("frenchbee_flight_manager.ico", "."),
        (str(python_home / "tcl"), "tcl"),
        (str(python_lib / "tkinter"), "tkinter"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="FrenchbeeFlightManager",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="frenchbee_flight_manager.ico",
)
