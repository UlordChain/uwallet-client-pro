#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2012 thomasv@gitorious
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import sys, time, threading
import os, json, traceback
import shutil
import socket
import weakref
import webbrowser
import csv
from decimal import Decimal
import base64
from functools import partial

import PyQt4
from PyQt4.QtGui import *
from PyQt4.QtCore import *
import PyQt4.QtCore as QtCore
import icons_rc

from uwallet.bitcoin import COIN, is_valid, TYPE_ADDRESS
from uwallet.plugins import run_hook
from uwallet.i18n import _
from uwallet.util import (block_explorer, block_explorer_info, format_time,
                           block_explorer_URL, format_satoshis, PrintError,
                           format_satoshis_plain, NotEnoughFunds, StoreDict,
                           UserCancelled)
from uwallet import Transaction, mnemonic #
from uwallet import util, bitcoin, commands, coinchooser
from uwallet import SimpleConfig, paymentrequest
from uwallet.wallet import Wallet, Multisig_Wallet
from uwallet.blockchain import Blockchain
from uwallet.version import UWallet_VERSION
from uwallet.privatekey import BitcoinPrivateKey
from amountedit import BTCAmountEdit, MyLineEdit, BTCkBEdit
from network_dialog import NetworkDialog
from qrcodewidget import QRCodeWidget, QRDialog
from qrtextedit import ShowQRTextEdit
from transaction_dialog import show_transaction
from title import TitleWidget
from IP4Edit import Ip4Edit
import multiprocessing
from util import *
import math
import mmap
import contextlib
import subprocess
import win32api
systemname = platform.system()
if systemname == 'darwin':
    is_macos = True
else:
    is_macos = False

class StatusBarButton(QPushButton):
    def __init__(self, icon, tooltip, func):
        QPushButton.__init__(self, icon, '')
        self.setToolTip(tooltip)
        self.setFlat(True)
        self.setMaximumWidth(25)
        self.clicked.connect(self.onPress)
        self.func = func
        self.setIconSize(QSize(25,25))

    def onPress(self, checked=False):
        '''Drops the unwanted PyQt4 "checked" argument'''
        self.func()

    def keyPressEvent(self, e):
        if e.key() == QtCore.Qt.Key_Return:
            self.func()


from uwallet.paymentrequest import PR_UNPAID, PR_PAID, PR_UNKNOWN, PR_EXPIRED

