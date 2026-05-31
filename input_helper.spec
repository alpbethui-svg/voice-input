# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# 不把大模型/大型可选训练栈打进安装包。
# Whisper 模型、Ollama 模型、RapidOCR 模型缓存均在用户机器上按需下载/准备。
EXCLUDES = [
    "torch",
    "torchvision",
    "torchaudio",
    "tensorflow",
    "tensorflow_intel",
    "jax",
    "jaxlib",
]

a = Analysis(
    ["voice_input.pyw"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=["model_setup"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="输入助手",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
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
    upx=True,
    upx_exclude=[],
    name="输入助手",
)
