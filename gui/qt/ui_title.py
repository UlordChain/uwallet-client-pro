# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'F:\MyProject\Ulord\uwallet-client-pro\gui\qt\ui\title.ui'
#
# Created: Fri Apr 27 15:45:30 2018
#      by: PyQt4 UI code generator 4.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_titleWD(object):
    def setupUi(self, titleWD,parent):
        self.setObjectName(_fromUtf8("titleWD"))
        self.resize(960, 35)
        self.setMinimumSize(QtCore.QSize(0, 35))
        self.setMaximumSize(QtCore.QSize(16777215, 35))
        self.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.horizontalLayout = QtGui.QHBoxLayout(titleWD)
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setSizeConstraint(QtGui.QLayout.SetNoConstraint)
        self.horizontalLayout.setContentsMargins(15, 5, 5, 5)
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        # self.verticalLayout = QtGui.QVBoxLayout()
        # self.verticalLayout.setSpacing(0)
        # self.verticalLayout.setContentsMargins(-1, 0, 0, 0)
        # self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.horizontalLayout_5 = QtGui.QHBoxLayout()
        self.horizontalLayout_5.setSpacing(0)
        self.horizontalLayout_5.setContentsMargins(0, -1, 0, 0)
        self.horizontalLayout_5.setObjectName(_fromUtf8("horizontalLayout_5"))
        self.label_walletName = QtGui.QLabel(titleWD)
        font = QtGui.QFont()
        font.setFamily(_fromUtf8("Arial"))
        font.setPointSize(15)
        font.setBold(True)
        font.setWeight(75)

        self.label_walletName.setFont(font)
        self.label_walletName.setStyleSheet(_fromUtf8("color: #FFD100;"))
        self.label_walletName.setLineWidth(11)
        self.label_walletName.setScaledContents(False)
        self.label_walletName.setAlignment(QtCore.Qt.AlignBottom|QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft)
        self.label_walletName.setObjectName(_fromUtf8("label_walletName"))
        self.label_walletName.setStyleSheet("image:url(:icons/electrum_light_icon.png);")
        self.label_walletName.setMaximumSize(QtCore.QSize(20, 20))
        self.label_walletName.setMinimumSize(QtCore.QSize(20, 20))
        self.horizontalLayout_5.addWidget(self.label_walletName)

        spacerItem = QtGui.QSpacerItem(15, 20, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_5.addItem(spacerItem)

        # self.label_2 = QtGui.QLabel(titleWD)
        # font = QtGui.QFont()
        # font.setFamily(_fromUtf8("Arial"))
        # font.setPointSize(15)
        # font.setBold(True)
        # font.setWeight(75)
        # self.label_2.setFont(font)
        # self.label_2.setAlignment(QtCore.Qt.AlignBottom|QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft)
        # self.label_2.setObjectName(_fromUtf8("label_2"))
        # self.horizontalLayout_5.addWidget(self.label_2)
        menubar = parent.init_menubar()
        self.horizontalLayout_5.addWidget(menubar)

        # self.label_version = QtGui.QLabel(titleWD)
        # self.label_version.setSizeIncrement(QtCore.QSize(0, 0))
        # font = QtGui.QFont()
        # font.setFamily(_fromUtf8("Arial"))
        # font.setPointSize(15)
        # font.setBold(False)
        # font.setWeight(50)
        # font.setKerning(True)
        # self.label_version.setFont(font)
        # self.label_version.setAlignment(QtCore.Qt.AlignBottom|QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft)
        # self.label_version.setObjectName(_fromUtf8("label_version"))
        # self.horizontalLayout_5.addWidget(self.label_version)
        spacerItem1 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        self.horizontalLayout_5.addItem(spacerItem1)
        spacerItem2 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        self.horizontalLayout_5.addItem(spacerItem2)

        self.btn_min = QtGui.QPushButton(titleWD)
        self.btn_min.setMinimumSize(QtCore.QSize(21, 17))
        self.btn_min.setMaximumSize(QtCore.QSize(21, 17))
        self.btn_min.setText(_fromUtf8(""))
        self.btn_min.setObjectName(_fromUtf8("btn_min"))
        # self.btn_min.setStyleSheet("padding-right:10px;")
        self.horizontalLayout_5.addWidget(self.btn_min)
        self.btn_max = QtGui.QPushButton(titleWD)
        self.btn_max.setMinimumSize(QtCore.QSize(21, 17))
        self.btn_max.setMaximumSize(QtCore.QSize(21, 17))
        self.btn_max.setText(_fromUtf8(""))
        self.btn_max.setObjectName(_fromUtf8("btn_max"))

        spacerItem11 = QtGui.QSpacerItem(15, 20, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_5.addItem(spacerItem11)

        self.horizontalLayout_5.addWidget(self.btn_max)
        self.btn_close = QtGui.QPushButton(titleWD)
        self.btn_close.setMinimumSize(QtCore.QSize(21, 17))
        self.btn_close.setMaximumSize(QtCore.QSize(21, 17))
        self.btn_close.setText(_fromUtf8(""))
        self.btn_close.setObjectName(_fromUtf8("btn_close"))

        spacerItem12 = QtGui.QSpacerItem(15, 20, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_5.addItem(spacerItem12)

        self.horizontalLayout_5.addWidget(self.btn_close)
        # self.verticalLayout.addLayout(self.horizontalLayout_5)

        # self.horizontalLayout_6 = QtGui.QHBoxLayout()
        # self.horizontalLayout_6.setSpacing(14)
        # self.horizontalLayout_6.setContentsMargins(-1, -1, 0, 0)
        # self.horizontalLayout_6.setObjectName(_fromUtf8("horizontalLayout_6"))
        # spacerItem2 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        # self.horizontalLayout_6.addWidget(menubar)
        # self.horizontalLayout_6.addItem(spacerItem2)
        # self.btn_network = QtGui.QPushButton(titleWD)
        # self.btn_network.setMinimumSize(QtCore.QSize(17, 17))
        # self.btn_network.setMaximumSize(QtCore.QSize(17, 17))
        # self.btn_network.setText(_fromUtf8(""))
        # self.btn_network.setStyleSheet("background-color: #333333")
        # self.btn_network.setObjectName(_fromUtf8("btn_network"))
        # self.horizontalLayout_6.addWidget(self.btn_network)
        # self.verticalLayout.addLayout(self.horizontalLayout_6)
        self.horizontalLayout.addLayout(self.horizontalLayout_5)

        self.retranslateUi(titleWD)
        QtCore.QMetaObject.connectSlotsByName(titleWD)

    def retranslateUi(self, titleWD):
        titleWD.setWindowTitle(_translate("titleWD", "Form", None))
        self.label_walletName.setText(_translate("titleWD", "", None))
        # self.label_2.setText(_translate("titleWD", "Wallet", None))
        # self.label_version.setText(_translate("titleWD", "1.0", None))

