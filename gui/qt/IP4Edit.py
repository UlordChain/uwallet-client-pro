from PyQt4.QtGui import *
from PyQt4.QtCore import *
import sys


class IpPartEdit(QLineEdit):
    def __init__(self, parent=None):
        QLineEdit.__init__(self, parent)

        self.nextTab = None
        self.setMaxLength(3)
        self.setFrame(False)
        self.setAlignment(Qt.AlignCenter)

        validator = QIntValidator(0, 255, self)
        self.setValidator(validator)

        self.connect(self, SIGNAL('textEdited(QString)'), \
                     self, SLOT('text_edited(QString)'))

    def set_nextTabEdit(self, nextTab):
        self.nextTab = nextTab

    def focusInEvent(self, event):
        self.selectAll()
        super(IpPartEdit, self).focusInEvent(event)

    def keyPressEvent(self, event):
        if (event.key() == Qt.Key_Period):
            if self.nextTab:
                self.nextTab.setFocus()
                self.nextTab.selectAll()
        super(IpPartEdit, self).keyPressEvent(event)

    @pyqtSlot('QString')
    def text_edited(self, text):
        validator = QIntValidator(0, 255, self)
        ipaddr = text
        pos = 0

        state = validator.validate(ipaddr, pos)[0]
        if state == QValidator.Acceptable:
            if ipaddr.size() > 1:
                if ipaddr.size() == 2:
                    ipnum = ipaddr.toInt()[0]
                    if ipnum > 25:
                        if self.nextTab:
                            self.nextTab.setFocus()
                            self.nextTab.selectAll()
                else:
                    if self.nextTab:
                        self.nextTab.setFocus()
                        self.nextTab.selectAll()

class Ip4Edit(QLineEdit):
    def __init__(self, parent=None):
        QLineEdit.__init__(self, parent)

        self.ip_part1 = IpPartEdit()
        self.ip_part2 = IpPartEdit()
        self.ip_part3 = IpPartEdit()
        self.ip_part4 = IpPartEdit()
        self.ip_part1.setAlignment(Qt.AlignCenter)
        self.ip_part2.setAlignment(Qt.AlignCenter)
        self.ip_part3.setAlignment(Qt.AlignCenter)
        self.ip_part4.setAlignment(Qt.AlignCenter)

        self.labeldot1 = QLabel('.')
        self.labeldot2 = QLabel('.')
        self.labeldot3 = QLabel('.')
        self.labeldot1.setAlignment(Qt.AlignCenter)
        self.labeldot2.setAlignment(Qt.AlignCenter)
        self.labeldot3.setAlignment(Qt.AlignCenter)

        layout = QHBoxLayout()
        layout.addWidget(self.ip_part1)
        layout.addWidget(self.labeldot1)
        layout.addWidget(self.ip_part2)
        layout.addWidget(self.labeldot2)
        layout.addWidget(self.ip_part3)
        layout.addWidget(self.labeldot3)
        layout.addWidget(self.ip_part4)
        layout.setSpacing(0)
        layout.setContentsMargins(QMargins(2, 2, 2, 2))

        self.setLayout(layout)

        QWidget.setTabOrder(self.ip_part1, self.ip_part2)
        QWidget.setTabOrder(self.ip_part2, self.ip_part3)
        QWidget.setTabOrder(self.ip_part3, self.ip_part4)
        self.ip_part1.set_nextTabEdit(self.ip_part2)
        self.ip_part2.set_nextTabEdit(self.ip_part3)
        self.ip_part3.set_nextTabEdit(self.ip_part4)

        self.connect(self.ip_part1, SIGNAL('textChanged(QString)'), \
                     self, SLOT('textChangedSlot(QString)'))
        self.connect(self.ip_part2, SIGNAL('textChanged(QString)'), \
                     self, SLOT('textChangedSlot(QString)'))
        self.connect(self.ip_part3, SIGNAL('textChanged(QString)'), \
                     self, SLOT('textChangedSlot(QString)'))
        self.connect(self.ip_part4, SIGNAL('textChanged(QString)'), \
                     self, SLOT('textChangedSlot(QString)'))

        self.connect(self.ip_part1, SIGNAL('textEdited(QString)'), \
                     self, SLOT('textEditedSlot(QString)'))
        self.connect(self.ip_part2, SIGNAL('textEdited(QString)'), \
                     self, SLOT('textEditedSlot(QString)'))
        self.connect(self.ip_part3, SIGNAL('textEdited(QString)'), \
                     self, SLOT('textEditedSlot(QString)'))
        self.connect(self.ip_part4, SIGNAL('textEdited(QString)'), \
                     self, SLOT('textEditedSlot(QString)'))

    @pyqtSlot('QString')
    def textChangedSlot(self, text):
        ippart1 = self.ip_part1.text()
        ippart2 = self.ip_part2.text()
        ippart3 = self.ip_part3.text()
        ippart4 = self.ip_part4.text()

        ipaddr = QString('%1.%2.%3.%4') \
            .arg(ippart1) \
            .arg(ippart2) \
            .arg(ippart3) \
            .arg(ippart4)
        self.emit(SIGNAL('textChanged'), ipaddr)
#
    @pyqtSlot('QString')
    def textEditedSlot(self, text):
        ippart1 = self.ip_part1.text()
        ippart2 = self.ip_part2.text()
        ippart3 = self.ip_part3.text()
        ippart4 = self.ip_part4.text()

        ipaddr = QString('%1.%2.%3.%4') \
            .arg(ippart1) \
            .arg(ippart2) \
            .arg(ippart3) \
            .arg(ippart4)
        self.emit(SIGNAL('textEdited'), ipaddr)

    def setText(self, text):
        regexp = QRegExp('^((2[0-4]\d|25[0-5]|[01]?\d\d?).){3}(2[0-4]\d||25[0-5]|[01]?\d\d?)$')
        validator = QRegExpValidator(regexp, self)
        nPos = 0
        state = validator.validate(text, nPos)[0]

        ippart1 = QString()
        ippart2 = QString()
        ippart3 = QString()
        ippart4 = QString()

        if state == QValidator.Acceptable:  # valid
            ippartlist = text.split('.')

            strcount = len(ippartlist)
            index = 0
            if index < strcount:
                ippart1 = ippartlist[index]
            index += 1
            if index < strcount:
                ippart2 = ippartlist[index]
                index += 1
            if index < strcount:
                ippart3 = ippartlist[index]
                index += 1
            if index < strcount:
                ippart4 = ippartlist[index]

        self.ip_part1.setText(ippart1)
        self.ip_part2.setText(ippart2)
        self.ip_part3.setText(ippart3)
        self.ip_part4.setText(ippart4)

    def text(self):
        ippart1 = self.ip_part1.text()
        ippart2 = self.ip_part2.text()
        ippart3 = self.ip_part3.text()
        ippart4 = self.ip_part4.text()

        return QString('%1.%2.%3.%4') \
            .arg(ippart1) \
            .arg(ippart2) \
            .arg(ippart3) \
            .arg(ippart4)

    def setStyleSheet(self, styleSheet):
        self.ip_part1.setStyleSheet(styleSheet)
        self.ip_part2.setStyleSheet(styleSheet)
        self.ip_part3.setStyleSheet(styleSheet)
        self.ip_part4.setStyleSheet(styleSheet)