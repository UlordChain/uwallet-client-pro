#!/usr/bin/env python
#
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


import webbrowser

from util import *
from uwallet.i18n import _
from uwallet.util import block_explorer_URL, format_satoshis, format_time
from uwallet.plugins import run_hook


TX_ICONS = [
    "warning.png",
    "warning.png",
    "warning.png",
    "unconfirmed.png",
    "unconfirmed.png",
    "clock1.png",
    "clock2.png",
    "clock3.png",
    "clock4.png",
    "clock5.png",
    "confirmed.png",
]


class HistoryList(MyTreeWidget):

    def __init__(self, parent=None):
        MyTreeWidget.__init__(self, parent, self.create_menu, [], 3)
        self.refresh_headers()
        self.setColumnHidden(1, True)

    def refresh_headers(self):
        headers = ['', '', _('Date'), _('Description') , _('Amount')+'          ', _('Balance')+'           ',_(' ')]
        run_hook('history_tab_headers', headers)
        self.update_headers(headers)
        self.headerItem().setTextAlignment(4,Qt.AlignRight | Qt.AlignVCenter)
        self.headerItem().setTextAlignment(5, Qt.AlignRight | Qt.AlignVCenter)

    def get_domain(self):
        '''Replaced in address_dialog.py'''
        return self.wallet.get_addresses()

    def on_update(self):
        self.wallet = self.parent.wallet
        h = self.wallet.get_history(self.get_domain())
        item = self.currentItem()
        current_tx = item.data(0, Qt.UserRole).toString() if item else None
        self.clear()
        run_hook('history_tab_update_begin')
        # if(len(h)==0):
        self.header().setResizeMode(2, QHeaderView.Fixed)
        self.setColumnWidth(2, 170)
        self.header().setResizeMode(3, QHeaderView.Fixed)
        self.setColumnWidth(3, 120)
        self.header().setResizeMode(4, QHeaderView.Fixed)
        self.setColumnWidth(4, 120)
        self.header().setResizeMode(5, QHeaderView.Fixed)
        self.setColumnWidth(5, 180)
        for h_item in h:
            tx_hash, height, conf, timestamp, value, balance = h_item
            status, status_str = self.wallet.get_tx_status(tx_hash, height, conf, timestamp)
            icon = QIcon(":icons/" + TX_ICONS[status])
            v_str = self.parent.format_amount(value, True, whitespaces=True)
            balance_str = self.parent.format_amount(balance, whitespaces=True)
            label = self.wallet.get_label(tx_hash)
            entry = ['', tx_hash, status_str, label, v_str, balance_str]
            run_hook('history_tab_update', h_item, entry)
            item = QTreeWidgetItem(entry)
            item.setIcon(0, icon)
            for i in range(len(entry)):
                if i>3:
                    item.setTextAlignment(i, Qt.AlignRight|Qt.AlignVCenter)
                # if i!=2:
                #     item.setFont(i, QFont("Arial Black"))#MONOSPACE_FONT
            if value < 0:
                # item.setForeground(3, QBrush(QColor("red")))
                item.setForeground(4, QBrush(QColor("red")))
            if tx_hash:
                item.setData(0, Qt.UserRole, tx_hash)
            self.insertTopLevelItem(0, item)
            if current_tx == tx_hash:
                self.setCurrentItem(item)

    def update_item(self, tx_hash, height, conf, timestamp):
        status, status_str = self.wallet.get_tx_status(tx_hash, height, conf, timestamp)
        icon = QIcon(":icons/" +  TX_ICONS[status])
        items = self.findItems(tx_hash, Qt.UserRole|Qt.MatchContains|Qt.MatchRecursive, column=1)
        if items:
            item = items[0]
            item.setIcon(0, icon)
            item.setText(2, status_str)

    def create_menu(self, position):
        self.selectedIndexes()
        item = self.currentItem()
        if not item:
            return
        column = self.currentColumn()
        tx_hash = str(item.data(0, Qt.UserRole).toString())
        if not tx_hash:
            return
        if column is 0:
            column_title = "ID"
            column_data = tx_hash
        else:
            column_title = self.headerItem().text(column)
            column_data = item.text(column)

        tx_URL = block_explorer_URL(self.config, 'tx', tx_hash)
        height, conf, timestamp = self.wallet.get_tx_height(tx_hash)
        tx = self.wallet.transactions.get(tx_hash)
        is_relevant, is_mine, v, fee = self.wallet.get_wallet_delta(tx)
        rbf = is_mine and height <=0 and tx and not tx.is_final()
        menu = QMenu()
        menu.setStyleSheet(
            "QMenu{background-color: white;color: black;border: 0px solid #000;}QMenu::item::selected{color: black;background-color:rgb(255,251,160);}")
        menu.addAction(_("Copy %s")%column_title, lambda: self.parent.app.clipboard().setText(column_data))
        if column in self.editable_columns:
            menu.addAction(_("Edit %s")%column_title, lambda: self.editItem(item, column))

        menu.addAction(_("Details"), lambda: self.parent.show_transaction(tx))
        if rbf:
            menu.addAction(_("Increase fee"), lambda: self.parent.bump_fee_dialog(tx))
        # if tx_URL:
        #     menu.addAction(_("View on block explorer"), lambda: webbrowser.open(tx_URL))
        menu.exec_(self.viewport().mapToGlobal(position))
