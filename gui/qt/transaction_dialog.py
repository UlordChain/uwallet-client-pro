#!/usr/bin/env python
# -*- coding: utf-8 -*-
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

import copy
import datetime
import json
import webbrowser
import PyQt4
from PyQt4.QtGui import *
from PyQt4.QtCore import *
import PyQt4.QtCore as QtCore

from uwallet import transaction
from uwallet.bitcoin import base_encode
from uwallet.i18n import _
from uwallet.plugins import run_hook
from uwallet import util
from uwallet.util import block_explorer_URL
from util import *

dialogs = []  # Otherwise python randomly garbage collects the dialogs...

def show_transaction(tx, parent, desc=None, prompt_if_unsaved=False):
    d = TxDialog(tx, parent, desc, prompt_if_unsaved)
    dialogs.append(d)
    d.show()

class TxDialog(QDialog, MessageBoxMixin):

    def __init__(self, tx, parent, desc, prompt_if_unsaved):
        '''Transactions in the wallet will show their description.
        Pass desc to give a description for txs not yet in the wallet.
        '''
        # We want to be a top-level window
        QDialog.__init__(self, parent=None)
        # Take a copy; it might get updated in the main window by
        # e.g. the FX plugin.  If this happens during or after a long
        # sign operation the signatures are lost.
        # f = QFile("F:\MyProject\Ulord\uwallet-client-pro\gui\qt\ui\wallet.qss")
        f = QFile("wallet.qss")
        f.open(QFile.ReadOnly)
        styleSheet = unicode(f.readAll(), encoding='utf8')
        self.setStyleSheet(styleSheet)
        f.close()

        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setContentsMargins(15, 9, 15, 15)

        self.tx = copy.deepcopy(tx)
        self.tx.deserialize()
        self.main_window = parent
        self.wallet = parent.wallet
        self.prompt_if_unsaved = prompt_if_unsaved
        self.saved = False
        self.desc = desc

        self.setMinimumWidth(660)
        self.setWindowTitle(_("Transaction"))

        vbox = QVBoxLayout()

        self.setTitleBar(vbox)
        self.setLayout(vbox)

        vbox.addWidget(QLabel(_("Transaction ID:")))
        self.tx_hash_e  = ButtonsLineEdit()
        qr_show = lambda: parent.show_qrcode(str(self.tx_hash_e.text()), _('Transaction ID'), parent=self)
        self.tx_hash_e.addButton(":icons/ic_qr_code.png", qr_show, _("Show as QR code"))
        self.tx_hash_e.setReadOnly(True)
        vbox.addWidget(self.tx_hash_e)
        self.tx_desc = QLabel()
        vbox.addWidget(self.tx_desc)
        self.status_label = QLabel()
        vbox.addWidget(self.status_label)
        self.date_label = QLabel()
        vbox.addWidget(self.date_label)
        self.amount_label = QLabel()
        vbox.addWidget(self.amount_label)
        self.fee_label = QLabel()
        vbox.addWidget(self.fee_label)

        self.add_io(vbox)

        vbox.addStretch(1)

        self.sign_button = b = QPushButton(_("Sign"))
        b.clicked.connect(self.sign)

        self.broadcast_button = b = QPushButton(_("Broadcast"))
        b.clicked.connect(self.do_broadcast)

        self.save_button = b = QPushButton(_("Save"))
        b.clicked.connect(self.save)

        self.cancel_button = b = QPushButton(_("Close"))
        b.clicked.connect(self.close)
        b.setDefault(True)

        self.qr_button = b = QPushButton()
        b.setIcon(QIcon(":icons/ic_qr_code.png"))
        b.clicked.connect(self.show_qr)
        self.qr_button.setStyleSheet(
            "QPushButton{background-color: white;border:0px;image: url(:icons/ic_qr_code.png)center no-repeat;}QPushButton:hover{image: url(:icons/ic_qr_code_pre.png) center no-repeat;}")
        self.s_button = ShowTxExplorButton(lambda: str(self.tx), parent.app)
        self.s_button.setMinimumWidth(150)
        self.s_button.clicked.connect(self.showExplorerTx)

        self.copy_button = CopyButton(lambda: str(self.tx), parent.app)


        # Action buttons
        self.buttons = [self.sign_button, self.broadcast_button, self.cancel_button]
        # Transaction sharing buttons
        self.sharing_buttons = [self.s_button, self.copy_button,self.qr_button, self.save_button]#self.qr_button,, self.save_button

        run_hook('transaction_dialog', self)

        hbox = QHBoxLayout()
        hbox.addLayout(Buttons(*self.sharing_buttons))
        hbox.addStretch(1)
        hbox.addLayout(Buttons(*self.buttons))
        vbox.addLayout(hbox)
        self.update()

    def showExplorerTx(self):
        tx_URL = block_explorer_URL(self.main_window.config, 'tx', str(self.tx_hash_e.text()))
        webbrowser.open(tx_URL)

    def setTitleBar(self,vbox):
        tq = QLabel(_("Transaction"))
        tq.setObjectName("QDialogTitle")
        tq.setStyleSheet("font-family: \"Arial\";font:bold;font-size:18px;border-bottom: 2px solid #FFD100;border-color:rgb(200,200,200);")
        self.btn_close = QPushButton()
        self.btn_close.setMinimumSize(QSize(21, 21))
        self.btn_close.setMaximumSize(QSize(21, 21))
        self.btn_close.setObjectName("btn_close1")
        self.btn_close.clicked.connect(self.close)
        hbox = QHBoxLayout()
        hbox.addWidget(tq)
        hbox.addWidget(self.btn_close)
        toto = QFrame()
        toto.setFrameShape(QFrame.HLine)
        toto.setFrameShadow(QFrame.Sunken)
        titleVBox = QVBoxLayout()
        titleVBox.addLayout(hbox)
        titleVBox.addWidget(toto)
        vbox.insertLayout(0,titleVBox,1)


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
    def paintEvent(self, event):
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

    def do_broadcast(self):
        self.main_window.push_top_level_window(self)
        try:
            self.main_window.broadcast_transaction(self.tx, self.desc)
        finally:
            self.main_window.pop_top_level_window(self)
        self.saved = True
        self.update()

    def closeEvent(self, event):
        if (self.prompt_if_unsaved and not self.saved
            and not self.question(_('This transaction is not saved. Close anyway?'), title=_("Warning"))):
            event.ignore()
        else:
            event.accept()
            dialogs.remove(self)

    def show_qr(self):
        text = str(self.tx).decode('hex')
        text = base_encode(text, base=43)
        try:
            self.main_window.show_qrcode(text, _('Transaction'), parent=self)
        except Exception as e:
            self.show_message(str(e))


    def sign(self):
        def sign_done(success):
            self.sign_button.setDisabled(False)
            self.main_window.pop_top_level_window(self)
            if success:
                self.prompt_if_unsaved = True
                self.saved = False
                self.update()

        self.sign_button.setDisabled(True)
        self.main_window.push_top_level_window(self)
        self.main_window.sign_tx(self.tx, sign_done)

    def save(self):
        name = 'signed_%s.txn' % (self.tx.hash()[0:8]) if self.tx.is_complete() else 'unsigned.txn'
        fileName = self.main_window.getSaveFileName(_("Select where to save your signed transaction"), name, "*.txn")
        if fileName:
            with open(fileName, "w+") as f:
                f.write(json.dumps(self.tx.as_dict(), indent=4) + '\n')
            self.show_message(_("Transaction saved successfully"))
            self.saved = True


    def update(self):
        desc = self.desc
        base_unit = self.main_window.base_unit()
        format_amount = self.main_window.format_amount
        tx_hash, status, label, can_broadcast, can_rbf, amount, fee, height, conf, timestamp, exp_n = self.wallet.get_tx_info(self.tx)

        if can_broadcast:
            self.broadcast_button.show()
        else:
            self.broadcast_button.hide()

        if self.wallet.can_sign(self.tx):
            self.sign_button.show()
        else:
            self.sign_button.hide()
        tx_hash = self.tx.hash()
        self.tx_hash_e.setText(tx_hash or _('Unknown'))
        if desc is None:
            self.tx_desc.hide()
        else:
            self.tx_desc.setText(_("Description") + ': ' + desc)
            self.tx_desc.show()
        tx_hei,tx_conf,tx_time = self.wallet.get_tx_height(tx_hash)
        c_status = _("%d confirmations") % tx_conf
        text_status = status if status == c_status else c_status
        self.status_label.setText(_('Status:') + ' ' + text_status)

        if timestamp:
            time_str = datetime.datetime.fromtimestamp(timestamp).isoformat(' ')[:-3]
            self.date_label.setText(_("Date: %s")%time_str)
            self.date_label.show()
        elif exp_n:
            text = '%d blocks'%(exp_n) if exp_n > 0 else _('unknown (low fee)')
            self.date_label.setText(_('Expected confirmation time') + ': ' + text)
            self.date_label.show()
        else:
            self.date_label.hide()
        if amount is None:
            amount_str = _("Transaction unrelated to your wallet")
        elif amount > 0:
            amount_str = _("Amount received:") + ' %s'% format_amount(amount) + ' ' + base_unit
        else:
            amount_str = _("Amount sent:") + ' %s'% format_amount(-amount) + ' ' + base_unit
        fee_str = _("Transaction fee") + ': %s'% (format_amount(fee) + ' ' + base_unit if fee is not None else _('None'))
        self.amount_label.setText(amount_str)
        self.fee_label.setText(fee_str)
        run_hook('transaction_dialog_update', self)

    def add_io(self, vbox):
        if self.tx.locktime > 0:
            timeArray = time.localtime(self.tx.locktime)
            otherStyleTime = time.strftime("%Y-%m-%d %H:%M:%S", timeArray)
            vbox.addWidget(QLabel(_("LockTime:") + otherStyleTime))

        vbox.addWidget(QLabel(_("Inputs") + _(' %d txs')%len(self.tx.inputs())))
        ext = QTextCharFormat()
        rec = QTextCharFormat()
        rec.setBackground(QBrush(QColor("lightgreen")))
        rec.setToolTip(_("Wallet receive address"))
        chg = QTextCharFormat()
        chg.setBackground(QBrush(QColor("yellow")))
        chg.setToolTip(_("Wallet change address"))

        def text_format(addr):
            if self.wallet.is_mine(addr):
                return chg if self.wallet.is_change(addr) else rec
            return ext

        def format_amount(amt):
            return self.main_window.format_amount(amt, whitespaces = True)

        i_text = QTextEditEx()
        i_text.setFont(QFont(MONOSPACE_FONT))
        i_text.setReadOnly(True)
        i_text.setStyleSheet("font-family: \""+MONOSPACE_FONT+"\";")
        i_text.setMaximumHeight(100)
        cursor = i_text.textCursor()
        for x in self.tx.inputs():
            if x.get('is_coinbase'):
                cursor.insertText('coinbase')
            else:
                prevout_hash = x.get('prevout_hash')
                prevout_n = x.get('prevout_n')
                cursor.insertText(prevout_hash[0:8] + '...', ext)
                cursor.insertText(prevout_hash[-8:] + ":%-4d " % prevout_n, ext)
                addr = x.get('address')
                if addr == "(pubkey)":
                    _addr = self.wallet.find_pay_to_pubkey_address(prevout_hash, prevout_n)
                    if _addr:
                        addr = _addr
                if addr is None:
                    addr = _('unknown')
                cursor.insertText(addr, text_format(addr))
                if x.get('value'):
                    cursor.insertText(format_amount(x['value']), ext)
            cursor.insertBlock()

        vbox.addWidget(i_text)
        vbox.addWidget(QLabel(_("Outputs") + _(' %d txs')%len(self.tx.outputs())))
        o_text = QTextEditEx()
        # o_text.setFont(QFont(MONOSPACE_FONT))
        o_text.setStyleSheet("font-family: \""+MONOSPACE_FONT+"\";")
        o_text.setReadOnly(True)
        o_text.setMaximumHeight(100)
        cursor = o_text.textCursor()
        for addr, v in self.tx.get_outputs():
            cursor.insertText(addr, text_format(addr))
            if v is not None:
                cursor.insertText('', ext)
                cursor.insertText(format_amount(v), ext)
            cursor.insertBlock()
        vbox.addWidget(o_text)
