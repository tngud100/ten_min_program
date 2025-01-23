# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        #('static', 'static'),  # static 폴더 전체를 포함
        #('static/image', 'static/image'),  # image 폴더도 명시적으로 포함
        ('.env', '.'),  # .env 파일을 루트 디렉토리에 포함
    ],
    hiddenimports=[
        # Database
        'aiomysql',
        'pymysql',
        'sqlalchemy.ext.asyncio',
        'sqlalchemy.orm',
        'sqlalchemy.ext.declarative',
        'sqlalchemy.dialects.mysql',
        
        # Windows specific
        'win32api',
        'win32con',
        'pywinauto',
        
        # Async
        'asyncio',
        'contextlib',
        
        # Environment
        'dotenv',
        
        # MySQL Replication
        'pymysqlreplication',
        'pymysqlreplication.row_event'
        
        # Logging
        'src.logging',
        'src.logging.log_window',
        'src.logging.print_logger'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ten_min',
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
    uac_admin=True,
    icon='static/ten.ico',
)

# coll = COLLECT(
#    exe,
#    a.binaries,
#    a.datas,
#    strip=False,
#    upx=True,
#    upx_exclude=[],
#    name='app',
# )
