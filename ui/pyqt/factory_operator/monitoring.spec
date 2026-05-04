# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Casting Factory Monitoring App v1.0.

사용법:
    cd monitoring
    source venv/bin/activate
    pyinstaller monitoring.spec --clean --noconfirm

결과물:
    dist/CastingFactoryMonitoring.app  (macOS .app 번들)
    dist/CastingFactoryMonitoring/     (onedir 번들)
"""
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# 런타임에 로드되는 hidden 모듈들
hiddenimports = [
    "PyQt5.sip",
    "PyQt5.QtChart",
    "PyQt5.QtCore",
    "PyQt5.QtGui",
    "PyQt5.QtWidgets",
    # V6 canonical (Phase D): MQTT 제거, Management gRPC 직결만
    "grpc",
    "grpc._channel",
    "app.generated.management_pb2",
    "app.generated.management_pb2_grpc",
    "app",
    "app.pages",
    "app.widgets",
    "app.pages.dashboard",
    "app.pages.logistics",
    "app.pages.map",
    "app.pages.operations",
    "app.pages.pp_worker",
    "app.pages.production",
    "app.pages.quality",
    "app.pages.schedule",
    "app.pages.storage",
    "app.widgets.alert_widgets",
    "app.widgets.amr_card",
    "app.widgets.charts",
    "app.widgets.conveyor_card",
    "app.widgets.defect_panels",
    "app.widgets.factory_map",
    "app.widgets.gauges",
    "app.widgets.sorter_dial",
    "app.widgets.warehouse_rack",
]

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("resources/styles.qss", "resources"),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CastingFactoryMonitoring",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="CastingFactoryMonitoring",
)

app = BUNDLE(
    coll,
    name="CastingFactoryMonitoring.app",
    icon=None,
    bundle_identifier="com.casting-factory.monitoring",
    version="1.0.0",
    info_plist={
        "CFBundleName": "Casting Factory Monitoring",
        "CFBundleDisplayName": "주물공장 모니터링",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "LSMinimumSystemVersion": "11.0",
        "NSHighResolutionCapable": True,
    },
)
