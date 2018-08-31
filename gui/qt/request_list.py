#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Electrum - lightweight Bitcoin client
# Copyright (C) 2015 Thomas Voegtlin
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


from uwallet.i18n import _
from uwallet.util import block_explorer_URL, format_satoshis, format_time, age
from uwallet.plugins import run_hook
from uwallet.paymentrequest import PR_UNPAID, PR_PAID, PR_UNKNOWN, PR_EXPIRED
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from util import MyTreeWidget, pr_tooltips, pr_icons


class RequestList(MyTreeWidget):

    def __init__(self, parent):
        MyTreeWidget.__init__(self, parent, self.create_menu, ['        '+_('Date'), _('Address'), '', _('Description'), _('Amount'), _('Status')], 3)
        self.pr_tooltips = {
            PR_UNPAID: _('Pending'),
            PR_PAID: _('Paid'),
            PR_EXPIRED: _('Expired')
        }
        self.currentItemChanged.connect(self.item_changed)
        self.itemClicked.connect(self.item_changed)
        self.setSortingEnabled(True)
        # self.setColumnWidth(0, 180)
        self.hideColumn(1)
        self.hideColumn(5)

    def item_changed(self, item):
        if item is None:
            return
        if not self.isItemSelected(item):
            return
        addr = str(item.text(1))
        req = self.wallet.receive_requests[addr]
        expires = age(req['time'] + req['exp']) if req.get('exp') else _('Never')
        amount = req['amount']
        message = self.wallet.labels.get(addr, '')
        self.parent.receive_address_e.setText(addr)
        self.parent.receive_message_e.setText(message)
        self.parent.receive_amount_e.setAmount(amount)
        self.parent.expires_combo.hide()
        # self.parent.expires_label.show()
        self.parent.expires_label.setText(expires)
        # self.parent.new_request_button.setEnabled(True)

    def on_update(self):
        self.wallet = self.parent.wallet
        # hide receive tab if no receive requests available
        b = len(self.wallet.receive_requests) > 0
        self.setVisible(b)
        # self.parent.receive_requests_label.setVisible(b)
        if not b:
            self.parent.expires_label.hide()
            # self.parent.expires_combo.show()

        # update the receive address if necessary
        current_address = self.parent.receive_address_e.text()
        domain = self.wallet.get_receiving_addresses()
        addr = self.wallet.get_unused_address()
        if not current_address in domain and addr:
            self.parent.set_receive_address(addr)
        # self.parent.new_request_button.setEnabled(addr != current_address)
        self.header().setResizeMode(0, QHeaderView.Fixed)
        self.setColumnWidth(0, 170)
        self.header().setResizeMode(3, QHeaderView.Fixed)
        self.setColumnWidth(3, 170)
        self.header().setResizeMode(4, QHeaderView.Fixed)
        self.setColumnWidth(4, 170)
        self.header().setResizeMode(5, QHeaderView.Fixed)
        self.setColumnWidth(5, 170)

        # clear the list and fill it again
        self.clear()
        for req in self.wallet.get_sorted_requests(self.config):
            address = req['address']
            if address not in domain:
                continue
            timestamp = req.get('time', 0)
            amount = req.get('amount')
            expiration = req.get('exp', None)
            message = req.get('memo', '')
            date = format_time(timestamp)
            status = req.get('status')
            signature = req.get('sig')
            requestor = req.get('name', '')
            amount_str = self.parent.format_amount(amount) if amount else ""
            item = QTreeWidgetItem([date, address, '', message, amount_str, self.pr_tooltips.get(status,'')])
            if signature is not None:
                # item.setIcon(2, QIcon(":icons/seal.png"))
                item.setToolTip(2, 'signed by '+ requestor)
            if status is not PR_UNKNOWN:
                item.setIcon(6, QIcon(pr_icons.get(status)))
            self.addTopLevelItem(item)


    def create_menu(self, position):
        item = self.itemAt(position)
        if not item:
            return
        addr = str(item.text(1))
        req = self.wallet.receive_requests[addr]
        column = self.currentColumn()
        column_title = self.headerItem().text(column)
        column_data = item.text(column)
        menu = QMenu(self)
        menu.addAction(_("Copy %s")%column_title, lambda: self.parent.app.clipboard().setText(column_data))
        menu.addAction(_("Copy URI"), lambda: self.parent.view_and_paste('URI', '', self.parent.get_request_URI(addr)))
        menu.addAction(_("Save as BIP70 file"), lambda: self.parent.export_payment_request(addr))
        menu.addAction(_("Delete"), lambda: self.parent.delete_payment_request(item))
        run_hook('receive_list_menu', menu, addr)
        menu.exec_(self.viewport().mapToGlobal(position))
