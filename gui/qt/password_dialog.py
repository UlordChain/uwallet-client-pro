#!/usr/bin/env python
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2013 ecdsa@github
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

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from uwallet.i18n import _
from util import *
import re
import math

def check_password_strength(password):

    '''
    Check the strength of the password entered by the user and return back the same
    :param password: password entered by user in New Password
    :return: password strength Weak or Medium or Strong
    '''
    password = unicode(password)
    n = math.log(len(set(password)))
    num = re.search("[0-9]", password) is not None and re.match("^[0-9]*$", password) is None
    caps = password != password.upper() and password != password.lower()
    extra = re.match("^[a-zA-Z0-9]*$", password) is None
    score = len(password)*( n + caps + num + extra)/20
    password_strength = {0:_("Weak"),1:_("Medium"),2:_("Strong"),3:_("Very Strong")}
    return password_strength[min(3, int(score))]


PW_NEW, PW_CHANGE, PW_PASSPHRASE = range(0, 3)


class PasswordLayout(object):



    def __init__(self, wallet, msg, kind, OK_button):
        self.wallet = wallet
        self.titles = [_("Enter Password"), _("Change Password"), _("Enter Passphrase")]
        self.pw = QLineEditEx()
        self.pw.setEchoMode(2)
        self.new_pw = QLineEditEx()
        self.new_pw.setEchoMode(2)
        self.conf_pw = QLineEditEx()
        self.conf_pw.setEchoMode(2)
        self.kind = kind
        self.OK_button = OK_button

        vbox = QVBoxLayout()

        label = QLabel(msg + "\n")
        label.setStyleSheet("color:#999999;")
        label.setWordWrap(True)

        if kind == PW_PASSPHRASE:
            vbox.addWidget(label)
            msgs = [_('Passphrase:'), _('Confirm Passphrase:')]
        else:
            lblayout = QHBoxLayout()
            lblayout.addWidget(label)
            vbox.addLayout(lblayout)
            m1 = _('New Password:') if kind == PW_NEW else _('Password:')
            msgs = [m1, _('Confirm Password:')]
            if wallet and wallet.has_password():
                layouttop= QHBoxLayout()
                vbox.addLayout(layouttop)
                self.pw.setPlaceholderText(_('Current Password:'))
                layouttop.addWidget(self.pw)

        layoutmdl = QHBoxLayout()
        vbox.addLayout(layoutmdl)
        self.new_pw.setPlaceholderText(msgs[0])
        layoutmdl.addWidget(self.new_pw)

        layoutbtm = QHBoxLayout()
        vbox.addLayout(layoutbtm)
        self.conf_pw.setPlaceholderText(msgs[1])
        layoutbtm.addWidget(self.conf_pw)

        # Password Strength Label
        if kind != PW_PASSPHRASE:
            layoutstr = QHBoxLayout()
            vbox.addLayout(layoutstr)
            self.pw_strength = QLabel()
            layoutstr.addWidget(self.pw_strength)
            self.new_pw.textChanged.connect(self.pw_changed)

        def enable_OK():
            OK_button.setEnabled(self.new_pw.text() == self.conf_pw.text())
        self.new_pw.textChanged.connect(enable_OK)
        self.conf_pw.textChanged.connect(enable_OK)

        self.vbox = vbox

    def title(self):
        return self.titles[self.kind]

    def layout(self):
        return self.vbox

    def pw_changed(self):
        password = self.new_pw.text()
        if password:
            colors = {_("Weak"):"Red", _("Medium"):"Blue", _("Strong"):"Green",
                      _("Very Strong"):"Green"}
            strength = check_password_strength(password)
            label = (_("Password Strength") + ": " + "<font color="
                     + colors[strength] + ">" + strength + "</font>")
        else:
            label = ""
        self.pw_strength.setText(label)

    def old_password(self):
        if self.kind == PW_CHANGE:
            return unicode(self.pw.text()) or None
        return None

    def new_password(self):
        pw = unicode(self.new_pw.text())
        # Empty passphrases are fine and returned empty.
        if pw == "" and self.kind != PW_PASSPHRASE:
            pw = None
        return pw


class PasswordDialog(WindowModalDialog):

    def __init__(self, parent, wallet, msg, kind):
        WindowModalDialog.__init__(self, parent)
        OK_button = OkButton(self)
        self.playout = PasswordLayout(wallet, msg, kind, OK_button)
        self.setWindowTitle(self.playout.title())
        self.titleStr = self.playout.title()
        vbox = QVBoxLayout(self)
        self.setTitleBar(vbox)
        vbox.addLayout(self.playout.layout())
        vbox.addStretch(1)
        vbox.addLayout(Buttons(CancelButton(self), OK_button))

    def run(self):
        if not self.exec_():
            return False, None, None

        return True, self.playout.old_password(), self.playout.new_password()
