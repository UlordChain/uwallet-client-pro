# -*- mode: python -*-

block_cipher = None


a = Analysis(['uwallet'],
             pathex=['/Users/shakawu/workspace/github/uwallet-client-pro'],
             binaries=[],
             datas=[],
             hiddenimports=['queue'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='uwallet',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False , version='version', icon='uwallet.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='uwallet')
app = BUNDLE(coll,
             name='uwallet.app',
             icon='uwallet.ico',
             bundle_identifier=None)
