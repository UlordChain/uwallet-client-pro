#!/usr/bin/env python
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2014 Thomas Voegtlin
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

import re
import platform
from decimal import Decimal
from urllib import quote

from PyQt4.QtGui import *
from PyQt4.QtCore import *
import PyQt4.QtCore as QtCore
import PyQt4.QtGui as QtGui

from uwallet_gui.qt.qrcodewidget import QRCodeWidget
from uwallet.i18n import _

if platform.system() == 'Windows':
    MONOSPACE_FONT = 'Lucida Console'
elif platform.system() == 'Darwin':
    MONOSPACE_FONT = 'Monaco'
else:
    MONOSPACE_FONT = 'monospace'

column_index = 4

class QR_Window(QWidget):

    def __init__(self, win):
        QWidget.__init__(self)
        self.win = win
        self.setWindowTitle('UWalletLite - '+_('Payment Request'))
        self.setMinimumSize(800, 250)
        self.address = ''
        self.label = ''
        self.amount = 0
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setStyleSheet("background-color:white;")
        main_box = QHBoxLayout()

        self.qrw = QRCodeWidget()
        main_box.addWidget(self.qrw, 1)

        vbox = QVBoxLayout()
        main_box.addLayout(vbox)

        self.address_label = QLabel("")
        #self.address_label.setFont(QFont(MONOSPACE_FONT))
        vbox.addWidget(self.address_label)

        self.label_label = QLabel("")
        vbox.addWidget(self.label_label)

        self.amount_label = QLabel("")
        vbox.addWidget(self.amount_label)

        vbox.addStretch(1)
        self.setLayout(main_box)


    def set_content(self, address, amount, message, url):
        address_text = "<span style='font-size: 18pt'>%s</span>" % address if address else ""
        self.address_label.setText(address_text)
        if amount:
            amount = self.win.format_amount(amount)
            amount_text = "<span style='font-size: 21pt'>%s</span> <span style='font-size: 16pt'>%s</span> " % (amount, self.win.base_unit())
        else:
            amount_text = ''
        self.amount_label.setText(amount_text)
        label_text = "<span style='font-size: 21pt'>%s</span>" % message if message else ""
        self.label_label.setText(label_text)
        self.qrw.setData(url)
