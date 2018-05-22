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
from qrtextedit import ShowQRTextEdit, ScanQRTextEdit


class SeedLayoutBase(object):

    def _seed_layout(self, seed=None, title=None, icon=True):
        if seed:
            self.seed_e = ShowQRTextEdit()
            self.seed_e.setText(seed)
        else:
            self.seed_e = ScanQRTextEdit()
            self.seed_e.setTabChangesFocus(True)
        self.seed_e.setMaximumHeight(75)
        hbox = QHBoxLayout()
        if icon:
            logo = QLabel()
            logo.setPixmap(QPixmap(":icons/seed.png").scaledToWidth(64))
            logo.setMaximumWidth(60)
            # hbox.addWidget(logo)
        hbox.addWidget(self.seed_e)
        if not title:
            return hbox
        vbox = QVBoxLayout()
        vbox.addWidget(WWLabel(title))
        vbox.addLayout(hbox)
        return vbox

    def layout(self):
        return self.layout_

    def seed_edit(self):
        return self.seed_e



class SeedDisplayLayout(SeedLayoutBase):
    def __init__(self, seed, title=None, icon=True):
        self.layout_ = self._seed_layout(seed=seed, title=title, icon=icon)



def seed_warning_msg(seed):
    return ''.join([
        "<p>",
        _("Please save these %d words on paper (order is important). "),
        _("This seed will allow you to recover your wallet in case "
          "of computer failure."),
        "</p>",
        "<b><font color=red>" + _("WARNING") + ":</font></b>",
        "<ul>",
        "<li list-style-type:none;><font color=red>" + _("Never disclose your seed.") + "</font></li>",
        "<li><font color=red>" + _("Never type it on a website.") + "</font></li>",
        "<li><font color=red>" + _("Do not store it electronically.") + "</font></li>",
        "</ul>"
    ]) % len(seed.split())


class CreateSeedLayout(SeedLayoutBase):

    def __init__(self, seed):
        title =  _("Your wallet generation seed is:")
        vbox = QVBoxLayout()
        vbox.addLayout(self._seed_layout(seed=seed, title=title))
        msg = seed_warning_msg(seed)
        vbox.addWidget(WWLabel(msg))
        self.layout_ = vbox


class TextInputLayout(SeedLayoutBase):

    def __init__(self, parent, title, is_valid):
        self.is_valid = is_valid
        self.parent = parent
        self.layout_ = self._seed_layout(title=title, icon=False)
        self.seed_e.textChanged.connect(self.on_edit)

    def get_text(self):
        return clean_text(self.seed_edit())

    def on_edit(self):
        self.parent.next_button.setEnabled(self.is_valid(self.get_text()))


class SeedInputLayout(SeedLayoutBase):

    def __init__(self, parent, title, is_seed):
        vbox = QVBoxLayout()
        vbox.addLayout(self._seed_layout(title=title))
        hbox = QHBoxLayout()
        hbox.addStretch(1)
        hbox.addWidget(QLabel(''))
        self.seed_type_label = QLabel('')
        hbox.addWidget(self.seed_type_label)
        vbox.addLayout(hbox)
        self.layout_ = vbox
        self.parent = parent
        self.is_seed = is_seed
        self.seed_e.textChanged.connect(self.on_edit)

    def get_seed(self):
        return clean_text(self.seed_edit())

    def on_edit(self):
        from uwallet.bitcoin import seed_type
        s = self.get_seed()
        b = self.is_seed(s)
        t = seed_type(s)
        label = _('Seed Type') + ': ' + t if t else ''
        self.seed_type_label.setText(label)
        self.parent.next_button.setEnabled(b)



class ShowSeedLayout(SeedLayoutBase):
#team decline soap baby term dragon gaze staff all assist useful ivory
    def __init__(self, seed, passphrase):
        title =  _("Your wallet generation seed is:")
        vbox = QVBoxLayout()
        vbox.addLayout(self._seed_layout(seed=seed, title=title))
        if passphrase:
            hbox = QHBoxLayout()
            passphrase_e = QLineEditEx()
            passphrase_e.setText(passphrase)
            passphrase_e.setReadOnly(True)
            hbox.addWidget(QLabel('Your seed passphrase is'))
            hbox.addWidget(passphrase_e)
            vbox.addLayout(hbox)
        msg = seed_warning_msg(seed)
        vbox.addWidget(WWLabel(msg))
        self.layout_ = vbox


class SeedDialog(WindowModalDialog):
    def __init__(self, parent, seed, passphrase):
        WindowModalDialog.__init__(self, parent, ('UWalletLite - ' + _('Seed')))
        self.setMinimumWidth(400)
        vbox = QVBoxLayout(self)
        self.setTitleBar(vbox)
        vbox.addLayout(ShowSeedLayout(seed, passphrase).layout())
        vbox.addLayout(Buttons(CloseButton(self)))
