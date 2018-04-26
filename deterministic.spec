# -*- mode: python -*-

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


# see https://github.com/pyinstaller/pyinstaller/issues/2005
hiddenimports = []
#hiddenimports += collect_submodules('trezorlib')
#hiddenimports += collect_submodules('btchip')
#hiddenimports += collect_submodules('keepkeylib')

datas = [
    ('lib/wordlist/english.txt', 'uwallet/wordlist'),
    ('plugins', 'uwallet_plugins'),
]
#datas += collect_data_files('trezorlib')
#datas += collect_data_files('btchip')
#datas += collect_data_files('keepkeylib')

# We don't put these files in to actually include them in the script but to make the Analysis method scan them for imports
a = Analysis(['uwallet',
              'gui/qt/main_window.py',
              'gui/text.py',
              'lib/util.py',
              'lib/wallet.py',
              'lib/simple_config.py',
              'lib/bitcoin.py',
              'lib/dnssec.py',
              'lib/commands.py',
              'plugins/cosigner_pool/qt.py',
              'plugins/email_requests/qt.py',
              'plugins/trezor/client.py',
              'plugins/trezor/qt.py',
              'plugins/keepkey/qt.py',
              'plugins/ledger/qt.py',
              #'packages/requests/utils.py'
              ],
             datas=datas,
             #pathex=['lib', 'gui', 'plugins'],
             hiddenimports=hiddenimports,
             hookspath=[])


# http://stackoverflow.com/questions/19055089/pyinstaller-onefile-warning-pyconfig-h-when-importing-scipy-or-scipy-signal
for d in a.datas:
    if 'pyconfig' in d[0]: 
        a.datas.remove(d)
        break

# hotfix for #3171 (pre-Win10 binaries)
a.binaries = [x for x in a.binaries if not x[1].lower().startswith(r'c:\windows')]

pyz = PYZ(a.pure)


#####
# "standalone" exe with all dependencies packed into it

#options = [ ('v', None, 'OPTION')]  - put this in the following exe list to debug and turn console=true

exe_standalone = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,  
    name="uwallet",
    debug=False,
    strip=None,
    upx=False,
    icon='uwallet.ico',
    console=False)
    # console=True makes an annoying black box pop up, but it does make Electrum output command line commands, with this turned off no output will be given but commands can still be used

exe_portable = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name="uwallet-portable.exe",
    debug=False,
    strip=None,
    upx=False,
    icon='uwallet.ico',
    console=False)

#####
# exe and separate files that NSIS uses to build installer "setup" exe

exe_dependent = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="uwallet",
    debug=False,
    strip=None,
    upx=False,
    icon='uwallet.ico',
    console=False)

coll = COLLECT(
    exe_dependent,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=None,
    upx=True,
    debug=False,
    icon='uwallet.ico',
    console=False,
    name='uwallet')