class UWalletWindow(QMainWindow, MessageBoxMixin, PrintError):

    def __init__(self, gui_object, wallet):
        QMainWindow.__init__(self)

        self.fee_level = [_('Within 25 blocks'), _('Within 10 blocks'), _('Within 5 blocks'), _('Within 2 blocks'), _('In the next block')]
        f = QFile("wallet.qss")
        f.open(QFile.ReadOnly)
        styleSheet = unicode(f.readAll(), encoding='utf8')
        self.setStyleSheet(styleSheet)
        f.close()
        self.languages = {
            '': _('Default'),
            'zh_CN': _('Chinese'),
            'en_UK': _('English'),
        }

        self.expiration_values = [
            (_('1 hour'), 60 * 60),
            (_('1 day'), 24 * 60 * 60),
            (_('1 week'), 7 * 24 * 60 * 60),
            (_('Never'), None)
        ]

        self.setMinimumSize(QSize(800, 530))
        self.mouse_press_status = False
        self.startPos = self.pos()
        self.ismaxsize = False
        self.geo = self.geometry()
        self.setWindowIcon(QIcon(':icons/electrum_light_icon.png'))
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        # self.set_transparency(True)
        self.currentPos = None

        self.gui_object = gui_object
        self.config = config = gui_object.config
        self.network = gui_object.daemon.network
        slpcount = 0
        # try:
        #     if os.path.exists("clearIconBuf.bat"):
        #     #     si = subprocess.STARTUPINFO()
        #     #     si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        #     #     subprocess.call('clearIconBuf.bat', startupinfo=si)
        #         os.system("clearIconBuf.bat")
        #         os.remove("clearIconBuf.bat")
        # except:
        #     pass

        # rVersion = self.getRemoteVersion()
        # if rVersion != UWallet_VERSION and rVersion != '':
        #     if self.question(_("New version found. Is it updated?"),self):
        #         win32api.ShellExecute(0, 'open', r'UpdateAppClient.exe', '', '', 1)
        #         sys.exit(0)
        if not is_macos:
            while self.network.blockchain.height_diff==0 and slpcount<50:
                if self.network.blockchain.downloading:
                    break
                time.sleep(0.1)
                slpcount +=1
                print "sleep"
            if self.network.blockchain.downloading==False:
                try:
                    if self.network.blockchain.height_diff > self.network.blockchain.CHUNK_SIZE-1:
                        with open("process.dat", "w") as f:
                            f.write('\x00' * 1024)
                        with open('process.dat', 'r+') as f:
                            with contextlib.closing(mmap.mmap(f.fileno(), 1024, access=mmap.ACCESS_WRITE)) as m:
                                m.seek(0)
                                s = str(0) + "/" + str(self.network.blockchain.height_diff)
                                s.rjust(1024, '\x00')
                                m.write(s)
                                m.flush()
                        # os.system("python progressbarWindow.py")
                        si = subprocess.STARTUPINFO()
                        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                        subprocess.call('progressbarWindow.exe', startupinfo=si)
                        # if (self.network.max_block_height - self.network.blockchain.local_height) > self.network.blockchain.CHUNK_SIZE-1:
                        #     sys.exit(0)
                except Exception,ex:
                    print ex

        self.invoices = gui_object.invoices
        self.contacts = gui_object.contacts
        self.tray = gui_object.tray
        self.app = gui_object.app
        self.cleaned_up = False
        self.sb = self.create_status_bar()
        self.need_update = threading.Event()
        self.decimal_point = config.get('decimal_point', 8)
        self.num_zeros     = int(config.get('num_zeros',6))
        self.completions = QStringListModel()

        self.tabs = tabs = QTabWidget(self)
        # tabs.setContentsMargins(9,9,9,9)
        tabs.addTab(self.create_history_tab(), _('History') )
        tabs.addTab(self.create_send_tab(), _('Send') )
        tabs.addTab(self.create_receive_tab(), _('Receive') )
        self.addresses_tab = self.create_addresses_tab()

        tabs.addTab(self.addresses_tab, _('Addresses'))
        tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        top_layout = QVBoxLayout()
        top_layout.setSpacing(0)
        self.title_widget = TitleWidget(self)
        top_layout.addWidget(self.title_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)


        self.title_widget.btn_close.clicked.connect(self.close)
        self.title_widget.btn_min.clicked.connect(self.slot_minimize)
        self.title_widget.btn_max.clicked.connect(self.slot_maximize)

        top_layout.addWidget(tabs)
        twidget = QWidget(self)
        twidget.setLayout(top_layout)
        twidget.setObjectName("twidget")

        main_layout.addWidget(twidget)
        main_layout.addWidget(self.sb)

        widget = QWidget(self)
        widget.setLayout(main_layout)
        widget.setObjectName("mwidget")
        self.setCentralWidget(widget)
        self.setContentsMargins(9,9,9,9)

        wrtabs = weakref.proxy(tabs)
        QShortcut(QKeySequence("Ctrl+W"), self, self.close)
        QShortcut(QKeySequence("Ctrl+Q"), self, self.close)
        QShortcut(QKeySequence("Ctrl+R"), self, self.update_wallet)
        QShortcut(QKeySequence("Ctrl+PgUp"), self, lambda: wrtabs.setCurrentIndex((wrtabs.currentIndex() - 1)%wrtabs.count()))
        QShortcut(QKeySequence("Ctrl+PgDown"), self, lambda: wrtabs.setCurrentIndex((wrtabs.currentIndex() + 1)%wrtabs.count()))

        for i in range(wrtabs.count()):
            QShortcut(QKeySequence("Alt+" + str(i + 1)), self, lambda i=i: wrtabs.setCurrentIndex(i))

        self.connect(self, QtCore.SIGNAL('payment_request_ok'), self.payment_request_ok)
        self.connect(self, QtCore.SIGNAL('payment_request_error'), self.payment_request_error)
        self.history_list.setFocus(True)

        # network callbacks
        if self.network:
            self.connect(self, QtCore.SIGNAL('network'), self.on_network_qt)
            interests = ['updated', 'new_transaction', 'status',
                         'banner', 'verified']
            self.network.register_callback(self.on_network, interests)

        self.is_max = False
        self.payment_request = None
        self.checking_accounts = False
        self.qr_window = None
        self.not_enough_funds = False
        self.pluginsdialog = None
        self.fetch_alias()
        self.require_fee_update = False
        self.tx_notifications = []
        self.tl_windows = []
        self.load_wallet(wallet)
        self.connect_slots(gui_object.timer)
        self.is_show_warning =False
        self.set_receive_address()

    def is_macos(self):
        return is_macos

    def getRemoteVersion(self):
        try:
            while True:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(('wallet1.ulord.one', 57888))  # 118.190.145.8
                name = 'get_version'
                sock.sendall(name)
                response = sock.recv(8192)
                # todo:equal this app version if different set down = True
                sock.sendall('bye')
                sock.close()
                return str(response).strip()
        except:
            return ''

    def get_version(self):
        return  UWallet_VERSION

    def warn_version(self):
        if self.network.cli_version !='' and UWallet_VERSION!=self.network.cli_version:
            if not self.is_show_warning:
                self.is_show_warning = True
                if self.question(_('Your wallet version is too old, please go to ulord. One to download the new wallet.')):
                    f = lambda: webbrowser.open("http://ulord.one/download.html")
                    f()

    def resizeEvent(self,event):
        print "resizeEvent isHiden:",self.is_hidden()

    def hideEvent(self, event):
        # print "hideEvent isHiden:", self.is_hidden()
        self.set_transparency(False)

    def showEvent(self, *args, **kwargs):
        # print "showEvent isHiden:", self.is_hidden()
        self.set_transparency(True)

    def set_transparency(self, enabled):
        if enabled:
            self.setAutoFillBackground(False)
        else:
            self.setAttribute(Qt.WA_NoSystemBackground, False)

        self.setAttribute(Qt.WA_TranslucentBackground, enabled)
        self.repaint()

    def mousePressEvent(self, event):
        try:
            self.currentPos = event.pos()
        except Exception:
            return

    def mouseMoveEvent(self, event):
        try:
            self.move(QPoint(self.pos() + event.pos() - self.currentPos))
        except Exception:
            return

    def slot_minimize(self):
        # self.showMinimized()
        self.hide()

    def slot_maximize(self):
        if self.ismaxsize:
            self.setContentsMargins(9, 9, 9, 9)
            self.geo.setWidth(800)
            self.geo.setHeight(530)
            self.setGeometry(self.geo)
            # self.setGeometry(QRect(800, 530))
            self.ismaxsize = False
        else:
            self.setContentsMargins(0, 0, 0, 0)
            self.geo = self.geometry()
            self.setGeometry(QApplication.desktop().availableGeometry())
            self.ismaxsize = True

    def paintEvent(self, event):
        if not is_macos:
            m = 9
            path = QPainterPath()
            path.setFillRule(Qt.WindingFill)
            path.addRect(m, m, self.width() - m * 2, self.height() - m * 2)
            painter = QPainter(self)
            painter.fillPath(path, QBrush(Qt.white))
            color = QColor(100, 100, 100, 30)
            for i in range(m):
                path = QPainterPath()
                path.setFillRule(Qt.WindingFill)
                path.addRoundRect(m - i, m - i, self.width() - (m - i) * 2, self.height() - (m - i) * 2, 1, 1)
                color.setAlpha(90 - math.sqrt(i) * 30)
                painter.setPen(QPen(color, 1, Qt.SolidLine))
                painter.drawRoundRect(QRect(m - i, m - i, self.width() - (m - i) * 2, self.height() - (m - i) * 2), 0, 0)

    def toggle_addresses_tab(self):
        show_addr = not self.config.get('show_addresses_tab', False)
        self.config.set_key('show_addresses_tab', show_addr)
        if show_addr:
            self.tabs.insertTab(3, self.addresses_tab, _('Addresses'))
        else:
            i = self.tabs.indexOf(self.addresses_tab)
            self.tabs.removeTab(i)

    def push_top_level_window(self, window):
        '''Usecd for e.g. tx dialog box to ensure new dialogs are appropriately
        parented.  This used to be done by explicitly providing the parent
        window, but that isn't something hardware wallet prompts know.'''
        self.tl_windows.append(window)

    def pop_top_level_window(self, window):
        self.tl_windows.remove(window)

    def top_level_window(self):
        '''Do the right thing in the presence of tx dialog windows'''
        override = self.tl_windows[-1] if self.tl_windows else None
        return self.top_level_window_recurse(override)

    def diagnostic_name(self):
        return "%s/%s" % (PrintError.diagnostic_name(self),
                          self.wallet.basename() if self.wallet else "None")

    def is_hidden(self):
        return self.isMinimized() or self.isHidden()

    def show_or_hide(self):
        if self.is_hidden():
            self.bring_to_top()
        else:
            self.hide()

    def bring_to_top(self):
        self.show()
        self.raise_()

    def on_error(self, exc_info):
        if not isinstance(exc_info[1], UserCancelled):
            erro = exc_info[1]
            if isinstance(erro,util.InvalidPassword):
                title = "UWalletLite"
                text = _("Incorrect password")
                icontype = "warm"
                qm = QMessageBoxEx(title, text, self, icontype)
                qm.exec_()
            traceback.print_exception(*exc_info)
            self.show_error((exc_info[1]))


    def on_network(self, event, *args):
        if event == 'updated':
            self.need_update.set()
        elif event == 'new_transaction':
            self.tx_notifications.append(args[0])
        elif event in ['status', 'banner', 'verified']:
            # Handle in GUI thread
            self.emit(QtCore.SIGNAL('network'), event, *args)
        else:
            self.print_error("unexpected network message:", event, args)

    def on_network_qt(self, event, *args):
        # Handle a network message in the GUI thread
        if event == 'status':
            self.update_status()
        # elif event == 'banner':
        #     self.console.showMessage("")
        elif event == 'verified':
            self.history_list.update_item(*args)
        else:
            self.print_error("unexpected network_qt signal:", event, args)

    def fetch_alias(self):
        self.alias_info = None
        alias = self.config.get('alias')
        if alias:
            alias = str(alias)
            def f():
                self.alias_info = self.contacts.resolve_openalias(alias)
                self.emit(SIGNAL('alias_received'))
            t = threading.Thread(target=f)
            t.setDaemon(True)
            t.start()

    def close_wallet(self):
        if self.wallet:
            self.print_error('close_wallet', self.wallet.storage.path)
        run_hook('close_wallet', self.wallet)

    def load_wallet(self, wallet):
        wallet.thread = TaskThread(self, self.on_error)
        self.wallet = wallet
        self.update_recently_visited(wallet.storage.path)
        # address used to create a dummy transaction and estimate transaction fee
        self.history_list.update()
        self.need_update.set()
        # Once GUI has been initialized check if we want to announce something since the callback has been called before the GUI was initialized
        self.notify_transactions()
        # update menus
        self.seed_menu.setEnabled(self.wallet.has_seed())
        self.mpk_menu.setEnabled(self.wallet.is_deterministic())
        self.update_lock_icon()
        self.update_buttons_on_seed()
        # self.update_console()
        self.clear_receive_tab()
        # self.request_list.update()
        self.tabs.show()
        self.init_geometry()
        if self.config.get('hide_gui') and self.gui_object.tray.isVisible():
            self.hide()
        else:
            self.show()
        self.watching_only_changed()
        run_hook('load_wallet', wallet, self)

    def init_geometry(self):
        winpos = self.wallet.storage.get("winpos-qt")
        try:
            screen = self.app.desktop().screenGeometry()
            assert screen.contains(QRect(*winpos))
            self.setGeometry(*winpos)
        except:
            self.print_error("using default geometry")
            self.setGeometry(100, 100, 840, 400)

    def watching_only_changed(self):
        title = 'UWalletLite %s  -  %s' % (self.wallet.uwallet_version,
                                        self.wallet.basename())
        extra = [self.wallet.storage.get('wallet_type', '?')]
        if self.wallet.is_watching_only():
            self.warn_if_watching_only()
            extra.append(_('watching only'))
        title += '  [%s]'% ', '.join(extra)
        self.setWindowTitle(title)
        self.password_menu.setEnabled(self.wallet.can_change_password())
        self.import_privkey_menu.setVisible(self.wallet.can_import_privkey())
        self.import_address_menu.setVisible(self.wallet.can_import_address())
        self.export_menu.setEnabled(self.wallet.can_export())

    def warn_if_watching_only(self):
        if self.wallet.is_watching_only():
            msg = ' '.join([
                _("This wallet is watching-only."),
                _("This means you will not be able to spend Ulord with it."),
                _("Make sure you own the seed phrase or the private keys, before you request Ulord to be sent to this wallet.")
            ])
            self.show_warning(msg, title=_('Information'))

    def open_wallet(self):
        wallet_folder = self.get_wallet_folder()
        filename = unicode(QFileDialog.getOpenFileName(self, "Select your wallet file", wallet_folder))
        if not filename:
            return
        self.gui_object.new_window(filename)


    def backup_wallet(self):
        path = self.wallet.storage.path
        wallet_folder = os.path.dirname(path)
        filename = unicode( QFileDialog.getSaveFileName(self, _('Enter a filename for the copy of your wallet'), wallet_folder) )
        if not filename:
            return

        new_path = os.path.join(wallet_folder, filename)
        if new_path != path:
            try:
                shutil.copy2(path, new_path)
                self.show_message(_("A copy of your wallet file was created in")+" '%s'" % str(new_path), title=_("Wallet backup created"))
            except (IOError, os.error), reason:
                self.show_critical(_("UWalletLite was unable to copy your wallet file to the specified location.") + "\n" + str(reason), title=_("Unable to create backup"))

    def update_recently_visited(self, filename):
        recent = self.config.get('recently_open', [])
        if filename in recent:
            recent.remove(filename)
        print 'filename:', filename#.decode('gbk').encode('utf-8')
        recent.insert(0, filename)
        print 'recent0:', recent
        recent = recent[:5]
        print 'recent1:', recent
        self.config.set_key('recently_open', recent)
        self.recently_visited_menu.clear()
        for i, k in enumerate(sorted(recent)):
            b = os.path.basename(k)
            def loader(k):
                return lambda: self.gui_object.new_window(k)
            self.recently_visited_menu.addAction(b, loader(k)).setShortcut(QKeySequence("Ctrl+%d"%(i+1)))
        self.recently_visited_menu.setEnabled(len(recent))

    def get_wallet_folder(self):
        return os.path.dirname(os.path.abspath(self.config.get_wallet_path()))

    def new_wallet(self):
        wallet_folder = self.get_wallet_folder()
        i = 1
        while True:
            filename = "wallet_%d" % i
            if filename in os.listdir(wallet_folder):
                i += 1
            else:
                break
        aa = _('Enter file name')
        filename = line_dialog(self, _('New Wallet'), aa
                               + ':', _('OK'), filename)
        if not filename:
            return
        full_path = os.path.join(wallet_folder, filename)
        if os.path.exists(full_path):
            self.show_critical(_("File exists"))
            return
        self.gui_object.start_new_window(full_path, None)

    def init_menubar(self):
        if is_macos:
            menubar = self.menuBar()
            menubar.setNativeMenuBar(False)
        else:
            menubar = QMenuBar()
            menubar.setStyleSheet("padding-top:2px;")
        # menubar.setMinimumSize(QtCore.QSize(0, 35))
        file_menu = menubar.addMenu(_("&File"))
        self.recently_visited_menu = file_menu.addMenu(_("&Recently open"))
        file_menu.addAction(_("&Open"), self.open_wallet).setShortcut(QKeySequence.Open)
        file_menu.addAction(_("&New/Restore"), self.new_wallet).setShortcut(QKeySequence.New)
        file_menu.addAction(_("&Save Copy"), self.backup_wallet).setShortcut(QKeySequence.SaveAs)
        file_menu.addSeparator()
        file_menu.addAction(_("&Quit"), self.close)

        wallet_menu = menubar.addMenu(_("&Wallet"))
        # wallet_menu.addAction(_("&New contact"), self.new_contact_dialog)
        wallet_menu.addSeparator()

        self.password_menu = wallet_menu.addAction(_("&Password"), self.change_password_dialog)
        self.seed_menu = wallet_menu.addAction(_("&Seed"), self.show_seed_dialog)
        self.mpk_menu = wallet_menu.addAction(_("&Master Public Keys"), self.show_master_public_keys)

        wallet_menu.addSeparator()
        labels_menu = wallet_menu.addMenu(_("&Labels"))
        labels_menu.addAction(_("&Import"), self.do_import_labels)
        labels_menu.addAction(_("&Export"), self.do_export_labels)

        self.private_keys_menu = wallet_menu.addMenu(_("&Private keys"))
        # self.private_keys_menu.addAction(_("&Sweep"), self.sweep_key_dialog)
        self.import_privkey_menu = self.private_keys_menu.addAction(_("&Import"), self.do_import_privkey)
        self.export_menu = self.private_keys_menu.addAction(_("&Export"), self.export_privkeys_dialog)
        self.import_address_menu = wallet_menu.addAction(_("Import addresses"), self.import_addresses)
        wallet_menu.addAction(_("&Export History"), self.export_history_dialog)
        # wallet_menu.addAction(_("Search"), self.toggle_search).setShortcut(QKeySequence("Ctrl+S"))
        # wallet_menu.addAction(_("Addresses"), self.toggle_addresses_tab).setShortcut(QKeySequence("Ctrl+A"))

        tools_menu = menubar.addMenu(_("&Tools"))

        # Settings / Preferences are all reserved keywords in OSX using this as work around
        tools_menu.addAction(_("UWalletLite preferences") if sys.platform == 'darwin' else _("Preferences"), self.settings_dialog)
        tools_menu.addAction(_("&Network"), self.run_network_dialog)
        # tools_menu.addAction(_("&Plugins"), self.plugins_dialog)
        tools_menu.addSeparator()
        tools_menu.addAction(_("&Sign/verify message"), self.sign_verify_message)
        tools_menu.addAction(_("&Encrypt/decrypt message"), self.encrypt_message)
        tools_menu.addSeparator()

        paytomany_menu = tools_menu.addAction(_("&Pay to many"), self.paytomany)

        raw_transaction_menu = tools_menu.addMenu(_("&Load transaction"))
        raw_transaction_menu.addAction(_("&Local file loading"), self.do_process_from_file)
        raw_transaction_menu.addAction(_("&Manual loading"), self.do_process_from_text)
        raw_transaction_menu.addAction(_("&Transaction ID loading"), self.do_process_from_txid)
        # raw_transaction_menu.addAction(_("&From QR code"), self.read_tx_from_qrcode)
        self.raw_transaction_menu = raw_transaction_menu

        help_menu = menubar.addMenu(_("&Help"))
        help_menu.addAction(_("&About"), self.show_about)
        help_menu.addAction(_("&Official website"), lambda: webbrowser.open("http://ulord.one"))
        help_menu.addSeparator()
        # help_menu.addAction(_("&Documentation"), lambda: webbrowser.open("http://docs.ulord.org/")).setShortcut(QKeySequence.HelpContents)
        # help_menu.addAction(_("&Report Bug"), self.show_report_bug)
        help_menu.addSeparator()
        # help_menu.addAction(_("&Donate to server"), self.donate_to_server)
        # menubar.setMaximumWidth(350)
        return menubar
        # self.setMenuBar(menubar)

    def donate_to_server(self):
        d = self.network.get_donation_address()
        if d:
            host = self.network.get_parameters()[0]
            self.pay_to_URI('ulord:%s?message=donation for %s'%(d, host))
        else:
            self.show_error(_('No donation address for this server'))

    def show_about(self):
        title = "UWalletLite V"+  UWallet_VERSION#str(getLocalVersion())[0:5]
        text = _("UWalletLite's focus is speed, with low resource usage and simplifying UT. You do not need to perform regular backups, because your wallet can be recovered from a secret phrase that you can memorize or write on paper. Startup times are instant because it operates in conjunction with high-performance servers that handle the most complicated parts of the ULORD system.")
        icontype = "icon"
        qm = QMessageBoxEx(title,text,self,icontype)
        qm.exec_()


    def show_report_bug(self):
        msg = ' '.join([
            _("Please report any bugs as issues on github:<br/>"),
            "<a href=\"\"></a><br/><br/>",
            _("Before reporting a bug, upgrade to the most recent version of UWalletLite (latest release or git HEAD), and include the version number in your report."),
            _("Try to explain not only what the bug is, but how it occurs.")
         ])
        self.show_message(msg, title="UWalletLite - " + _("Reporting Bugs"))

    def notify_transactions(self):
        if not self.network or not self.network.is_connected():
            return
        self.print_error("Notifying GUI")
        if len(self.tx_notifications) > 0:
            # Combine the transactions if there are more then three
            tx_amount = len(self.tx_notifications)
            if(tx_amount >= 3):
                total_amount = 0
                for tx in self.tx_notifications:
                    is_relevant, is_mine, v, fee = self.wallet.get_wallet_delta(tx)
                    if(v > 0):
                        total_amount += v
                self.notify(_("%(txs)s new transactions received. Total amount received in the new transactions %(amount)s") \
                            % { 'txs' : tx_amount, 'amount' : self.format_amount_and_units(total_amount)})
                self.tx_notifications = []
            else:
              for tx in self.tx_notifications:
                  if tx:
                      self.tx_notifications.remove(tx)
                      is_relevant, is_mine, v, fee = self.wallet.get_wallet_delta(tx)
                      if(v > 0):
                          self.notify(_("New transaction received. %(amount)s") % { 'amount' : self.format_amount_and_units(v)})

    def notify(self, message):
        if self.tray:
            self.tray.showMessage("UWalletLite", message, QSystemTrayIcon.Information, 20000)



    # custom wrappers for getOpenFileName and getSaveFileName, that remember the path selected by the user
    def getOpenFileName(self, title, filter = ""):
        directory = self.config.get('io_dir', unicode(os.path.expanduser('~')))
        fileName = unicode( QFileDialog.getOpenFileName(self, title, directory, filter) )
        if fileName and directory != os.path.dirname(fileName):
            self.config.set_key('io_dir', os.path.dirname(fileName), True)
        return fileName

    def getSaveFileName(self, title, filename, filter = ""):
        directory = self.config.get('io_dir', unicode(os.path.expanduser('~')))
        path = os.path.join( directory, filename )
        fileName = unicode( QFileDialog.getSaveFileName(self, title, path, filter) )
        if fileName and directory != os.path.dirname(fileName):
            self.config.set_key('io_dir', os.path.dirname(fileName), True)
        return fileName

    def connect_slots(self, sender):
        self.connect(sender, QtCore.SIGNAL('timersignal'), self.timer_actions)

    def timer_actions(self):
        # self.warn_version()
        # Note this runs in the GUI thread
        if self.need_update.is_set():
            self.need_update.clear()
            self.update_wallet()
        # resolve aliases
        self.payto_e.resolve()
        # update fee
        if self.require_fee_update:
            self.do_update_fee()
            self.require_fee_update = False

    def format_amount(self, x, is_diff=False, whitespaces=False):
        return format_satoshis(x, is_diff, self.num_zeros, self.decimal_point, whitespaces)

    def format_amount_and_units(self, amount):
        s = self.format_amount(amount)
        slist = s.split('.',1)
        l = slist[1]
        if len(l)<6:
            diff = 6-len(l)
            for i in range(0,diff):
                l +='0'
        text = slist[0]+'.'+l + ' '+ self.base_unit()
        x = run_hook('format_amount_and_units', amount)
        if text and x:
            text += ' (%s)'%x
        return text

    def get_decimal_point(self):
        return self.decimal_point

    def base_unit(self):
        assert self.decimal_point in [2, 5, 8]
        if self.decimal_point == 2:
            return 'bits'
        if self.decimal_point == 5:
            return 'mUT'
        if self.decimal_point == 8:
            return 'UT'
        raise Exception('Unknown base unit')

    def update_status(self):
        if not self.wallet:
            return

        if self.network is None or not self.network.is_running():
            text = _("Offline")
            icon = QIcon(":icons/network_red.png")

        elif self.network.is_connected():
            server_height = self.network.get_server_height()
            server_lag = self.network.get_local_height() - server_height
            # Server height can be 0 after switching to a new server
            # until we get a headers subscription request response.
            # Display the synchronizing message in that case.
            if not self.wallet.up_to_date or server_height == 0:
                text = _("Synchronizing...")
                icon = QIcon(":icons/status_waiting.png")
            elif server_lag > 1:
                text = _("Server is lagging (%d blocks)")%server_lag
                icon = QIcon(":icons/network_yellow.png")
            else:
                c, u, x = self.wallet.get_balance()
                # text =  _("Balance" ) + ": %s "%(self.format_amount_and_units(c))
                tempBalance = self.format_amount_and_units(c)
                tempBArray= tempBalance.split(' ')
                if(tempBArray[0].endswith('.')):
                    tempBalance = tempBArray[0][:-1]
                    tempBalance = tempBalance+ " " + tempBArray[1]
                text = _("Balance") + ": %s " % (tempBalance)
                if u:
                    text +=  _("[%s unconfirmed]")%(self.format_amount(u, True).strip())
                if x:
                    s = (self.format_amount(x, True).strip())
                    text +=  _("[%s unmatured]")%s
                # append fiat balance and price from exchange rate plugin
                rate = run_hook('get_fiat_status_text', c + u + x)
                if rate:
                    text += rate
                icon = QIcon(":icons/network_green.png")
        else:
            text = _("Not connected")
            icon = QIcon(":icons/network_red.png")
        # text = _("Server is lagging (%d blocks)") % 0
        self.tray.setToolTip("%s (%s)" % (text, self.wallet.basename()))
        self.balance_label.setText(text)
        self.status_button.setIcon(icon)
        self.status_button.setStyleSheet("background-color: white;border:0px;")



    def update_wallet(self):
        self.update_status()
        if self.wallet.up_to_date or not self.network or not self.network.is_connected():
            self.update_tabs()

    def update_tabs(self):
        self.history_list.update()
        # self.request_list.update()
        self.address_list.update()
        # self.contact_list.update()
        self.invoice_list.update()
        self.update_completions()

    def create_history_tab(self):
        from history_list import HistoryList
        self.history_list = l = HistoryList(self)

        return l

    def show_address(self, addr):
        import address_dialog
        d = address_dialog.AddressDialog(self, addr)
        d.exec_()

    def show_transaction(self, tx, tx_desc = None):
        '''tx_desc is set only for txs created in the Send tab'''
        show_transaction(tx, self, tx_desc)

    def lock_deposit(self,tx_hash,item,txt):
        self.wallet.set_lock_txoid(tx_hash)
        item.setText(3, txt)

    def create_receive_tab(self):
        # A 4-column grid layout.  All the stretch is in the last column.
        # The exchange rate plugin adds a fiat widget in column 2
        self.receive_grid = grid = QGridLayout()
        grid.setSpacing(8)
        grid.setColumnStretch(3, 1)

        self.receive_address_e = ButtonsLineEdit()
        self.receive_address_e.addCopyButton(self.app)
        self.receive_address_e.setReadOnly(True)
        msg = _('Ulord address where the payment should be received. Note that each payment request uses a different Ulord address.')
        self.receive_address_label = HelpLabel(_('Receiving address'), msg)
        self.receive_address_e.textChanged.connect(self.update_receive_qr)
        self.receive_address_e.setFocusPolicy(Qt.NoFocus)
        grid.addWidget(self.receive_address_label, 0, 0)
        grid.addWidget(self.receive_address_e, 0, 1, 1, -1)

        self.receive_message_e = MyLineEdit()
        grid.addWidget(QLabel(_('Description')), 1, 0)
        grid.addWidget(self.receive_message_e, 1, 1, 1, -1)
        self.receive_message_e.textChanged.connect(self.update_receive_qr)
        # self.receive_message_e.contextMenuEvent.connect(self.receviveMenu)

        self.receive_amount_e = BTCAmountEdit(self.get_decimal_point)
        grid.addWidget(QLabel(_('Requested amount')), 2, 0)
        grid.addWidget(self.receive_amount_e, 2, 1)
        self.receive_amount_e.textChanged.connect(self.update_receive_qr)
        # self.receive_amount_e.editingFinished.connect(self.amount_edited)


        self.expires_combo = QComboBox()
        self.expires_combo.setView(QListView())
        self.expires_combo.addItems(map(lambda x:x[0], self.expiration_values))
        self.expires_combo.setCurrentIndex(1)
        self.expires_combo.setFixedWidth(self.receive_amount_e.width())
        msg = ' '.join([
            _('Expiration date of your request.'),
            _('This information is seen by the recipient if you send them a signed payment request.'),
            _('Expired requests have to be deleted manually from your list, in order to free the corresponding Ulord addresses.'),
            _('The bitcoin address never expires and will always be part of this ulord wallet.'),
        ])
        # grid.addWidget(HelpLabel(_('Request expires'), msg), 3, 0)
        grid.addWidget(self.expires_combo, 3, 1)
        self.expires_label = QLineEditEx('')
        self.expires_label.setReadOnly(1)
        self.expires_label.setFocusPolicy(Qt.NoFocus)
        self.expires_label.hide()
        grid.addWidget(self.expires_label, 3, 1)
        self.expires_combo.setHidden(True)
        # self.save_request_button = QPushButton(_('Save'))
        # self.save_request_button.clicked.connect(self.save_payment_request)
        #
        # self.new_request_button = QPushButton(_('New'))
        # self.new_request_button.clicked.connect(self.new_payment_request)

        self.receive_qr = QRCodeWidget(fixedSize=200)
        self.receive_qr.mouseReleaseEvent = lambda x: self.toggle_qr_window()
        self.receive_qr.enterEvent = lambda x: self.app.setOverrideCursor(QCursor(Qt.PointingHandCursor))
        self.receive_qr.leaveEvent = lambda x: self.app.setOverrideCursor(QCursor(Qt.ArrowCursor))

        self.receive_buttons = buttons = QHBoxLayout()
        buttons.addStretch(1)
        # buttons.addWidget(self.save_request_button)
        # buttons.addWidget(self.new_request_button)
        grid.addLayout(buttons, 4, 1, 1, 2)

        # self.receive_requests_label = QLabel(_('Requests'))

        # from request_list import RequestList
        # self.request_list = RequestList(self)
        # self.request_list.setSortingEnabled(False)
        # layout
        vbox_g = QVBoxLayout()
        vbox_g.addLayout(grid)
        vbox_g.addStretch()

        hbox = QHBoxLayout()
        hbox.addLayout(vbox_g)
        hbox.addWidget(self.receive_qr)

        w = QWidget()
        vbox = QVBoxLayout(w)
        vbox.addLayout(hbox)
        vbox.addStretch(1)
        # vbox.addWidget(self.receive_requests_label)
        # vbox.addWidget(self.request_list)
        # vbox.setStretchFactor(self.request_list, 1000)
        return w


    def delete_payment_request(self, item):
        addr = str(item.text(1))
        self.wallet.remove_payment_request(addr, self.config)
        # self.request_list.update()
        self.clear_receive_tab()

    def get_request_URI(self, addr):
        req = self.wallet.receive_requests[addr]
        message = self.wallet.labels.get(addr, '')
        amount = req['amount']
        URI = util.create_URI(addr, amount, message)
        if req.get('time'):
            URI += "&time=%d"%req.get('time')
        if req.get('exp'):
            URI += "&exp=%d"%req.get('exp')
        if req.get('name') and req.get('sig'):
            sig = req.get('sig').decode('hex')
            sig = bitcoin.base_encode(sig, base=58)
            URI += "&name=" + req['name'] + "&sig="+sig
        return str(URI)


    def sign_payment_request(self, addr):
        alias = self.config.get('alias')
        alias_privkey = None
        if alias and self.alias_info:
            alias_addr, alias_name, validated = self.alias_info
            if alias_addr:
                if self.wallet.is_mine(alias_addr):
                    msg = _('This payment request will be signed.') + '\n' + _('Please enter your password')
                    password = self.password_dialog(msg)
                    if password:
                        try:
                            self.wallet.sign_payment_request(addr, alias, alias_addr, password)
                        except Exception as e:
                            self.show_error(str(e))
                            return
                    else:
                        return
                else:
                    return


    def save_payment_request(self):
        addr = str(self.receive_address_e.text())
        amount = self.receive_amount_e.get_amount()
        message = unicode(self.receive_message_e.text())
        if not message and not amount:
            self.show_error(_('No message or amount'))
            return False
        i = self.expires_combo.currentIndex()
        # expiration = map(lambda x: x[1], self.expiration_values)[i]
        expiration = map(lambda x: x[1], self.expiration_values)[3]
        req = self.wallet.make_payment_request(addr, amount, message, expiration)
        self.wallet.add_payment_request(req, self.config)
        self.sign_payment_request(addr)
        # self.request_list.update()
        self.address_list.update()
        # self.save_request_button.setEnabled(False)

    def view_and_paste(self, title, msg, data):
        dialog = WindowModalDialog(self, title)
        vbox = QVBoxLayout()
        dialog.setTitleBar(vbox)
        label = QLabel(msg)
        label.setWordWrap(True)
        vbox.addWidget(label)
        pr_e = ShowQRTextEdit(text=data)
        vbox.addWidget(pr_e)
        vbox.addLayout(Buttons(CopyCloseButton(pr_e.text, self.app, dialog)))
        dialog.setLayout(vbox)
        dialog.exec_()

    def export_payment_request(self, addr):
        r = self.wallet.receive_requests.get(addr)
        pr = paymentrequest.serialize_request(r).SerializeToString()
        name = r['id'] + '.bip70'
        fileName = self.getSaveFileName(_("Select where to save your payment request"), name, "*.bip70")
        if fileName:
            with open(fileName, "wb+") as f:
                f.write(str(pr))
            self.show_message(_("Request saved successfully"))
            self.saved = True

    def new_payment_request(self):
        addr = self.wallet.get_unused_address()
        if addr is None:
            from uwallet.wallet import Imported_Wallet
            if not self.wallet.is_deterministic():
                msg = [
                    _('No more addresses in your wallet.'),
                    _('You are using a non-deterministic wallet, which cannot create new addresses.'),
                    _('If you want to create new addresses, use a deterministic wallet instead.')
                   ]
                self.show_message(' '.join(msg))
                return
            if not self.question(_("Warning: The next address will not be recovered automatically if you restore your wallet from seed; you may need to add it manually.\n\nThis occurs because you have too many unused addresses in your wallet. To avoid this situation, use the existing addresses first.\n\nCreate anyway?")):
                return
            addr = self.wallet.create_new_address(False)
        self.set_receive_address()
        self.expires_label.hide()
        # self.expires_combo.show()
        # self.new_request_button.setEnabled(False)
        self.receive_message_e.setFocus(1)

    def set_receive_address(self,addr=''):
        self.receive_address_e.setText(self.wallet.get_receiving_addresses()[0])
        self.receive_message_e.setText('')
        self.receive_amount_e.setAmount(None)

    def clear_receive_tab(self):
        addr = self.wallet.get_unused_address()
        self.receive_address_e.setText(addr if addr else '')
        self.receive_message_e.setText('')
        self.receive_amount_e.setAmount(None)
        self.expires_label.hide()
        # self.expires_combo.show()

    def toggle_qr_window(self):
        import qrwindow
        if not self.qr_window:
            # self.qr_window = qrwindow.QR_Window(self)
            # self.qr_window.setVisible(True)
            # self.qr_window_geometry = self.qr_window.geometry()
            a = 1
        else:
            if not self.qr_window.isVisible():
                self.qr_window.setVisible(True)
                self.qr_window.setGeometry(self.qr_window_geometry)
            else:
                self.qr_window_geometry = self.qr_window.geometry()
                self.qr_window.setVisible(False)
        self.update_receive_qr()


    def receive_at(self, addr):
        if not bitcoin.is_address(addr):
            return
        self.tabs.setCurrentIndex(2)
        self.receive_address_e.setText(addr)
        # self.new_request_button.setEnabled(True)

    # def amount_edited(self):
    #     tamount = self.receive_amount_e.text()
    #     if float(tamount)==0:
    #         title = "UWalletLite"
    #         text = _("amount can not be 0")
    #         icontype = "warm"
    #         qm = QMessageBoxEx(title, text, self, icontype)
    #         qm.exec_()
            # self.receive_amount_e.setFocus()


    def update_receive_qr(self):
        addr = str(self.receive_address_e.text())
        amount = self.receive_amount_e.get_amount()
        message = unicode(self.receive_message_e.text()).encode('utf8')
        # self.save_request_button.setEnabled((amount is not None) or (message != ""))
        uri = util.create_URI(addr, amount, message)
        self.receive_qr.setData(uri)
        if self.qr_window and self.qr_window.isVisible():
            self.qr_window.set_content(addr, amount, message, uri)

    def create_send_tab(self):
        # A 4-column grid layout.  All the stretch is in the last column.
        # The exchange rate plugin adds a fiat widget in column 2
        self.send_grid = grid = QGridLayout()
        grid.setSpacing(8)
        grid.setColumnStretch(3, 1)

        from paytoedit import PayToEdit
        self.amount_e = BTCAmountEdit(self.get_decimal_point)
        self.payto_e = PayToEdit(self)
        msg = _('Recipient of the funds.') + '\n\n'\
              + _('You may enter a Ulord address, a label from your list of contacts (a list of completions will be proposed), or an alias (email-like address that forwards to a Ulord address)')
        payto_label = HelpLabel(_('Pay to'), msg)
        grid.addWidget(payto_label, 1, 0)
        grid.addWidget(self.payto_e, 1, 1, 1, -1)

        completer = QCompleter()
        completer.setCaseSensitivity(False)
        self.payto_e.setCompleter(completer)
        completer.setModel(self.completions)

        msg = _('Description of the transaction (not mandatory).') + '\n\n'\
              + _('The description is not sent to the recipient of the funds. It is stored in your wallet file, and displayed in the \'History\' tab.')
        description_label = HelpLabel(_('Description'), msg)
        grid.addWidget(description_label, 2, 0)
        self.message_e = MyLineEdit()
        grid.addWidget(self.message_e, 2, 1, 1, -1)

        self.from_label = QLabel(_('From'))
        grid.addWidget(self.from_label, 3, 0)
        self.from_list = MyTreeWidget(self, self.from_list_menu, ['',''])
        self.from_list.setHeaderHidden(True)
        self.from_list.setMaximumHeight(80)
        grid.addWidget(self.from_list, 3, 1, 1, -1)
        self.set_pay_from([])

        msg = _('Amount to be sent.') + '\n\n' \
              + _('The amount will be displayed in red if you do not have enough funds in your wallet.') + ' ' \
              + _('Note that if you have frozen some of your addresses, the available funds will be lower than your total balance.') + '\n\n' \
              + _('Keyboard shortcut: type "!" to send all your coins.')
        amount_label = HelpLabel(_('Amount'), msg)
        grid.addWidget(amount_label, 4, 0)
        grid.addWidget(self.amount_e, 4, 1)

        self.max_button = EnterButton(_("Max"), self.spend_max)
        hbox = QHBoxLayout()
        hbox.addWidget(self.max_button)
        hbox.addStretch(1)
        grid.addLayout(hbox, 4, 3)

        msg = _('Bitcoin transactions are in general not free. A transaction fee is paid by the sender of the funds.') + '\n\n'\
              + _('The amount of fee can be decided freely by the sender. However, transactions with low fees take more time to be processed.') + '\n\n'\
              + _('A suggested fee is automatically added to this field. You may override it. The suggested fee increases with the size of the transaction.')
        self.fee_e_label = HelpLabel(_('Fee'), msg)

        self.fee_slider = QSlider(Qt.Horizontal, self)
        self.fee_slider.setRange(0, 4)
        self.fee_slider.setToolTip('')
        def slider_moved():
            from uwallet.util import fee_levels
            i = self.fee_slider.sliderPosition()
            tooltip = self.fee_level[i]
            if self.network:
                dynfee = self.network.dynfee(i)
                if dynfee:
                    tooltip += '\n' + self.format_amount(dynfee) + ' ' + self.base_unit() + '/kB'
            QToolTip.showText(QCursor.pos(), tooltip, self.fee_slider)
        def slider_released():
            self.config.set_key('fee_level', self.fee_slider.sliderPosition(), False)
            if self.is_max:
                self.spend_max()
            else:
                self.update_fee()
        self.fee_slider.valueChanged.connect(slider_moved)
        self.fee_slider.sliderReleased.connect(slider_released)
        self.fee_slider.setValue(self.config.get('fee_level', 2)) #default not use dydynamic_fees

        self.fee_e = BTCAmountEdit(self.get_decimal_point)
        self.fee_e.textEdited.connect(self.update_fee)
        # This is so that when the user blanks the fee and moves on,
        # we go back to auto-calculate mode and put a fee back.
        self.fee_e.editingFinished.connect(self.update_fee)

        self.rbf_checkbox = QCheckBox(_('Replaceable'))
        msg = [_('If you check this box, your transaction will be marked as non-final,'),
               _('and you will have the possiblity, while it is unconfirmed, to replace it with a transaction that pays a higher fee.'),
               _('Note that some merchants do not accept non-final transactions until they are confirmed.')]
        self.rbf_checkbox.setToolTip('<p>' + ' '.join(msg) + '</p>')
        self.rbf_checkbox.setVisible(self.config.get('use_rbf', False))

        grid.addWidget(self.fee_e_label, 5, 0)
        grid.addWidget(self.fee_e, 5, 1)
        grid.addWidget(self.fee_slider, 5, 1)
        grid.addWidget(self.rbf_checkbox, 5, 2)

        self.preview_button = EnterButton(_("Preview"), self.do_preview)
        self.preview_button.setToolTip(_('Display the details of your transactions before signing it.'))
        self.send_button = EnterButton(_("Send"), self.do_send)
        self.clear_button = EnterButton(_("Clear"), self.do_clear)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.clear_button)
        buttons.addWidget(self.preview_button)
        buttons.addWidget(self.send_button)
        grid.addLayout(buttons, 6, 1, 1, 2)

        self.amount_e.shortcut.connect(self.spend_max)
        self.payto_e.textChanged.connect(self.update_fee)
        self.amount_e.textEdited.connect(self.update_fee)
        self.amount_e.textEdited.connect(self.reset_max)

        def entry_changed():
            text = ""
            if self.not_enough_funds:
                amt_color, fee_color = RED_FG, RED_FG
                text = _( "Not enough funds" )
                c, u, x = self.wallet.get_frozen_balance()
                if c+u+x:
                    text += ' (' + self.format_amount(c+u+x).strip() + ' ' + self.base_unit() + ' ' +_("are frozen") + ')'

            elif self.fee_e.isModified():
                amt_color, fee_color = BLACK_FG, BLACK_FG
            elif self.amount_e.isModified():
                amt_color, fee_color = BLACK_FG, BLUE_FG
            else:
                amt_color, fee_color = BLUE_FG, BLUE_FG

            self.sb.showMessage(text)
            self.amount_e.setStyleSheet(amt_color)
            self.fee_e.setStyleSheet(fee_color)

        self.amount_e.textChanged.connect(entry_changed)
        self.fee_e.textChanged.connect(entry_changed)

        self.invoices_label = QLabel(_('Invoices'))
        from invoice_list import InvoiceList
        self.invoice_list = InvoiceList(self)

        vbox0 = QVBoxLayout()
        vbox0.addLayout(grid)
        hbox = QHBoxLayout()
        hbox.addLayout(vbox0)
        w = QWidget()
        vbox = QVBoxLayout(w)
        vbox.addLayout(hbox)
        vbox.addStretch(1)
        vbox.addWidget(self.invoices_label)
        vbox.addWidget(self.invoice_list)
        vbox.setStretchFactor(self.invoice_list, 1000)

        # Defer this until grid is parented to avoid ugly flash during startup
        self.update_fee_edit()

        run_hook('create_send_tab', grid)
        return w


    def spend_max(self):
        inputs = self.get_coins()
        sendable = sum(map(lambda x:x['value'], inputs))
        fee = self.fee_e.get_amount() if self.fee_e.isModified() else None
        r = self.get_payto_or_dummy()
        amount, fee = self.wallet.get_max_amount(self.config, inputs, r, fee)
        if not self.fee_e.isModified():
            self.fee_e.setAmount(fee)
        self.amount_e.setAmount(amount)
        self.not_enough_funds = (fee + amount > sendable)
        # emit signal for fiat_amount update
        self.amount_e.textEdited.emit("")
        self.is_max = True

    def reset_max(self):
        self.is_max = False

    def update_fee(self):
        self.require_fee_update = True

    def get_payto_or_dummy(self):
        r = self.payto_e.get_recipient()
        if r:
            return r
        return (TYPE_ADDRESS, self.wallet.dummy_address())

    def do_update_fee(self):
        '''Recalculate the fee.  If the fee was manually input, retain it, but
        still build the TX to see if there are enough funds.
        '''
        freeze_fee = (self.fee_e.isModified()
                      and (self.fee_e.text() or self.fee_e.hasFocus()))
        amount = self.amount_e.get_amount()
        if amount is None:
            if not freeze_fee:
                self.fee_e.setAmount(None)
            self.not_enough_funds = False
        else:
            fee = self.fee_e.get_amount() if freeze_fee else None
            outputs = self.payto_e.get_outputs()
            if not outputs:
                _type, addr = self.get_payto_or_dummy()
                outputs = [(_type, addr, amount)]
            try:
                tx = self.wallet.make_unsigned_transaction(self.get_coins(), outputs, self.config, fee)
                self.not_enough_funds = False
            except NotEnoughFunds:
                self.not_enough_funds = True
            if not freeze_fee:
                fee = None if self.not_enough_funds else self.wallet.get_tx_fee(tx)
                self.fee_e.setAmount(fee)

    def update_fee_edit(self):
        b = self.config.get('dynamic_fees', False)
        self.fee_slider.setVisible(b)
        self.fee_e.setVisible(not b)

    def from_list_delete(self, item):
        i = self.from_list.indexOfTopLevelItem(item)
        self.pay_from.pop(i)
        self.redraw_from_list()
        self.update_fee()

    def from_list_menu(self, position):
        item = self.from_list.itemAt(position)
        menu = QMenu()
        menu.addAction(_("Remove"), lambda: self.from_list_delete(item))
        menu.exec_(self.from_list.viewport().mapToGlobal(position))

    def set_pay_from(self, domain = None):
        self.pay_from = [] if domain == [] else self.wallet.get_spendable_coins(domain)
        self.redraw_from_list()

    def redraw_from_list(self):
        self.from_list.clear()
        self.from_label.setHidden(len(self.pay_from) == 0)
        self.from_list.setHidden(len(self.pay_from) == 0)

        def format(x):
            h = x.get('prevout_hash')
            return h[0:8] + '...' + h[-8:] + ":%d"%x.get('prevout_n') + u'\t' + "%s"%x.get('address')

        for item in self.pay_from:
            self.from_list.addTopLevelItem(QTreeWidgetItem( [format(item), self.format_amount(item['value']) ]))

    def get_contact_payto(self, key):
        _type, label = self.contacts.get(key)
        return label + '  <' + key + '>' if _type == 'address' else key

    def update_completions(self):
        l = [self.get_contact_payto(key) for key in self.contacts.keys()]
        self.completions.setStringList(l)

    def protected(func):
        '''Password request wrapper.  The password is passed to the function
        as the 'password' named argument.  "None" indicates either an
        unencrypted wallet, or the user cancelled the password request.
        An empty input is passed as the empty string.'''
        def request_password(self, *args, **kwargs):
            parent = self.top_level_window()
            password = None
            while self.wallet.has_password():
                password = self.password_dialog(parent=parent)
                try:
                    if password:
                        self.wallet.check_password(password)
                    break
                except Exception as e:
                    title = "UWalletLite"
                    text = _("Incorrect password")
                    icontype = "warm"
                    qm = QMessageBoxEx(title, text, self, icontype)
                    qm.exec_()
                    self.show_error(str(e), parent=parent)
                    continue

            kwargs['password'] = password
            return func(self, *args, **kwargs)
        return request_password

    def read_send_tab(self):
        if self.payment_request and self.payment_request.has_expired():
            self.show_error(_('Payment request has expired'))
            return
        label = unicode( self.message_e.text() )

        if self.payment_request:
            outputs = self.payment_request.get_outputs()
        else:
            errors = self.payto_e.get_errors()
            if errors:
                self.show_warning(_("Invalid Lines found:"))# + "\n\n" + '\n'.join([ _("Line #") + str(x[0]+1) + ": " + x[1] for x in errors])
                return
            outputs = self.payto_e.get_outputs()

            if self.payto_e.is_alias and self.payto_e.validated is False:
                alias = self.payto_e.toPlainText()
                msg = _('WARNING: the alias "%s" could not be validated via an additional security check, DNSSEC, and thus may not be correct.'%alias) + '\n'
                msg += _('Do you wish to continue?')
                if not self.question(msg):
                    return

        if not outputs:
            self.show_error(_('No outputs'))
            return

        for _type, addr, amount in outputs:
            if addr is None:
                self.show_error(_('Ulord Address is None'))
                return
            if _type == TYPE_ADDRESS and not bitcoin.is_address(addr):
                self.show_error(_('Invalid Ulord Address'))
                return
            if amount is None:
                self.show_error(_('Invalid Amount'))
                return
            if amount is 0:
                self.show_error(_('Invalid 0 Amount'))
                return
        fee = self.fee_e.get_amount()
        if fee is None:
            self.show_error(_('Invalid Fee'))
            return
        if fee is 0:
            self.show_error(_('Invalid 0 Fee'))
            return
        coins = self.get_coins()
        return outputs, fee, label, coins

    def do_preview(self):
        self.do_send(preview = True)

    def do_send(self, preview = False):
        if not self.network.is_connected():
            self.show_message(_("connetion is abort."))
            return
        if run_hook('abort_send', self):
            return
        r = self.read_send_tab()
        if not r:
            return
        outputs, fee, tx_desc, coins = r
        amount = sum(map(lambda x:x[2], outputs))
        try:
            tx = self.wallet.make_unsigned_transaction(coins, outputs, self.config, fee)
        except NotEnoughFunds:
            self.show_message(_("Insufficient funds"))
            return
        except BaseException as e:
            traceback.print_exc(file=sys.stdout)
            self.show_message(str(e))
            return

        use_rbf = self.rbf_checkbox.isChecked()
        if use_rbf:
            tx.set_sequence(0)

        if tx.get_fee() < self.wallet.relayfee() * tx.estimated_size() / 1000 and tx.requires_fee(self.wallet):
            self.show_error(_("This transaction requires a higher fee, or it will not be propagated by the network"))
            return

        if preview:
            self.show_transaction(tx, tx_desc)
            return

        # confirmation dialog
        confirm_amount = self.config.get('confirm_amount', COIN)
        msg = [
            _("Amount to be sent") + ": " + self.format_amount_and_units(amount),
            _("Mining fee") + ": " + self.format_amount_and_units(fee),
        ]

        extra_fee = run_hook('get_additional_fee', self.wallet, tx)
        if extra_fee:
            msg.append( _("Additional fees") + ": " + self.format_amount_and_units(extra_fee) )

        if tx.get_fee() >= self.config.get('confirm_fee', 100000):
            msg.append(_('Warning')+ ': ' + _("The fee for this transaction seems unusually high."))

        if self.wallet.has_password():
            msg.append("")
            msg.append(_("Enter your password to proceed"))
            password = self.password_dialog('\n'.join(msg))
            if not password:
                return
        else:
            msg.append(_('Proceed?'))
            password = None
            if not self.question('\n'.join(msg)):
                return

        def sign_done(success):
            if success:
                if not tx.is_complete():
                    self.show_transaction(tx)
                    self.do_clear()
                else:
                    self.broadcast_transaction(tx, tx_desc)
        self.sign_tx_with_password(tx, sign_done, password)

    @protected
    def sign_tx(self, tx, callback, password):
        self.sign_tx_with_password(tx, callback, password)

    def sign_tx_with_password(self, tx, callback, password):
        '''Sign the transaction in a separate thread.  When done, calls
        the callback with a success code of True or False.
        '''
        if self.wallet.has_password() and not password:
            callback(False) # User cancelled password input
            return

        # call hook to see if plugin needs gui interaction
        run_hook('sign_tx', self, tx)

        def on_signed(result):
            callback(True)
        def on_failed(exc_info):
            self.on_error(exc_info)
            callback(False)

        task = partial(self.wallet.sign_transaction, tx, password)
        WaitingDialog(self, _('Signing transaction...'), task,
                      on_signed, on_failed)

    def broadcast_transaction(self, tx, tx_desc):

        def broadcast_thread():
            # non-GUI thread
            pr = self.payment_request
            if pr and pr.has_expired():
                self.payment_request = None
                return False, _("Payment request has expired")
            status, msg =  self.network.broadcast(tx)
            if pr and status is True:
                pr.set_paid(tx.hash())
                self.invoices.save()
                self.payment_request = None
                refund_address = self.wallet.get_receiving_addresses()[0]
                ack_status, ack_msg = pr.send_ack(str(tx), refund_address)
                if ack_status:
                    msg = ack_msg
            return status, msg

        # Capture current TL window; override might be removed on return
        parent = self.top_level_window()

        def broadcast_done(result):
            # GUI thread
            if result:
                status, msg = result
                if status:
                    if tx_desc is not None and tx.is_complete():
                        self.wallet.set_label(tx.hash(), tx_desc)
                    parent.show_message(_('Payment sent.') + '\n' + msg)
                    self.invoice_list.update()
                    self.do_clear()
                else:
                    if 'tx-size' in msg:
                        parent.show_error(_('Transaction size is too large.'))
                    else:
                        parent.show_error(msg)

        WaitingDialog(self, _('Broadcasting transaction...'),
                      broadcast_thread, broadcast_done, self.on_error)

    def query_choice(self, msg, choices):
        # Needed by QtHandler for hardware wallets
        dialog = WindowModalDialog(self.top_level_window())
        clayout = ChoicesLayout(msg, choices)
        vbox = QVBoxLayout(dialog)
        dialog.setTitleBar(vbox)
        vbox.addLayout(clayout.layout())
        vbox.addLayout(Buttons(OkButton(dialog)))
        if not dialog.exec_():
            return None
        return clayout.selected_index()

    def lock_amount(self, b):
        self.amount_e.setFrozen(b)
        self.max_button.setEnabled(not b)

    def prepare_for_payment_request(self):
        self.tabs.setCurrentIndex(1)
        self.payto_e.is_pr = True
        for e in [self.payto_e, self.amount_e, self.message_e]:
            e.setFrozen(True)
        self.payto_e.setText(_("please wait..."))
        return True

    def delete_invoice(self, key):
        self.invoices.remove(key)
        self.invoice_list.update()

    def payment_request_ok(self):
        pr = self.payment_request
        key = self.invoices.add(pr)
        status = self.invoices.get_status(key)
        self.invoice_list.update()
        if status == PR_PAID:
            self.show_message("invoice already paid")
            self.do_clear()
            self.payment_request = None
            return
        self.payto_e.is_pr = True
        if not pr.has_expired():
            self.payto_e.setGreen()
        else:
            self.payto_e.setExpired()
        self.payto_e.setText(pr.get_requestor())
        self.amount_e.setText(format_satoshis_plain(pr.get_amount(), self.decimal_point))
        self.message_e.setText(pr.get_memo())
        # signal to set fee
        self.amount_e.textEdited.emit("")

    def payment_request_error(self):
        self.show_message(self.payment_request.error)
        self.payment_request = None
        self.do_clear()

    def on_pr(self, request):
        self.payment_request = request
        if self.payment_request.verify(self.contacts):
            self.emit(SIGNAL('payment_request_ok'))
        else:
            self.emit(SIGNAL('payment_request_error'))

    def pay_to_URI(self, URI):
        if not URI:
            return
        try:
            out = util.parse_URI(unicode(URI), self.on_pr)
        except BaseException as e:
            self.show_error(_('Invalid bitcoin URI:') + '\n' + str(e))
            return
        self.tabs.setCurrentIndex(1)
        r = out.get('r')
        sig = out.get('sig')
        name = out.get('name')
        if r or (name and sig):
            self.prepare_for_payment_request()
            return
        address = out.get('address')
        amount = out.get('amount')
        label = out.get('label')
        message = out.get('message')
        # use label as description (not BIP21 compliant)
        if label and not message:
            message = label
        if address:
            self.payto_e.setText(address)
        if message:
            self.message_e.setText(message)
        if amount:
            self.amount_e.setAmount(amount)
            self.amount_e.textEdited.emit("")


    def do_clear(self):
        self.is_max = False
        self.not_enough_funds = False
        self.payment_request = None
        self.payto_e.is_pr = False
        for e in [self.payto_e, self.message_e, self.amount_e, self.fee_e]:
            e.setText('')
            e.setFrozen(False)
        self.set_pay_from([])
        self.rbf_checkbox.setChecked(False)
        self.update_status()
        run_hook('do_clear', self)

    def set_frozen_state(self, addrs, freeze):
        self.wallet.set_frozen_state(addrs, freeze)
        self.address_list.update()
        self.update_fee()

    def create_list_tab(self, l):
        w = QWidget()
        vbox = QVBoxLayout()
        w.setLayout(vbox)
        vbox.setMargin(0)
        vbox.setSpacing(0)
        vbox.addWidget(l)
        buttons = QWidget()
        vbox.addWidget(buttons)
        return w

    def create_addresses_tab(self):
        from address_list import AddressList
        self.address_list = l = AddressList(self)
        return self.create_list_tab(l)

    def create_contacts_tab(self):
        from contact_list import ContactList
        self.contact_list = l = ContactList(self)
        return self.create_list_tab(l)

    def remove_address(self, addr):
        if self.question(_("Do you want to remove")+" %s "%addr +_("from your wallet?")):
            self.wallet.delete_address(addr)
            self.address_list.update()
            self.history_list.update()

    def edit_account_label(self, k):
        text, ok = QInPutDialogEx.getText(self, _('Rename account'), _('Name') + ':', text = self.wallet.labels.get(k,''))
        if ok:
            label = unicode(text)
            self.wallet.set_label(k,label)
            self.address_list.update()

    def get_coins(self):
        if self.pay_from:
            return self.pay_from
        else:
            domain = self.wallet.get_addresses()
            return self.wallet.get_spendable_coins(domain,True,self.wallet.lock_txoids)


    def send_from_addresses(self, addrs):
        self.set_pay_from(addrs)
        self.tabs.setCurrentIndex(1)
        self.update_fee()

    def paytomany(self):
        self.tabs.setCurrentIndex(1)
        self.payto_e.paytomany()
        msg = '\n'.join([
            _('Enter a list of outputs in the \'Pay to\' field.'),
            _('One output per line.'),
            _('Format: address, amount'),
            _('You may load a CSV file using the file icon.')
        ])
        self.show_message(msg, title=_('Pay to many'))

    def payto_contacts(self, labels):
        paytos = [self.get_contact_payto(label) for label in labels]
        self.tabs.setCurrentIndex(1)
        if len(paytos) == 1:
            self.payto_e.setText(paytos[0])
            self.amount_e.setFocus()
        else:
            text = "\n".join([payto + ", 0" for payto in paytos])
            self.payto_e.setText(text)
            self.payto_e.setFocus()

    def set_contact(self, label, address):
        if not is_valid(address):
            self.show_error(_('Invalid Address'))
            self.contact_list.update()  # Displays original unchanged value
            return False
        self.contacts[address] = ('address', label)
        self.contact_list.update()
        self.history_list.update()
        self.update_completions()
        return True

    def delete_contacts(self, labels):
        try:
            if not self.question(_("Remove from your list of contacts?")):
                return
            for label in labels:
                self.contacts.pop(label)
            self.history_list.update()
            self.contact_list.update()
            self.update_completions()
        except Exception,ex:
            print ex


    def show_invoice(self, key):
        pr = self.invoices.get(key)
        pr.verify(self.contacts)
        self.show_pr_details(pr)

    def show_pr_details(self, pr):
        d = WindowModalDialog(self, _("Invoice"))
        vbox = QVBoxLayout(d)
        d.setTitleBar(vbox)
        grid = QGridLayout()
        grid.addWidget(QLabel(_("Requestor") + ':'), 0, 0)
        grid.addWidget(QLabel(pr.get_requestor()), 0, 1)
        grid.addWidget(QLabel(_("Expires") + ':'), 1, 0)
        grid.addWidget(QLabel(format_time(pr.get_expiration_date())), 1, 1)
        grid.addWidget(QLabel(_("Memo") + ':'), 2, 0)
        grid.addWidget(QLabel(pr.get_memo()), 2, 1)
        grid.addWidget(QLabel(_("Signature") + ':'), 3, 0)
        grid.addWidget(QLabel(pr.get_verify_status()), 3, 1)
        grid.addWidget(QLabel(_("Payment URL") + ':'), 4, 0)
        grid.addWidget(QLabel(pr.payment_url), 4, 1)
        grid.addWidget(QLabel(_("Outputs") + ':'), 5, 0)
        outputs_str = '\n'.join(map(lambda x: x[1] + ' ' + self.format_amount(x[2])+ self.base_unit(), pr.get_outputs()))
        grid.addWidget(QLabel(outputs_str), 5, 1)
        if pr.tx:
            grid.addWidget(QLabel(_("Transaction ID") + ':'), 6, 0)
            l = QLineEditEx(pr.tx)
            l.setReadOnly(True)
            grid.addWidget(l, 6, 1)
        vbox.addLayout(grid)
        vbox.addLayout(Buttons(CloseButton(d)))
        d.exec_()
        return


    def do_pay_invoice(self, key):
        pr = self.invoices.get(key)
        self.payment_request = pr
        self.prepare_for_payment_request()
        if pr.verify(self.contacts):
            self.payment_request_ok()
        else:
            self.payment_request_error()

    # def create_console_tab(self):
    #     from console import Console
    #     self.console = console = Console()
    #     return console
    #
    #
    # def update_console(self):
    #     console = self.console
    #     console.history = self.config.get("console-history",[])
    #     console.history_index = len(console.history)
    #
    #     console.updateNamespace({'wallet' : self.wallet,
    #                              'network' : self.network,
    #                              'plugins' : self.gui_object.plugins,
    #                              'window': self})
    #     console.updateNamespace({'util' : util, 'bitcoin':bitcoin})
    #
    #     c = commands.Commands(self.config, self.wallet, self.network, lambda: self.console.set_json(True))
    #     methods = {}
    #     def mkfunc(f, method):
    #         return lambda *args: apply( f, (method, args, self.password_dialog ))
    #     for m in dir(c):
    #         if m[0]=='_' or m in ['network','wallet']: continue
    #         methods[m] = mkfunc(c._run, m)
    #
    #     console.updateNamespace(methods)



    def create_status_bar(self):

        sb = QStatusBar()
        sb.setFixedHeight(30)
        sb.setSizeGripEnabled(False)
        sb.setStyleSheet(QString("QStatusBar::item{border: 0px}QStatusBar{border:0px;}"));
        self.balance_label = QLabel("")
        self.balance_label.setObjectName("balance_label")
        sb.addWidget(self.balance_label)
        sb.setStyleSheet("background-color:white;")
        # self.search_box = QLineEdit()
        # self.search_box.textChanged.connect(self.do_search)
        # self.search_box.hide()
        # sb.addPermanentWidget(self.search_box)

        self.lock_icon = QIcon()
        self.password_button = StatusBarButton(self.lock_icon, _("Password"), self.change_password_dialog )
        self.password_button.setObjectName("password_button")
        sb.addPermanentWidget(self.password_button)
        self.password_button.setStyleSheet("border:0px;")

        self.setting_button = StatusBarButton(QIcon(""), _("Preferences"), self.settings_dialog)#:icons/ic_settings_pre.png
        self.setting_button.setObjectName("setting_button")
        sb.addPermanentWidget(self.setting_button)
        self.setting_button.setStyleSheet("QPushButton{background-color: white;border:0px;image: url(:icons/ic_settings.png)center no-repeat;}QPushButton:hover{image: url(:icons/ic_settings_pre.png) center no-repeat;}")


        self.seed_button = StatusBarButton(QIcon(""), _("Seed"), self.show_seed_dialog)#:icons/ic_spa_pre.png
        self.seed_button.setObjectName("seed_button")
        sb.addPermanentWidget(self.seed_button)
        self.seed_button.setStyleSheet("QPushButton{background-color: white;border:0px;image: url(:icons/ic_spa.png) center no-repeat;}QPushButton:hover{image: url(:icons/ic_spa_pre.png) center no-repeat;}")


        self.status_button = StatusBarButton(QIcon(":icons/network_red.png"), _("Network"), self.run_network_dialog)
        sb.addPermanentWidget(self.status_button)
        self.status_button.setObjectName("status_button")
        self.status_button.setStyleSheet("border:0px;")

        run_hook('create_status_bar', sb)
        # self.setStatusBar(sb)
        return sb

    def update_lock_icon(self):
        if self.wallet.has_password():
            self.password_button.setStyleSheet(
                "QPushButton{background-color: white;border:0px;image: url(:icons/ic_lock_colse.png)center no-repeat;}QPushButton:hover{image: url(:icons/ic_lock_colse_pre.png) center no-repeat;}")

        else:
            self.password_button.setStyleSheet(
                "QPushButton{background-color: white;border:0px;image: url(:icons/ic_lock_open.png)center no-repeat;}QPushButton:hover{image: url(:icons/ic_lock_open_pre.png) center no-repeat;}")

    def update_buttons_on_seed(self):
        self.seed_button.setVisible(self.wallet.has_seed())
        self.password_button.setVisible(self.wallet.can_change_password())
        self.send_button.setVisible(not self.wallet.is_watching_only())

    def change_password_dialog(self):
        from password_dialog import PasswordDialog, PW_CHANGE

        msg = (_("The current wallet is encrypted. To cancel the password, set the new password to empty.") if self.wallet.has_password()
               else _('Your wallet keys are not encrypted'))
        d = PasswordDialog(self, self.wallet, msg, PW_CHANGE)
        ok, password, new_password = d.run()
        if not ok or (password==None and self.wallet.has_password()):
            return

        try:
            # if(password==""or password==None):
            #     return
            self.wallet.update_password(password, new_password)
        except BaseException as e:
            title = "UWalletLite"
            text = _("Incorrect password")
            icontype = "icon"
            qm = QMessageBoxEx(title, text, self, icontype)
            qm.exec_()
            self.show_error(str(e))
            return
        except:
            traceback.print_exc(file=sys.stdout)
            self.show_error(_('Failed to update password'))
            return

        msg = _('Password was updated successfully') if new_password else _('This wallet is not encrypted')
        self.show_message(msg, title=_("Success"))
        self.update_lock_icon()

    def toggle_search(self):
        self.search_box.setHidden(not self.search_box.isHidden())
        if not self.search_box.isHidden():
            self.search_box.setFocus(1)
        else:
            self.do_search('')

    def do_search(self, t):
        i = self.tabs.currentIndex()
        if i == 0:
            self.history_list.filter(t, [2, 3, 4])  # Date, Description, Amount
        elif i == 1:
            self.invoice_list.filter(t, [0, 1, 2, 3]) # Date, Requestor, Description, Amount
        # elif i == 2:
        #     self.request_list.filter(t, [0, 1, 2, 3, 4]) # Date, Account, Address, Description, Amount
        elif i == 3:
            self.address_list.filter(t, [0,1, 2])  # Address, Label, Balance
        # elif i == 4:
        #     self.contact_list.filter(t, [0, 1])  # Key, Value


    def new_contact_dialog(self):
        d = WindowModalDialog(self, _("New Contact"))
        vbox = QVBoxLayout(d)
        d.setTitleBar(vbox)
        vbox.addWidget(QLabel(_('New Contact') + ':'))
        grid = QGridLayout()
        line1 = QLineEditEx()
        line1.setFixedWidth(280)
        line2 = QLineEditEx()
        line2.setFixedWidth(280)
        # grid.addWidget(QLabel(_("Address")), 1, 0)
        line1.setPlaceholderText(_("Address"))
        grid.addWidget(line1, 1, 1)
        # grid.addWidget(QLabel(_("Name")), 2, 0)
        line2.setPlaceholderText(_("Name"))
        grid.addWidget(line2, 2, 1)

        vbox.addLayout(grid)
        vbox.addLayout(Buttons(OkButton(d),CancelButton(d)))

        if not d.exec_():
            return

        if self.set_contact(unicode(line2.text()), str(line1.text())):
            self.tabs.setCurrentIndex(4)

    def show_master_public_keys(self):
        dialog = WindowModalDialog(self, _("Master Public Keys"))
        mpk_dict = self.wallet.get_master_public_keys()
        vbox = QVBoxLayout()
        dialog.setTitleBar(vbox)
        mpk_text = ShowQRTextEdit()
        mpk_text.setMaximumHeight(100)
        mpk_text.addCopyButton(self.app)
        sorted_keys = sorted(mpk_dict.keys())
        def show_mpk(index):
            mpk_text.setText(mpk_dict[sorted_keys[index]])

        # only show the combobox in case multiple accounts are available
        if len(mpk_dict) > 1:
            def label(key):
                if isinstance(self.wallet, Multisig_Wallet):
                    is_mine = False#self.wallet.master_private_keys.has_key(key)
                    mine_text = [_("cosigner"), _("self")]
                    return "%s (%s)" % (key, mine_text[is_mine])
                return key
            labels = list(map(label, sorted_keys))
            on_click = lambda clayout: show_mpk(clayout.selected_index())
            labels_clayout = ChoicesLayout(_("Master Public Keys"), labels,
                                           on_click)
            vbox.addLayout(labels_clayout.layout())

        show_mpk(0)
        vbox.addWidget(mpk_text)
        vbox.addLayout(Buttons(CloseButton(dialog)))
        dialog.setLayout(vbox)
        dialog.exec_()

    @protected
    def show_seed_dialog(self, password):
        if self.wallet.has_password() and password is None:
            # User cancelled password input
            return
        if not self.wallet.has_seed():
            self.show_message(_('This wallet has no seed'))
            return
        keystore = self.wallet.get_keystore()
        try:
            mnemonic = keystore.get_mnemonic(password)
            passphrase = keystore.get_passphrase(password)
        except BaseException as e:

            self.show_error(str(e))
            return
        from seed_dialog import SeedDialog
        d = SeedDialog(self, mnemonic, passphrase)
        d.exec_()



    def show_qrcode(self, data, title = _("QR code"), parent=None):
        if not data:
            return
        d = QRDialog(data, parent or self, title)
        d.exec_()

    def show_public_keys(self, address):
        if not address: return
        try:
            pubkey_list = self.wallet.get_public_keys(address)
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            self.show_message(str(e))
            return
        d = WindowModalDialog(self, _("Public key"))
        d.setMinimumSize(600, 200)
        vbox = QVBoxLayout()
        d.setTitleBar(vbox)
        vbox.addWidget( QLabel(_("Address") + ': ' + address))
        vbox.addWidget(QLabel(_("Public key") + ':'))
        keys_e = ShowQRTextEdit(text='\n'.join(pubkey_list))
        keys_e.addCopyButton(self.app)
        vbox.addWidget(keys_e)
        vbox.addLayout(Buttons(CloseButton(d)))
        d.setLayout(vbox)
        d.exec_()

    @protected
    def show_private_key(self, address, password):
        if not address: return
        try:
            if self.wallet.has_password() and password==None:
                return
            pk_list = self.wallet.get_private_key(address, password)
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            self.show_message(str(e))
            return

        d = WindowModalDialog(self, _("Private key"))
        d.setMinimumSize(600, 200)
        vbox = QVBoxLayout()
        d.setTitleBar(vbox)
        vbox.addWidget( QLabel(_("Address") + ': ' + address))
        vbox.addWidget( QLabel(_("Private key") + ':'))
        keys_e = ShowQRTextEdit(text='\n'.join(pk_list))
        keys_e.addCopyButton(self.app)
        vbox.addWidget(keys_e)
        vbox.addLayout(Buttons(CloseButton(d)))
        d.setLayout(vbox)
        d.exec_()

    def generate_key(self,main_address_e,b_g,b_rg):
        private_key = BitcoinPrivateKey()
        pk = private_key.to_wif()
        main_address_e.setText(pk)
        b_g.setEnabled(False)
        b_rg.setEnabled(True)

    def regenerate_key(self,main_address_e,signature_e):
        if not self.question(_('Warning: click the regenerate button to regenerate the master node certificate. Do you want to continue?')):#警告：点击重新生成按钮将会重新生成主节点证书,是否继续?
            return
        private_key = BitcoinPrivateKey()
        pk = private_key.to_wif()
        main_address_e.setText(pk)
        signature_e.setText('')

    @protected
    def do_sign(self, address, message, signature,main_address_e, password):
        message = unicode(message.text()).encode('utf-8')
        if message ==None or message =='':
            self.show_warning(_('Invalid message'))
            return
        pbk = str(address.currentText())
        if pbk == None or pbk == '' or len(pbk) != 34:
            self.show_warning(_('Invalid address'))
            return
        mainadd = str(main_address_e.text()).strip()
        if mainadd == None or mainadd == ''or len(mainadd) < 45:
            self.show_warning(_('Invalid main node key'))
            return
        task = partial(self.wallet.sign_message_bc, str(address.currentText()),
                       message, password,mainadd)
        def show_signed_message(sig):
            signature.setText(base64.b64encode(sig))
            signMsg = {}
            signMsg['Address'] = unicode(pbk).encode('utf-8')
            signMsg['IP'] = message
            signMsg['Signature'] = unicode(signature.toPlainText()).encode('utf-8')
            signMsg['Key'] = mainadd
            fpath = os.path.join(util.user_dir(), "msg_sign")
            with open(fpath, 'w') as f:
                s = json.dumps(signMsg, indent=4, sort_keys=True)
                r = f.write(s)
        self.wallet.thread.add(task, on_success=show_signed_message)

    def do_verify(self, address, message, signature):
        message = unicode(message.toPlainText())
        message = message.encode('utf-8')
        if message ==None or message =='':
            self.show_warning(_('Invalid message'))
            return
        pbk = str(address.text())
        if pbk == None or pbk == '' or len(pbk) != 34:
            self.show_warning(_('Invalid address'))
            return
        try:
            info = str(signature.toPlainText())
            if info == None or info == '':
                self.show_warning(_('Invalid signtrue'))
                return
            # This can throw on invalid base64
            sig = base64.b64decode(str(signature.toPlainText()))

            verified = bitcoin.verify_message(address.text(), sig, message)
        except:
            verified = False
        if verified:
            self.show_message(_("Signature verified"))
        else:
            self.show_error(_("Wrong signature"))


    def sign_verify_message(self, address=''):
        d = WindowModalDialog(self, _('Sign/verify Message'))
        d.setMaximumSize(610, 290)
        d.setMinimumSize(610, 290)
        layout = QVBoxLayout(d)
        d.setTitleBar(layout)

        hlayoutTop=QHBoxLayout()
        layout.addLayout(hlayoutTop)
        message_e = Ip4Edit()
        hlayoutTop.addWidget(QLabel(_('Message')))
        hlayoutTop.addWidget(message_e)


        hlayoutMid=QHBoxLayout()
        layout.addLayout(hlayoutMid)
        address_e = QComboBox()
        address_e.setView(QListView())
        receiving_addresses = self.wallet.get_receiving_addresses()[:]
        change_addresses = self.wallet.get_change_addresses()
        receiving_addresses.extend(change_addresses)
        address_e.addItems(receiving_addresses)
        if address.strip():
            address_e.setCurrentIndex(receiving_addresses.index(address))
        # address_e.setEditText(QString(address))
        address_e.setFixedWidth(481)
        hlayoutMid.addWidget(QLabel(_('Sign Address')))
        hlayoutMid.addWidget(address_e)

        hlayoutMid1=QHBoxLayout()
        layout.addLayout(hlayoutMid1)
        main_address_e = QLineEditEx()
        # main_address_e.setText(address)
        hlayoutMid1.addWidget(QLabel(_('Main Node Key')))
        hlayoutMid1.addWidget(main_address_e)

        hlayoutBtm=QHBoxLayout()
        layout.addLayout(hlayoutBtm)
        signature_e = QTextEditEx()
        hlayoutBtm.addWidget(QLabel(_('Signature')))
        hlayoutBtm.addWidget(signature_e)

        hbox = QHBoxLayout()
        b_g = QPushButton(_("Generate the private key"))
        b_rg = QPushButton(_("reGenerate the private key"))  # 重新生成
        b_g.clicked.connect(lambda: self.generate_key(main_address_e,b_g,b_rg))
        b_rg.clicked.connect(lambda: self.regenerate_key(main_address_e,signature_e))
        hbox.addWidget(b_g)
        hbox.addWidget(b_rg)

        b_s = QPushButton(_("Sign Main Node"))
        b_s.clicked.connect(lambda: self.do_sign(address_e, message_e, signature_e,main_address_e))
        hbox.addWidget(b_s)

        msgFilePath = os.path.join(util.user_dir(), "msg_sign")
        if not os.path.exists(msgFilePath):
            b_g.setEnabled(True)
            b_rg.setEnabled(False)
        else:
            b_g.setEnabled(False)
            b_rg.setEnabled(True)
            try:
                with open(msgFilePath, 'r') as f:
                    msgInfo = json.loads(f.read())
                    sAddress = msgInfo['Address']
                    message_e.setText(QString(msgInfo['IP']))
                    if sAddress not in receiving_addresses:
                        self.show_warning(_('The address is not included in the current list. Please check if it is the correct signature wallet.'))#地址不包含在当前列表中。请检查它是否是正确的签名钱包
                    else:
                        # address_e.setEditText(sAddress)
                        address_e.setCurrentIndex(receiving_addresses.index(sAddress))
                        main_address_e.setText(msgInfo['Key'])
                        signature_e.setText(msgInfo['Signature'])
            except Exception,ex:
                pass
        b = QPushButton(_("Close"))
        b.clicked.connect(d.accept)
        hbox.addWidget(b)
        layout.addLayout(hbox)
        d.exec_()




    @protected
    def do_decrypt(self, message_e, pubkey_e, encrypted_e, password):
        cyphertext = str(encrypted_e.toPlainText())
        if cyphertext ==None or cyphertext =='':
            self.show_warning(_('Invalid cyphertext'))
            return
        # task = partial(self.wallet.decrypt_message, str(pubkey_e.text()),
        #                cyphertext, password)
        # self.wallet.thread.add(task, on_success=message_e.setText)
        try:
            txt = self.wallet.decrypt_message(str(pubkey_e.text()),cyphertext, password)
            message_e.setText(txt)
            self.show_message(_("Decrypt Successed"))
        except:
            self.show_warning(_('Invalid decrypt'))
            return

    def do_encrypt(self, message_e, pubkey_e, encrypted_e):
        message = unicode(message_e.toPlainText())
        if message ==None or message =='':
            self.show_warning(_('Invalid message'))
            return
        pbk = str(pubkey_e.text())
        if pbk ==None or pbk =='' or len(pbk)!=66:
            self.show_warning(_('Invalid pubkey'))
            return
        message = message.encode('utf-8')
        try:
            encrypted = bitcoin.encrypt_message(message, pbk)
            encrypted_e.setText(encrypted)
        except BaseException as e:
            traceback.print_exc(file=sys.stdout)
            self.show_warning(str(e))


    def encrypt_message(self, address = ''):
        d = WindowModalDialog(self, _('Encrypt/decrypt Message'))
        d.setMinimumSize(610, 490)

        layout = QVBoxLayout(d)
        d.setTitleBar(layout)

        tlayout=QHBoxLayout()
        layout.addLayout(tlayout)
        message_e = QTextEditEx()
        tlayout.addWidget(QLabel(_('Message')))
        tlayout.addWidget(message_e)

        mlayout=QHBoxLayout()
        layout.addLayout(mlayout)
        pubkey_e = QLineEditEx()
        if address:
            sequence = self.wallet.get_address_index(address)
            pubkey = self.wallet.get_pubkey(*sequence)
            pubkey_e.setText(pubkey)
        mlayout.addWidget(QLabel(_('Public key')))
        mlayout.addWidget(pubkey_e)

        blayout=QHBoxLayout()
        layout.addLayout(blayout)
        encrypted_e = QTextEditEx()
        blayout.addWidget(QLabel(_('Encrypted')))
        blayout.addWidget(encrypted_e)

        hbox = QHBoxLayout()
        b = QPushButton(_("Encrypt"))
        b.clicked.connect(lambda: self.do_encrypt(message_e, pubkey_e, encrypted_e))
        hbox.addWidget(b)

        b = QPushButton(_("Decrypt"))
        b.clicked.connect(lambda: self.do_decrypt(message_e, pubkey_e, encrypted_e))
        hbox.addWidget(b)

        b = QPushButton(_("Close"))
        b.clicked.connect(d.accept)
        hbox.addWidget(b)

        layout.addLayout(hbox)
        d.exec_()

    def password_dialog(self, msg=None, parent=None):
        parent = parent or self
        d = WindowModalDialog(parent, _("Enter Password"))
        pw = QLineEditEx()
        pw.setPlaceholderText(_('Password'))
        pw.setEchoMode(2)
        vbox = QVBoxLayout()
        d.setTitleBar(vbox)
        if not msg:
            msg = _('Please enter your password')
        vbox.addWidget(QLabel(msg))
        grid = QGridLayout()
        grid.setSpacing(8)
        # grid.addWidget(QLabel(_('Password')), 1, 0)
        grid.addWidget(pw, 1, 1)
        vbox.addLayout(grid)
        vbox.addLayout(Buttons(OkButton(d),CancelButton(d) ))
        d.setLayout(vbox)
        run_hook('password_dialog', pw, grid, 1)
        if not d.exec_(): return
        return unicode(pw.text())


    def tx_from_text(self, txt):
        from uwallet.transaction import tx_from_str, Transaction
        try:
            tx = tx_from_str(txt)
            return Transaction(tx)
        except:
            traceback.print_exc(file=sys.stdout)
            self.show_critical(_("UWalletLite was unable to parse your transaction"))
            return

    def read_tx_from_qrcode(self):
        from uwallet import qrscanner
        try:
            data = qrscanner.scan_qr(self.config)
        except BaseException as e:
            self.show_error(str(e))
            return
        if not data:
            return
        # if the user scanned a bitcoin URI
        if data.startswith("ulord:"):
            self.pay_to_URI(data)
            return
        # else if the user scanned an offline signed tx
        # transactions are binary, but qrcode seems to return utf8...
        data = data.decode('utf8')
        z = bitcoin.base_decode(data, length=None, base=43)
        data = ''.join(chr(ord(b)) for b in z).encode('hex')
        tx = self.tx_from_text(data)
        if not tx:
            return
        self.show_transaction(tx)


    def read_tx_from_file(self):
        fileName = self.getOpenFileName(_("Select your transaction file"), "*.txn")
        if not fileName:
            return
        try:
            with open(fileName, "r") as f:
                file_content = f.read()
        except (ValueError, IOError, os.error) as reason:
            self.show_critical(_("UWalletLite was unable to open your transaction file") + "\n" + str(reason), title=_("Unable to read file or no transaction found"))
        return self.tx_from_text(file_content)

    def do_process_from_text(self):
        text = text_dialog(self, _("Import multiple signatures"), _("Transaction sigature:"), _("Load transaction"))
        if not text:
            return
        tx = self.tx_from_text(text)
        if tx:
            self.show_transaction(tx)

    def do_process_from_file(self):
        tx = self.read_tx_from_file()
        if tx:
            self.show_transaction(tx)

    def do_process_from_txid(self):
        from uwallet import transaction
        # buttonBox = QDialogButtonBox()
        # buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)
        input =QInPutDialogEx(self)
        input.setOkButtonText(_("OK"))
        input.setCancelButtonText(_("Cancel"))
        input.setLabelText(_('Transaction ID'))
        input.setWindowTitle(_('Lookup transaction'))
        input.titleStr = _('Lookup transaction')
        input.setTitleBar(input.layout())
        txid = None
        if input.exec_():
            txid = input.textValue()
            if len(txid) != 64:
                self.show_message(_('Please input txid'))
                return
        if txid:
            txid = str(txid).strip()
            try:
                r = self.network.synchronous_get(('blockchain.transaction.get',[txid]))
            except BaseException as e:
                self.show_message(str(e))
                return
            tx = transaction.Transaction(r)
            self.show_transaction(tx)

