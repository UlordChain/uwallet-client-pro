# -*- coding: utf-8 -*-
# @Time    : 2017/12/14
# @Author  : Shu
# @Email   : httpservlet@yeah.net

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from ui_title import Ui_titleWD


class TitleWidget(QWidget, Ui_titleWD):
    def __init__(self, parent=None):
        super(TitleWidget, self).__init__(parent)
        self.setupUi(self,parent)

        self.parent = parent

        # self.tbt_history.setIcon(QIcon(":/images/history1"))
        # self.tbt_send.setIcon(QIcon(":/images/send1"))
        # self.tbt_receive.setIcon(QIcon(":/images/receive1"))
        # self.tbt_addresses.setIcon(QIcon(":/images/addresses1"))
        #
        # self.lbl_icon.setPixmap(QPixmap(":/images/logo"))
        # self.lbl_icon.setFixedSize(80, 16)

        # self.btn_file.setCursor(QCursor(Qt.PointingHandCursor))
        # self.btn_wallet.setCursor(QCursor(Qt.PointingHandCursor))
        # self.btn_view.setCursor(QCursor(Qt.PointingHandCursor))
        # self.btn_tools.setCursor(QCursor(Qt.PointingHandCursor))
        # self.btn_help.setCursor(QCursor(Qt.PointingHandCursor))
        # self.tbt_history.setCursor(QCursor(Qt.PointingHandCursor))
        # self.tbt_send.setCursor(QCursor(Qt.PointingHandCursor))
        # self.tbt_receive.setCursor(QCursor(Qt.PointingHandCursor))
        # self.tbt_addresses.setCursor(QCursor(Qt.PointingHandCursor))

        # self.btn_password.setCursor(QCursor(Qt.PointingHandCursor))
        # self.btn_setting.setCursor(QCursor(Qt.PointingHandCursor))
        # self.btn_seed.setCursor(QCursor(Qt.PointingHandCursor))

        self.button_group = QButtonGroup(self)
        # self.button_group.addButton(self.tbt_history)
        # self.button_group.addButton(self.tbt_send)
        # self.button_group.addButton(self.tbt_receive)
        # self.button_group.addButton(self.tbt_addresses)

        # self.tbt_history.clicked.connect(self.slot_checked)
        # self.tbt_send.clicked.connect(self.slot_checked)
        # self.tbt_receive.clicked.connect(self.slot_checked)
        # self.tbt_addresses.clicked.connect(self.slot_checked)


        # self.tbt_history.installEventFilter(self)
        # self.tbt_send.installEventFilter(self)
        # self.tbt_receive.installEventFilter(self)
        # self.tbt_addresses.installEventFilter(self)

    def slot_checked(self):
        for b in self.button_group.buttons():
            name = unicode(b.objectName()).split('_')[1]
            if b.isChecked():
                b.setIcon(QIcon(":/images/{}3".format(name)))
                b.setStyleSheet("QWidget{color:#4BA49C;}")
            else:
                b.setIcon(QIcon(":/images/{}1".format(name)))
                b.setStyleSheet("")

    def eventFilter(self, obj, event):
        if isinstance(obj, QToolButton):
            name = unicode(obj.objectName()).split('_')[1]
            if event.type() == QEvent.Enter:
                obj.setIcon(QIcon(":/images/{}2".format(name)))
                obj.setStyleSheet("QWidget{color:#68CAC1;}")
                return True
            elif event.type()==QEvent.MouseButtonPress:
                obj.setIcon(QIcon(":/images/{}3".format(name)))
                obj.setStyleSheet("QWidget{color:#4BA49C;}")
                return True
            elif event.type() == QEvent.Leave:
                obj.setIcon(QIcon(":/images/{}1".format(name)))
                obj.setStyleSheet("")
                return True
            else:
                return False
        else:
            return QWidget.eventFilter(obj, event)
