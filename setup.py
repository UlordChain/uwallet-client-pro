#!/usr/bin/env python2

# python setup.py sdist --format=zip,gztar

from setuptools import setup
import os
import sys
import platform
import imp
import argparse

version = imp.load_source('version', 'lib/version.py')

if sys.version_info[:3] < (2, 7, 0):
    sys.exit("Error: UWallet requires Python version >= 2.7.0...")

data_files = []

if platform.system() in ['Linux', 'FreeBSD', 'DragonFly']:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root=', dest='root_path', metavar='dir', default='/')
    opts, _ = parser.parse_known_args(sys.argv[1:])
    usr_share = os.path.join(sys.prefix, "share")
    if not os.access(opts.root_path + usr_share, os.W_OK) and \
       not os.access(opts.root_path, os.W_OK):
        if 'XDG_DATA_HOME' in os.environ.keys():
            usr_share = os.environ['XDG_DATA_HOME']
        else:
            usr_share = os.path.expanduser('~/.local/share')
    data_files += [
        (os.path.join(usr_share, 'applications/'), ['uwallet.desktop']),
        (os.path.join(usr_share, 'pixmaps/'), ['icons/uwallet.png'])
    ]

setup(
    name="UWallet",
    version=version.UWallet_VERSION,
    install_requires=[
        'slowaes>=0.1a1',
        'ecdsa>=0.9',
        'pbkdf2',
        'requests',
        'qrcode',
        'protobuf',
        'dnspython',
        'jsonrpclib',
    ],
    packages=[
        'uwallet',
        'uwallet_gui',
        'uwallet_gui.qt',
        'uwallet_plugins',
        'uwallet_plugins.audio_modem',
        'uwallet_plugins.cosigner_pool',
        'uwallet_plugins.email_requests',
        'uwallet_plugins.exchange_rate',
        'uwallet_plugins.greenaddress_instant',
        'uwallet_plugins.hw_wallet',
        'uwallet_plugins.keepkey',
        'uwallet_plugins.labels',
        'uwallet_plugins.ledger',
        'uwallet_plugins.plot',
        'uwallet_plugins.trezor',
        'uwallet_plugins.trustedcoin',
        'uwallet_plugins.virtualkeyboard',
    ],
    package_dir={
        'uwallet': 'lib',
        'uwallet_gui': 'gui',
        'uwallet_plugins': 'plugins',
    },
    package_data={
        'uwallet': [
            'www/index.html',
            'wordlist/*.txt',
            'locale/*/LC_MESSAGES/uwallet.mo',
        ]
    },
    scripts=['uwallet'],
    data_files=data_files,
    description="Lightweight Bitcoin Wallet",
    author="Thomas Voegtlin",
    author_email="",
    license="MIT Licence",
    url="http://www.ulord.org/",
    long_description="""Lightweight Bitcoin Wallet"""
)