#code border traffic say purchase sibling wide piece expire office wealth teach
    @protected
    def export_privkeys_dialog(self, password):
        if self.wallet.is_watching_only():
            self.show_message(_("This is a watching-only wallet"))
            return
        try:
            self.wallet.check_password(password)
        except Exception as e:
            if(password!=None):
                self.show_error(str(e))
            return

        d = WindowModalDialog(self, _('Private keys'))
        d.setMinimumSize(850, 300)
        vbox = QVBoxLayout(d)
        d.setTitleBar(vbox)
        msg = "%s\n%s\n%s" % (_("WARNING: ALL your private keys are secret."),
                              _("Exposing a single private key can compromise your entire wallet!"),
                              _("In particular, DO NOT use 'redeem private key' services proposed by third parties."))
        vbox.addWidget(QLabel(msg))

        e = QTextEditEx()
        e.setReadOnly(True)
        e.setStyleSheet("font-family: \"" + MONOSPACE_FONT + "\";")
        vbox.addWidget(e)

        defaultname = 'uwallet-private-keys.csv'
        select_msg = _('Select file to export your private keys to')
        hbox, filename_e, csv_button = filename_field(self, self.config, defaultname, select_msg)
        vbox.addLayout(hbox)

        b = OkButton(d, _('Export'))
        b.setEnabled(False)
        vbox.addLayout(Buttons(CancelButton(d), b))

        private_keys = {}
        addresses = self.wallet.get_addresses()
        done = False
        def privkeys_thread():
            for addr in addresses:
                time.sleep(0.1)
                if done:
                    break
                private_keys[addr] = "\n".join(self.wallet.get_private_key(addr, password))
                d.emit(SIGNAL('computing_privkeys'))
            d.emit(SIGNAL('show_privkeys'))

        def show_privkeys():
            s = "\n".join( map( lambda x: x[0] + "\t"+ x[1], private_keys.items()))
            e.setText(s)
            b.setEnabled(True)

        d.connect(d, QtCore.SIGNAL('computing_privkeys'), lambda: e.setText(_("Please wait... %d/%d")%(len(private_keys),len(addresses))))
        d.connect(d, QtCore.SIGNAL('show_privkeys'), show_privkeys)
        threading.Thread(target=privkeys_thread).start()

        if not d.exec_():
            done = True
            return

        filename = filename_e.text()
        if not filename:
            return

        try:
            self.do_export_privkeys(filename, private_keys, csv_button.isChecked())
        except (IOError, os.error) as reason:
            txt = "\n".join([
                _("UWalletLite was unable to produce a private key-export."),
                str(reason)
            ])
            self.show_critical(txt, title=_("Unable to create csv"))

        except Exception as e:
            self.show_message(str(e))
            return

        self.show_message(_("Private keys exported."))


    def do_export_privkeys(self, fileName, pklist, is_csv):
        with open(fileName, "w+") as f:
            if is_csv:
                transaction = csv.writer(f)
                # transaction.writerow(["address", "private_key"])
                for addr, pk in pklist.items():
                    # transaction.writerow(["%34s"%addr,pk])
                    transaction.writerow([pk])
            else:
                # import json
                # f.write(json.dumps(pklist, indent = 4))
                for addr, pk in pklist.items():
                    f.write(pk+'\n')


    def do_import_labels(self):
        labelsFile = self.getOpenFileName(_("Open labels file"), "*.json")
        if not labelsFile: return
        try:
            f = open(labelsFile, 'r')
            data = f.read()
            f.close()
            for key, value in json.loads(data).items():
                self.wallet.set_label(key, value)
            self.show_message(_("Your labels were imported from") + " '%s'" % str(labelsFile))
        except (IOError, os.error) as reason:
            self.show_critical(_("UWalletLite was unable to import your labels.") + "\n" + str(reason))


    def do_export_labels(self):
        labels = self.wallet.labels
        try:
            fileName = self.getSaveFileName(_("Select file to save your labels"), 'uwallet_labels.json', "*.json")
            if fileName:
                with open(fileName, 'w+') as f:
                    json.dump(labels, f, indent=4, sort_keys=True)
                self.show_message(_("Your labels where exported to") + " '%s'" % str(fileName))
        except (IOError, os.error), reason:
            self.show_critical(_("UWalletLite was unable to export your labels.") + "\n" + str(reason))


    def export_history_dialog(self):
        d = WindowModalDialog(self, _('Export History'))
        d.setMinimumSize(400, 200)
        vbox = QVBoxLayout(d)
        d.setTitleBar(vbox)
        defaultname = os.path.expanduser('~/uwallet-history.csv')
        select_msg = _('Select file to export your wallet transactions to')
        hbox, filename_e, csv_button = filename_field(self, self.config, defaultname, select_msg)
        vbox.addLayout(hbox)
        vbox.addStretch(1)
        hbox = Buttons(CancelButton(d), OkButton(d, _('Export')))
        vbox.addLayout(hbox)
        run_hook('export_history_dialog', self, hbox)
        self.update()
        if not d.exec_():
            return
        filename = filename_e.text()
        if not filename:
            return
        try:
            self.do_export_history(self.wallet, filename, csv_button.isChecked())
        except (IOError, os.error), reason:
            export_error_label = _("UWalletLite was unable to produce a transaction export.")
            self.show_critical(export_error_label + "\n" + str(reason), title=_("Unable to export history"))
            return
        self.show_message(_("Your wallet history has been successfully exported."))


    def do_export_history(self, wallet, fileName, is_csv):
        history = wallet.get_history()
        lines = []
        for item in history:
            tx_hash, height, confirmations, timestamp, value, balance = item
            if height>0:
                if timestamp is not None:
                    time_string = format_time(timestamp)
                else:
                    time_string = _("unverified")
            else:
                time_string = _("unconfirmed")

            if value is not None:
                value_string = format_satoshis(value, True)
            else:
                value_string = '--'

            if tx_hash:
                label = wallet.get_label(tx_hash)
                label = label.encode('utf-8')
            else:
                label = ""

            if is_csv:
                lines.append([tx_hash, label, confirmations, value_string, time_string])
            else:
                lines.append({'txid':tx_hash, 'date':"%16s"%time_string, 'label':label, 'value':value_string})

        with open(fileName, "w+") as f:
            if is_csv:
                transaction = csv.writer(f, lineterminator='\n')
                transaction.writerow(["transaction_hash","label", "confirmations", "value", "timestamp"])
                for line in lines:
                    transaction.writerow(line)
            else:
                import json
                f.write(json.dumps(lines, indent = 4))


    def sweep_key_dialog(self):
        d = WindowModalDialog(self, title=_('Sweep private keys'))
        d.setMinimumSize(600, 300)

        vbox = QVBoxLayout(d)
        d.setTitleBar(vbox)
        vbox.addWidget(QLabel(_("Enter private keys:")))

        keys_e = QTextEditEx()
        keys_e.setTabChangesFocus(True)
        vbox.addWidget(keys_e)

        addresses = self.wallet.get_unused_addresses(None)
        h, address_e = address_field(addresses)
        vbox.addLayout(h)

        vbox.addStretch(1)
        button = OkButton(d, _('Sweep'))
        vbox.addLayout(Buttons(CancelButton(d), button))
        button.setEnabled(False)

        def get_address():
            addr = str(address_e.text())
            if bitcoin.is_address(addr):
                return addr

        def get_pk():
            pk = str(keys_e.toPlainText()).strip()
            if Wallet.is_private_key(pk):
                return pk.split()

        f = lambda: button.setEnabled(get_address() is not None and get_pk() is not None)
        keys_e.textChanged.connect(f)
        address_e.textChanged.connect(f)
        if not d.exec_():
            return

        fee = self.wallet.fee_per_kb(self.config)
        tx = Transaction.sweep(get_pk(), self.network, get_address(), fee)
        if not tx:
            self.show_message(_('No inputs found. (Note that inputs need to be confirmed)'))
            return
        self.warn_if_watching_only()
        self.show_transaction(tx)

    def _do_import(self, title, msg, func):
        text = text_dialog(self, title, msg + ' :', _('Import'))
        if not text:
            return
        bad = []
        good = []
        for key in str(text).split():
            try:
                addr = func(key)
                good.append(addr)
            except BaseException as e:
                bad.append(key)
                continue
        if good:
            self.show_message(_("The following addresses were added") + ':\n' + '\n'.join(good))
        if bad:
            self.show_critical(_("The following inputs could not be imported") + ':\n'+ '\n'.join(bad))
        self.address_list.update()
        self.history_list.update()

    def import_addresses(self):
        if not self.wallet.can_import_address():
            return
        title, msg = _('Import addresses'), _("Enter addresses")
        self._do_import(title, msg, self.wallet.import_address)

    @protected
    def do_import_privkey(self, password):
        if not self.wallet.can_import_privkey():
            return
        title, msg = _('Import private keys'), _("Enter private keys")
        self._do_import(title, msg, lambda x: self.wallet.import_key(x, password))


    def settings_dialog(self):
        try:
            self.need_restart = False
            d = WindowModalDialog(self, _('Preferences'))
            d.setMinimumWidth(380)
            vbox = QVBoxLayout()
            d.setTitleBar(vbox)
            tabs = QTabWidget()
            tabs.setObjectName("settingtab")
            tabs.setStyleSheet("QTabBar::tab{background:white;font-family: \"Arial\";font:bold;width: 98px;height: 25px;}QTabBar::tab:selected{color:black;border-bottom: 2px solid #FFD100;}QTabBar::tab:!selected{color:rgb(150,150,150);}")

            gui_widgets = []
            fee_widgets = []
            tx_widgets = []
            id_widgets = []

            # language
            lang_help = _('Select which language is used in the GUI (after restart).')
            lang_label = HelpLabel(_('Language') + ':', lang_help)
            lang_combo = QComboBox()
            lang_combo.setView(QListView())
            from uwallet.i18n import languages
            lang_combo.addItems(self.languages.values())
            try:
                index = self.languages.keys().index(self.config.get("language",'zh_CN'))
            except Exception:
                index = 0
            lang_combo.setCurrentIndex(index)
            if not self.config.is_modifiable('language'):
                for w in [lang_combo, lang_label]: w.setEnabled(False)
            def on_lang(x):
                lang_request = self.languages.keys()[lang_combo.currentIndex()]
                print(lang_request)
                if lang_request != self.config.get('language'):
                    self.config.set_key("language", lang_request, True)
                    self.need_restart = True
            lang_combo.currentIndexChanged.connect(on_lang)
            gui_widgets.append((lang_label, lang_combo))

            nz_help = _('Number of zeros displayed after the decimal point. For example, if this is set to 2, "1." will be displayed as "1.00"')
            nz_label = HelpLabel(_('Zeros after decimal point') + ':', nz_help)
            nz = QSpinBoxEx()
            nz.setFocusPolicy(Qt.NoFocus);
            nz.setMinimum(0)
            nz.setMaximum(self.decimal_point)
            nz.setValue(self.num_zeros)
            if not self.config.is_modifiable('num_zeros'):
                for w in [nz, nz_label]: w.setEnabled(False)
            def on_nz():
                value = nz.value()
                if self.num_zeros != value:
                    self.num_zeros = value
                    self.config.set_key('num_zeros', value, True)
                    self.history_list.update()
                    self.address_list.update()
            nz.valueChanged.connect(on_nz)
            nz.setMinimum(1)
            gui_widgets.append((nz_label, nz))

            msg = _('Fee per kilobyte of transaction.')
            fee_label = HelpLabel(_('Transaction fee per kb') + ':', msg)
            fee_e = BTCkBEdit(self.get_decimal_point)
            def on_fee(is_done):
                if self.config.get('dynamic_fees', False):
                    return
                v = fee_e.get_amount() or 0
                self.config.set_key('fee_per_kb', v, is_done)
                self.update_fee()
            fee_e.editingFinished.connect(lambda: on_fee(True))
            fee_e.textEdited.connect(lambda: on_fee(False))
            fee_widgets.append((fee_label, fee_e))

            dynfee_cb = QCheckBox(_('Use dynamic fees'))
            dynfee_cb.setChecked(self.config.get('dynamic_fees', False))
            dynfee_cb.setToolTip(_("Use a fee per kB value recommended by the server."))
            fee_widgets.append((dynfee_cb, None))
            dynfee_cb.setHidden(True)
            def update_feeperkb():
                fee_e.setAmount(self.config.get('fee_per_kb', bitcoin.RECOMMENDED_FEE))
                b = self.config.get('dynamic_fees', False)
                fee_e.setEnabled(not b)
            def on_dynfee(x):
                self.config.set_key('dynamic_fees', x == Qt.Checked)
                update_feeperkb()
                self.update_fee_edit()
            dynfee_cb.stateChanged.connect(on_dynfee)
            update_feeperkb()
            #slider_moved()

            # msg = _('OpenAlias record, used to receive coins and to sign payment requests.') + '\n\n'\
            #       + _('The following alias providers are available:') + '\n'\
            #       + '\n'.join(['https://cryptoname.co/', 'http://xmr.link']) + '\n\n'
            # alias_label = HelpLabel(_('OpenAlias') + ':', msg)
            # alias = self.config.get('alias','')
            # alias_e = QLineEditEx(alias)
            # def set_alias_color():
            #     if not self.config.get('alias'):
            #         alias_e.setStyleSheet("")
            #         return
            #     if self.alias_info:
            #         alias_addr, alias_name, validated = self.alias_info
            #         alias_e.setStyleSheet(GREEN_BG if validated else RED_BG)
            #     else:
            #         alias_e.setStyleSheet(RED_BG)
            # def on_alias_edit():
            #     alias_e.setStyleSheet("")
            #     alias = str(alias_e.text())
            #     self.config.set_key('alias', alias, True)
            #     if alias:
            #         self.fetch_alias()
            # set_alias_color()
            # self.connect(self, SIGNAL('alias_received'), set_alias_color)
            # alias_e.editingFinished.connect(on_alias_edit)
            # id_widgets.append((alias_label, alias_e))

            # SSL certificate
            msg = ' '.join([
                _('SSL certificate used to sign payment requests.'),
                _('Use setconfig to set ssl_chain and ssl_privkey.'),
            ])
            # if self.config.get('ssl_privkey') or self.config.get('ssl_chain'):
            #     try:
            #         SSL_identity = paymentrequest.check_ssl_config(self.config)
            #         SSL_error = None
            #     except BaseException as e:
            #         SSL_identity = "error"
            #         SSL_error = str(e)
            # else:
            #     SSL_identity = ""
            #     SSL_error = None
            # SSL_id_label = HelpLabel(_('SSL certificate') + ':', msg)
            # SSL_id_e = QLineEditEx(SSL_identity)
            # SSL_id_e.setStyleSheet(RED_BG if SSL_error else GREEN_BG if SSL_identity else '')
            # if SSL_error:
            #     SSL_id_e.setToolTip(SSL_error)
            # SSL_id_e.setReadOnly(True)
            # id_widgets.append((SSL_id_label, SSL_id_e))

            units = ['UT', 'mUT', 'bits']
            msg = _('Base unit of your wallet.')\
                  + '\n1UT=1000mUT.\n' \
                  + _(' These settings affects the fields in the Send tab')+' '
            unit_label = HelpLabel(_('Base unit') + ':', msg)
            unit_combo = QComboBox()
            unit_combo.setView(QListView())
            unit_combo.addItems(units)
            unit_combo.setCurrentIndex(units.index(self.base_unit()))
            def on_unit(x):
                unit_result = units[unit_combo.currentIndex()]
                if self.base_unit() == unit_result:
                    return
                edits = self.amount_e, self.fee_e, self.receive_amount_e, fee_e
                amounts = [edit.get_amount() for edit in edits]
                if unit_result == 'UT':
                    self.decimal_point = 8
                elif unit_result == 'mUT':
                    self.decimal_point = 5
                elif unit_result == 'bits':
                    self.decimal_point = 2
                else:
                    raise Exception('Unknown base unit')
                self.config.set_key('decimal_point', self.decimal_point, True)
                self.history_list.update()
                # self.request_list.update()
                self.address_list.update()
                for edit, amount in zip(edits, amounts):
                    edit.setAmount(amount)
                self.update_status()
            unit_combo.currentIndexChanged.connect(on_unit)
            gui_widgets.append((unit_label, unit_combo))
            unit_label.setHidden(True)
            unit_combo.setHidden(True)

            block_explorers = sorted(block_explorer_info.keys())
            msg = _('Choose which online block explorer to use for functions that open a web browser')
            block_ex_label = HelpLabel(_('Online Block Explorer') + ':', msg)
            block_ex_combo = QComboBox()
            block_ex_combo.setView(QListView())
            block_ex_combo.addItems(block_explorers)
            block_ex_combo.setCurrentIndex(block_explorers.index(block_explorer(self.config)))
            def on_be(x):
                be_result = block_explorers[block_ex_combo.currentIndex()]
                self.config.set_key('block_explorer', be_result, True)
            block_ex_combo.currentIndexChanged.connect(on_be)
            gui_widgets.append((block_ex_label, block_ex_combo))
            block_ex_label.setHidden(True)
            block_ex_combo.setHidden(True)

            from uwallet import qrscanner
            system_cameras = qrscanner._find_system_cameras()
            qr_combo = QComboBox()
            qr_combo.setView(QListView())
            qr_combo.addItem("Default","default")
            for camera, device in system_cameras.items():
                qr_combo.addItem(camera, device)
            #combo.addItem("Manually specify a device", config.get("video_device"))
            index = qr_combo.findData(self.config.get("video_device"))
            qr_combo.setCurrentIndex(index)
            msg = _("Install the zbar package to enable this.\nOn linux, type: 'apt-get install python-zbar'")
            qr_label = HelpLabel(_('Video Device') + ':', msg)
            qr_combo.setEnabled(qrscanner.zbar is not None)
            on_video_device = lambda x: self.config.set_key("video_device", str(qr_combo.itemData(x).toString()), True)
            qr_combo.currentIndexChanged.connect(on_video_device)
            gui_widgets.append((qr_label, qr_combo))
            qr_label.setHidden(True)
            qr_combo.setHidden(True)

            use_rbf = self.config.get('use_rbf', False)
            rbf_cb = QCheckBox(_('Enable Replace-By-Fee'))
            rbf_cb.setChecked(use_rbf)
            def on_rbf(x):
                rbf_result = x == Qt.Checked
                self.config.set_key('use_rbf', rbf_result)
                self.rbf_checkbox.setVisible(rbf_result)
                self.rbf_checkbox.setChecked(False)
            rbf_cb.stateChanged.connect(on_rbf)
            rbf_cb.setToolTip(_('Enable RBF'))
            fee_widgets.append((rbf_cb, None))
            rbf_cb.setHidden(True)
            usechange_cb = QCheckBox(_('Use change addresses'))
            usechange_cb.setChecked(self.wallet.use_change)
            if not self.config.is_modifiable('use_change'): usechange_cb.setEnabled(False)
            def on_usechange(x):
                usechange_result = x == Qt.Checked
                if self.wallet.use_change != usechange_result:
                    self.wallet.use_change = usechange_result
                    self.wallet.storage.put('use_change', self.wallet.use_change)
                    multiple_cb.setEnabled(self.wallet.use_change)
                if not usechange_cb.isChecked():
                    multiple_cb.setChecked(False)
            usechange_cb.stateChanged.connect(on_usechange)
            usechange_cb.setToolTip(_('Using change addresses makes it more difficult for other people to track your transactions.'))
            tx_widgets.append((usechange_cb, None))

            def on_multiple(x):
                multiple = x == Qt.Checked
                if self.wallet.multiple_change != multiple:
                    self.wallet.multiple_change = multiple
                    self.wallet.storage.put('multiple_change', multiple)
            multiple_change = self.wallet.multiple_change
            multiple_cb = QCheckBox(_('Use multiple change addresses'))
            multiple_cb.setEnabled(self.wallet.use_change)
            multiple_cb.setToolTip('\n'.join([
                _('In some cases, use up to 3 change addresses in order to break '
                  'up large coin amounts and obfuscate the recipient address.'),
                _('This may result in higher transactions fees.')
            ]))
            multiple_cb.setChecked(multiple_change)
            multiple_cb.stateChanged.connect(on_multiple)
            tx_widgets.append((multiple_cb, None))

            def fmt_docs(key, klass):
                lines = [ln.lstrip(" ") for ln in klass.__doc__.split("\n")]
                return '\n'.join([key, "", " ".join(lines)])

            choosers = sorted(coinchooser.COIN_CHOOSERS.keys())
            chooser_name = coinchooser.get_name(self.config)
            msg = _('Choose coin (UTXO) selection method.  The following are available:\n\n')
            msg += '\n\n'.join(fmt_docs(*item) for item in coinchooser.COIN_CHOOSERS.items())
            chooser_label = HelpLabel(_('Coin selection') + ':', msg)
            chooser_combo = QComboBox()
            chooser_combo.setView(QListView())
            chooser_combo.addItems(choosers)
            i = choosers.index(chooser_name) if chooser_name in choosers else 0
            chooser_combo.setCurrentIndex(i)
            def on_chooser(x):
                chooser_name = choosers[chooser_combo.currentIndex()]
                self.config.set_key('coin_chooser', chooser_name)
            chooser_combo.currentIndexChanged.connect(on_chooser)
            tx_widgets.append((chooser_label, chooser_combo))
            chooser_label.setHidden(True)
            chooser_combo.setHidden(True)
            tabs_info = [
                (fee_widgets, _('Fees')),
                (tx_widgets, _('Transactions')),
                (gui_widgets, _('Appearance')),
                # (id_widgets, _('Identity')),
            ]
            for widgets, name in tabs_info:
                tab = QWidget()
                grid = QGridLayout(tab)
                grid.setColumnStretch(0,1)
                for a,b in widgets:
                    i = grid.rowCount()
                    if b:
                        if a:
                            grid.addWidget(a, i, 0)
                        grid.addWidget(b, i, 1)
                    else:
                        grid.addWidget(a, i, 0, 1, 2)

                tabs.addTab(tab, name)


            vbox.addWidget(tabs)
            vbox.addStretch(1)
            vbox.addLayout(Buttons(CloseButton(d)))
            d.setLayout(vbox)

            # run the dialog
            d.exec_()
            # self.disconnect(self, SIGNAL('alias_received'), set_alias_color)

            run_hook('close_settings_dialog')
            if self.need_restart:
                self.show_message(_('Please restart UWalletLite to activate the new GUI settings'),self, title=_('Success'))
        except Exception,ex:
            title = "UWalletLite"
            text = ex
            icontype = "icon"
            qm = QMessageBoxEx(title, text, self, icontype)
            qm.exec_()

    def run_network_dialog(self):
        try:
            if not self.network:
                self.show_warning(_('You are using UWalletLite in offline mode; restart UWalletLite if you want to get connected'), title=_('Offline'))
                return
            NetworkDialog(self.wallet.network, self.config, self).do_exec()
        except:
            return

    def closeEvent(self, event):
        # It seems in some rare cases this closeEvent() is called twice
        if not self.cleaned_up:
            self.cleaned_up = True
            self.clean_up()
        event.accept()

    def clean_up(self):
        self.wallet.thread.stop()
        if self.network:
            self.network.unregister_callback(self.on_network)
        # self.config.set_key("is_maximized", self.isMaximized())
        if not self.isMaximized():
            g = self.geometry()
            self.wallet.storage.put("winpos-qt", [g.left(),g.top(),
                                                  g.width(),g.height()])
        # self.config.set_key("console-history", self.console.history[-50:],
        #                     True)
        if self.qr_window:
            self.qr_window.close()
        self.close_wallet()
        self.gui_object.close_window(self)

    def plugins_dialog(self):
        self.pluginsdialog = d = WindowModalDialog(self, _('UWalletLite Plugins'))

        plugins = self.gui_object.plugins

        vbox = QVBoxLayout(d)
        d.setTitleBar(vbox)
        # plugins
        scroll = QScrollArea()
        scroll.setEnabled(True)
        scroll.setWidgetResizable(True)
        scroll.setMinimumSize(400,250)
        vbox.addWidget(scroll)

        w = QWidget()
        scroll.setWidget(w)
        w.setMinimumHeight(plugins.count() * 35)

        grid = QGridLayout()
        grid.setColumnStretch(0,1)
        w.setLayout(grid)

        settings_widgets = {}

        def enable_settings_widget(p, name, i):
            widget = settings_widgets.get(name)
            if not widget and p and p.requires_settings():
                widget = settings_widgets[name] = p.settings_widget(d)
                grid.addWidget(widget, i, 1)
            if widget:
                widget.setEnabled(bool(p and p.is_enabled()))

        def do_toggle(cb, name, i):
            p = plugins.toggle(name)
            cb.setChecked(bool(p))
            enable_settings_widget(p, name, i)
            run_hook('init_qt', self.gui_object)

        for i, descr in enumerate(plugins.descriptions.values()):
            name = descr['__name__']
            p = plugins.get(name)
            if descr.get('registers_keystore'):
                continue
            try:
                cb = QCheckBox(descr['fullname'])
                cb.setEnabled(plugins.is_available(name, self.wallet))
                cb.setChecked(p is not None and p.is_enabled())
                grid.addWidget(cb, i, 0)
                enable_settings_widget(p, name, i)
                cb.clicked.connect(partial(do_toggle, cb, name, i))
                msg = descr['description']
                if descr.get('requires'):
                    msg += '\n\n' + _('Requires') + ':\n' + '\n'.join(map(lambda x: x[1], descr.get('requires')))
                grid.addWidget(HelpButton(msg), i, 2)
            except Exception:
                self.print_msg("error: cannot display plugin", name)
                traceback.print_exc(file=sys.stdout)
        grid.setRowStretch(i+1,1)
        vbox.addLayout(Buttons(CloseButton(d)))
        d.exec_()

    def bump_fee_dialog(self, tx):
        is_relevant, is_mine, v, fee = self.wallet.get_wallet_delta(tx)
        d = WindowModalDialog(self, _('Bump Fee'))
        vbox = QVBoxLayout(d)
        d.setTitleBar(vbox)
        vbox.addWidget(QLabel(_('Current fee') + ': %s'% self.format_amount(fee) + ' ' + self.base_unit()))
        vbox.addWidget(QLabel(_('New Fee') + ': '))
        e = BTCAmountEdit(self.get_decimal_point)
        e.setAmount(fee *1.5)
        vbox.addWidget(e)
        cb = QCheckBox(_('Final'))
        vbox.addWidget(cb)
        vbox.addLayout(Buttons(OkButton(d), CancelButton(d)))
        if not d.exec_():
            return
        is_final = cb.isChecked()
        new_fee = e.get_amount()
        delta = new_fee - fee
        if delta < 0:
            self.show_error("fee too low")
            return
        try:
            new_tx = self.wallet.bump_fee(tx, delta)
        except BaseException as e:
            self.show_error(e)
            return
        if is_final:
            new_tx.set_sequence(0xffffffff)
        self.show_transaction(new_tx)
