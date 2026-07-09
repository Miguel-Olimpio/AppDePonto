# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

project_root = Path(SPECPATH)
icon_path = project_root / "icon" / "icon.ico"
bot_node_dir = project_root / "bot_node"


def collect_folder_datas(folder, target, ignored_names=None):
    ignored_names = set(ignored_names or [])
    items = []
    for path in folder.rglob("*"):
        relative = path.relative_to(folder)
        if any(part in ignored_names for part in relative.parts):
            continue
        if path.is_file():
            dest = Path(target) / relative.parent
            items.append((str(path), str(dest)))
    return items

datas = collect_data_files("ttkbootstrap")
datas += collect_data_files("reportlab")
# Pastas editaveis do cliente (data, pdfs, backups e sessao WhatsApp) nao entram aqui.
# Elas sao criadas/reutilizadas ao lado do executavel para permitir atualizar trocando apenas o .exe.
if icon_path.exists():
    datas.append((str(icon_path), "icon"))
if bot_node_dir.exists():
    datas += collect_folder_datas(bot_node_dir, "bot_node", ignored_names={".wwebjs_cache"})

a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "openpyxl.cell._writer",
        "openpyxl.styles",
        "reportlab.pdfbase._fontdata",
        "reportlab.pdfbase.ttfonts",
    ],
    hookspath=[str(project_root / "pyinstaller_hooks")],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ControlePontoTarefas",
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
    icon=str(icon_path) if icon_path.exists() else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ControlePontoTarefas",
)
