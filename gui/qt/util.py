# -*- coding: utf-8 -*-
import os.path
import time
import traceback
import sys
import threading
import platform
import Queue
from collections import namedtuple
from functools import partial
import math

from uwallet.i18n import _
from PyQt4.QtGui import *
from PyQt4.QtCore import *

if platform.system() == 'Windows':
    MONOSPACE_FONT = 'Lucida Console'
elif platform.system() == 'Darwin':
    MONOSPACE_FONT = 'Monaco'
else:
    MONOSPACE_FONT = 'monospace'

GREEN_BG = "QWidget {background-color:#80ff80;}"
RED_BG = "QWidget {background-color:#ffcccc;}"
RED_FG = "QWidget {color:red;}"
BLUE_FG = "QWidget {color:blue;}"
BLACK_FG = "QWidget {color:black;}"

dialogs = []

from uwallet.paymentrequest import PR_UNPAID, PR_PAID, PR_UNKNOWN, PR_EXPIRED

pr_icons = {
    PR_UNPAID:":icons/unpaid.png",
    PR_PAID:":icons/confirmed.png",
    PR_EXPIRED:":icons/expired.png"
}

pr_tooltips = {
    PR_UNPAID:_('Pending'),
    PR_PAID:_('Paid'),
    PR_EXPIRED:_('Expired')
}

expiration_values = [
    (_('1 hour'), 60*60),
    (_('1 day'), 24*60*60),
    (_('1 week'), 7*24*60*60),
    (_('Never'), None)
]


def clean_text(seed_e):
    text = unicode(seed_e.toPlainText()).strip()
    text = ' '.join(text.split())
    return text


class Timer(QThread):
    stopped = False

    def run(self):
        while not self.stopped:
            self.emit(SIGNAL('timersignal'))
            time.sleep(0.5)

    def stop(self):
        self.stopped = True
        self.wait()

class EnterButton(QPushButton):
    def __init__(self, text, func):
        QPushButton.__init__(self, text)
        self.func = func
        self.clicked.connect(func)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Return:
            apply(self.func,())


class ThreadedButton(QPushButton):
    def __init__(self, text, task, on_success=None, on_error=None):
        QPushButton.__init__(self, text)
        self.task = task
        self.on_success = on_success
        self.on_error = on_error
        self.clicked.connect(self.run_task)

    def run_task(self):
        self.setEnabled(False)
        self.thread = TaskThread(self)
        self.thread.add(self.task, self.on_success, self.done, self.on_error)

    def done(self):
        self.setEnabled(True)
        self.thread.stop()


class WWLabel(QLabel):
    def __init__ (self, text="", parent=None):
        QLabel.__init__(self, text, parent)
        self.setWordWrap(True)


class HelpLabel(QLabel):

    def __init__(self, text, help_text):
        QLabel.__init__(self, text)
        self.help_text = help_text
        self.app = QCoreApplication.instance()
        self.font = QFont()

    def mouseReleaseEvent(self, x):
        qm = QMessageBoxEx(_("Help"), self.help_text, self)
        qm.exec_()

    def enterEvent(self, event):
        self.font.setUnderline(True)
        self.setFont(self.font)
        self.app.setOverrideCursor(QCursor(Qt.PointingHandCursor))
        return QLabel.enterEvent(self, event)

    def leaveEvent(self, event):
        self.font.setUnderline(False)
        self.setFont(self.font)
        self.app.setOverrideCursor(QCursor(Qt.ArrowCursor))
        return QLabel.leaveEvent(self, event)


class HelpButton(QPushButton):
    def __init__(self, text):
        QPushButton.__init__(self, '?')
        self.help_text = text
        self.setFocusPolicy(Qt.NoFocus)
        self.setFixedWidth(20)
        self.clicked.connect(self.onclick)

    def onclick(self):
        qm = QMessageBoxEx(_("Help"), self.help_text, self)
        qm.exec_()

class Buttons(QHBoxLayout):
    def __init__(self, *buttons):
        QHBoxLayout.__init__(self)
        self.addStretch(1)
        for b in buttons:
            self.addWidget(b)

class CloseButton(QPushButton):
    def __init__(self, dialog):
        QPushButton.__init__(self, _("Close"))
        self.clicked.connect(dialog.close)
        self.setDefault(True)

class ShowTxExplorButton(QPushButton):
    def __init__(self, text_getter, app):
        QPushButton.__init__(self, _("View on block explorer"))
        # self.clicked.connect(lambda: app.clipboard().setText(text_getter()))

class CopyButton(QPushButton):
    def __init__(self, text_getter, app):
        QPushButton.__init__(self, _("Copy"))
        self.clicked.connect(lambda: app.clipboard().setText(text_getter()))

class CopyCloseButton(QPushButton):
    def __init__(self, text_getter, app, dialog):
        QPushButton.__init__(self, _("Copy and Close"))
        self.clicked.connect(lambda: app.clipboard().setText(text_getter()))
        self.clicked.connect(dialog.close)
        self.setDefault(True)

class OkButton(QPushButton):
    def __init__(self, dialog, label=None):
        QPushButton.__init__(self, label or _("OK"))
        self.clicked.connect(dialog.accept)
        self.setDefault(True)

class CancelButton(QPushButton):
    def __init__(self, dialog, label=None):
        QPushButton.__init__(self, label or _("Cancel"))
        self.clicked.connect(dialog.reject)

class MessageBoxMixin(object):
    def top_level_window_recurse(self, window=None):
        window = window or self
        classes = (WindowModalDialog, QMessageBoxEx)
        for n, child in enumerate(window.children()):
            # Test for visibility as old closed dialogs may not be GC-ed
            if isinstance(child, classes) and child.isVisible():
                return self.top_level_window_recurse(child)
        return window

    def top_level_window(self):
        return self.top_level_window_recurse()

    def question(self, msg, parent=None, title=None, icon=None):
        return self.msg_box("question",
                            parent, title or _('Question'),
                            msg)

    def show_warning(self, msg, parent=None, title=None):
        return self.msg_box("warm", parent,
                            title or _('Warning'), msg)

    def show_error(self, msg, parent=None):
        return self.msg_box("warm", parent,
                            _('Error'), msg)

    def show_critical(self, msg, parent=None, title=None):
        return self.msg_box("warm", parent,
                            title or _('Critical Error'), msg)

    def show_message(self, msg, parent=None, title=None):
        return self.msg_box("info", parent,
                            title or _('Information'), msg)

    def msg_box(self, icon, parent, title, text):
        parent = parent or self.top_level_window()
        d = QMessageBoxEx(title,text,parent,icon)
        return d.exec_()


class WindowModalDialog(QDialog, MessageBoxMixin):
    '''Handy wrapper; window modal dialogs are better for our multi-window
    daemon model as other wallet windows can still be accessed.'''
    def __init__(self, parent,title=None):
        QDialog.__init__(self, parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setContentsMargins(15, 9, 15, 15)
        if title:
            self.titleStr= title

    def setTitleBar(self,vbox):
        tq = QLabel(self.titleStr)
        tq.setStyleSheet("font-family: \"Arial\";font:bold;font-size:15px;border-bottom: 2px solid #FFD100;border-color:rgb(200,200,200);")
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
        if type(vbox).__name__ == 'QGridLayout':
            vbox.addLayout(titleVBox, 0,0,1,1)
        else:
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

class QProgressDialogEx(QProgressDialog):
    def __init__(self,parent,title):
        super(QProgressDialog, self).__init__(parent)
        self.setWindowFlags(Qt.Dialog|Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.titleStr= title
        self.setMinimumWidth(400)
        self.setMinimumHeight(130)


    def setTitleBar(self,vbox):
        mainBox=QVBoxLayout()
        self.setLayout(mainBox)
        self.tq = QLabel()
        self.tq.setStyleSheet(
            "font-family: \"Arial\";font:bold;font-size:15px;border-bottom: 2px solid #FFD100;border-color:rgb(200,200,200);")
        self.btn_close = QPushButton()
        self.btn_close.setMinimumSize(QSize(21, 21))
        self.btn_close.setMaximumSize(QSize(21, 21))
        self.btn_close.setObjectName("btn_close1")
        self.btn_close.clicked.connect(self.close)
        hbox = QHBoxLayout()
        hbox.addWidget(self.tq)
        hbox.addWidget(self.btn_close)
        toto = QFrame()
        toto.setFrameShape(QFrame.HLine)
        toto.setFrameShadow(QFrame.Sunken)
        titleVBox = QVBoxLayout()
        titleVBox.addLayout(hbox)
        titleVBox.addWidget(toto)
        mainBox.addLayout(titleVBox)
        mainBox.addLayout(vbox)
        self.setContentsMargins(15, 9, 15, 15)

    def setTile(self, text):
        self.tq.setText(text)

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

class QInPutDialogEx(QInputDialog):
    def __init__(self, parent,title=None):
        QInputDialog.__init__(self, parent)
        self.setWindowFlags(Qt.Dialog|Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setContentsMargins(15, 9, 15, 15)
        if title:
            self.titleStr= title

    def setTitleBar(self,vbox):
        tq = QLabel(self.titleStr)
        tq.setStyleSheet("font-family: \"Arial\";font:bold;font-size:15px;border-bottom: 2px solid #FFD100;border-color:rgb(200,200,200);")
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
        if type(vbox).__name__ == 'QGridLayout':
            vbox.addLayout(titleVBox, 0,0,1,1)
        else:
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

class QMessageBoxEx(QDialog):
    def __init__(self,title,text,parent,iconType="info"):
        QDialog.__init__(self,parent)
        self.setWindowFlags(Qt.Dialog|Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMaximumWidth(700)
        self.setContentsMargins(15, 9, 15, 15)
        self.titleStr= title

        if len(text)>160:
            text = text[0:160]
            text += "......"
        vbox = QVBoxLayout(self)
        self.setTitleBar(vbox)
        mdlHbox=QHBoxLayout()
        vbox.addLayout(mdlHbox)
        btmHbox= QHBoxLayout()
        vbox.addLayout(btmHbox)

        ico = QLabel()
        ico.setScaledContents(True)
        str = iconType
        if iconType == "question":
            str ="prompt"
        if iconType == "info":
            str = "prompt"
        if iconType == "warm":
            str = "caveat"
        if iconType == "icon":
            str = "electrum_light_icon"
        ico.setMinimumHeight(32)
        ico.setMinimumWidth(32)
        ico.setMaximumHeight(32)
        ico.setMaximumWidth(32)
        ico.setStyleSheet("border-image:url(:/icons/"+str+") center no-repeat;")
        # ico.setScaledContents(True)
        mdlHbox.addWidget(ico)

        txt = QLabel()
        txt.setScaledContents(True)
        txt.setText(text)
        txt.adjustSize()
        txt.setGeometry(QRect(328, 240, 329, 27 * 4))
        txt.setWordWrap(True)
        txt.setAlignment(Qt.AlignTop)
        spacerItem2 = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
        mdlHbox.addItem(spacerItem2)
        mdlHbox.addWidget(txt)

        spacerItem1 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Expanding)
        btmHbox.addItem(spacerItem1)
        if iconType == "question":
            buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            buttonBox.button(QDialogButtonBox.Ok).setDefault(True)
            buttonBox.button(QDialogButtonBox.Ok).setText(_("OK"))
            buttonBox.button(QDialogButtonBox.Cancel).setText(_("Cancel"))
            btmHbox.addWidget(buttonBox)
            self.connect(buttonBox, SIGNAL("accepted()"), self, SLOT("accept()"))  #
            self.connect(buttonBox, SIGNAL("rejected()"), self, SLOT("reject()"))  #
        else:
            bt = QPushButton(_("OK"))
            bt.clicked.connect(self.close)
            btmHbox.addWidget(bt)


    def setTitleBar(self,vbox):
        tq = QLabel(self.titleStr)
        tq.setStyleSheet("font-family: \"Arial\";font:bold;font-size:15px;border-bottom: 2px solid #FFD100;border-color:rgb(200,200,200);")
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

class WaitingDialog(WindowModalDialog):
    '''Shows a please wait dialog whilst runnning a task.  It is not
    necessary to maintain a reference to this dialog.'''
    def __init__(self, parent, message, task, on_success=None, on_error=None):
        assert parent
        if isinstance(parent, MessageBoxMixin):
            parent = parent.top_level_window()
        WindowModalDialog.__init__(self, parent, _("Please wait"))
        vbox = QVBoxLayout(self)
        self.setTitleBar(vbox)
        vbox.addWidget(QLabel(message))
        self.accepted.connect(self.on_accepted)
        self.show()
        self.thread = TaskThread(self)
        self.thread.add(task, on_success, self.accept, on_error)

    def wait(self):
        self.thread.wait()

    def on_accepted(self):
        self.thread.stop()

class QTextEditEx(QTextEdit):
    def __init__(self):
        QTextEdit.__init__(self)

    def contextMenuEvent(self, e):
        m = self.createStandardContextMenu()
        acs = m.actions()
        for ac in acs:
            t = ac.text()
            if "Undo" in t:
                ac.setText(_("Undo        Ctrl+Z"))
                continue
            if "Redo" in t:
                ac.setText(_("Redo        Ctrl+Y"))
                continue
            if "Cu&t" in t:
                ac.setText(_("Cut         Ctrl+X"))
                continue
            if "Copy" in t:
                ac.setText(_("Copy        Ctrl+C"))
                continue
            if "Paste" in t:
                ac.setText(_("Paste       Ctrl+V"))
                continue
            if "Delete" in t:
                ac.setText(_("Delete"))
                continue
            if "Select" in t:
                ac.setText(_("SelectAll   Ctrl+A"))
                continue
        m.exec_(e.globalPos())

class QLineEditEx(QLineEdit):
    def __init__(self,text=None):
        QLineEdit.__init__(self,text)


    def contextMenuEvent(self, e):
        m = self.createStandardContextMenu()
        acs = m.actions()
        for ac in acs:
            t = ac.text()
            if "Undo" in t:
                ac.setText(_("Undo        Ctrl+Z"))
                continue
            if "Redo" in t:
                ac.setText(_("Redo        Ctrl+Y"))
                continue
            if "Cu&t" in t:
                ac.setText(_("Cut         Ctrl+X"))
                continue
            if "Copy" in t:
                ac.setText(_("Copy        Ctrl+C"))
                continue
            if "Paste" in t:
                ac.setText(_("Paste       Ctrl+V"))
                continue
            if "Delete" in t:
                ac.setText(_("Delete"))
                continue
            if "Select" in t:
                ac.setText(_("SelectAll   Ctrl+A"))
                continue
        m.exec_(e.globalPos())

class QSpinBoxEx(QSpinBox):
    def __init__(self):
        QSpinBox.__init__(self)

    def contextMenuEvent(self, e):
        return


def line_dialog(parent, title, label, ok_label, default=None):
    dialog = WindowModalDialog(parent, title)
    dialog.setMinimumWidth(500)
    l = QVBoxLayout()
    dialog.setTitleBar(l)
    dialog.setLayout(l)
    l.addWidget(QLabel(label))
    txt = QLineEditEx()
    if default:
        txt.setText(default)
    l.addWidget(txt)
    l.addLayout(Buttons(CancelButton(dialog), OkButton(dialog, ok_label)))
    if dialog.exec_():
        return unicode(txt.text())


def text_dialog(parent, title, label, ok_label, default=None):
    from qrtextedit import ScanQRTextEdit
    dialog = WindowModalDialog(parent, title)
    dialog.setMinimumWidth(500)
    l = QVBoxLayout()
    dialog.setTitleBar(l)
    dialog.setLayout(l)
    l.addWidget(QLabel(label))
    txt = ScanQRTextEdit()
    if default:
        txt.setText(default)
    l.addWidget(txt)
    l.addLayout(Buttons(CancelButton(dialog), OkButton(dialog, ok_label)))
    if dialog.exec_():
        return unicode(txt.toPlainText())

class ChoicesLayout(object):
    def __init__(self, msg, choices, on_clicked=None, checked_index=0):
        vbox = QVBoxLayout()
        # if msg:
        #     if len(msg) > 50:
        vbox.addWidget(WWLabel("<font style=\"font-weight:bold;\">"+msg+"</font>"))
                # msg = ""
        gb2 = QGroupBox()
        gb2.setStyleSheet("margin-bottom:6px;")
        # if msg:
        #     msgLabel = QLabel(msg)
        #     msgLabel.setStyleSheet("padding-left:8px;")
        #     vbox.addWidget(msgLabel)
        vbox.addWidget(gb2)

        vbox2 = QVBoxLayout()
        gb2.setLayout(vbox2)

        self.group = group = QButtonGroup()
        for i,c in enumerate(choices):
            button = QRadioButton(gb2)
            button.setText(c)
            vbox2.addWidget(button)
            group.addButton(button)
            group.setId(button, i)
            if i==checked_index:
                button.setChecked(True)

        if on_clicked:
            group.buttonClicked.connect(partial(on_clicked, self))

        self.vbox = vbox

    def layout(self):
        return self.vbox

    def selected_index(self):
        return self.group.checkedId()

def address_field(addresses):
    hbox = QHBoxLayout()
    address_e = QLineEditEx()
    if addresses:
        address_e.setText(addresses[0])
    def func():
        i = addresses.index(str(address_e.text())) + 1
        i = i % len(addresses)
        address_e.setText(addresses[i])
    button = QPushButton(_('Address'))
    button.clicked.connect(func)
    hbox.addWidget(button)
    hbox.addWidget(address_e)
    return hbox, address_e


def filename_field(parent, config, defaultname, select_msg):

    vbox = QVBoxLayout()
    vbox.addWidget(QLabel(_("Format")))
    gb = QGroupBox("format", parent)
    b1 = QRadioButton(gb)
    b1.setText(_("CSV"))
    b1.setChecked(True)
    b2 = QRadioButton(gb)
    b2.setText(_("json"))
    vbox.addWidget(b1)
    vbox.addWidget(b2)

    hbox = QHBoxLayout()

    directory = config.get('io_dir', unicode(os.path.expanduser('~')))
    path = os.path.join( directory, defaultname )
    filename_e = QLineEditEx()
    filename_e.setText(path)

    def func():
        text = unicode(filename_e.text())
        _filter = "*.csv" if text.endswith(".csv") else "*.json" if text.endswith(".json") else None
        p = unicode( QFileDialog.getSaveFileName(None, select_msg, text, _filter))
        if p:
            filename_e.setText(p)

    button = QPushButton(_('File'))
    button.clicked.connect(func)
    hbox.addWidget(button)
    hbox.addWidget(filename_e)
    vbox.addLayout(hbox)

    def set_csv(v):
        text = unicode(filename_e.text())
        text = text.replace(".json",".csv") if v else text.replace(".csv",".json")
        filename_e.setText(text)

    b1.clicked.connect(lambda: set_csv(True))
    b2.clicked.connect(lambda: set_csv(False))

    return vbox, filename_e, b1

class UWalletItemDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        return self.parent().createEditor(parent, option, index)

class MyTreeWidget(QTreeWidget):

    def __init__(self, parent, create_menu, headers, stretch_column=None,
                 editable_columns=None):
        QTreeWidget.__init__(self, parent)

        self.parent = parent
        self.config = self.parent.config
        self.stretch_column = stretch_column
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(create_menu)
        self.setUniformRowHeights(True)
        # extend the syntax for consistency
        self.addChild = self.addTopLevelItem
        self.insertChild = self.insertTopLevelItem

        # Control which columns are editable
        self.editor = None
        self.pending_update = False
        if editable_columns is None:
            editable_columns = [stretch_column]
        self.editable_columns = editable_columns
        self.setItemDelegate(UWalletItemDelegate(self))
        self.itemDoubleClicked.connect(self.on_doubleclick)
        self.update_headers(headers)

    def update_headers(self, headers):
        self.setColumnCount(len(headers))
        self.setHeaderLabels(headers)
        self.header().setSortIndicatorShown(False)
        self.header().setStretchLastSection(True)
        self.header().setMovable(False)
        for col in range(len(headers)):
            sm = QHeaderView.Stretch if col == self.stretch_column else QHeaderView.ResizeToContents
            self.header().setResizeMode(col, QHeaderView.ResizeToContents)

    def editItem(self, item, column):
        if column in self.editable_columns:
            self.editing_itemcol = (item, column, unicode(item.text(column)))

            # Calling setFlags causes on_changed events for some reason
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            QTreeWidget.editItem(self, item, column)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)

    def keyPressEvent(self, event):
        if event.key() in [ Qt.Key_F2, Qt.Key_Return ] and self.editor is None:
            self.on_activated(self.currentItem(), self.currentColumn())
        else:
            QTreeWidget.keyPressEvent(self, event)

    def permit_edit(self, item, column):
        return (column in self.editable_columns
                and self.on_permit_edit(item, column))

    def on_permit_edit(self, item, column):
        return True

    def on_doubleclick(self, item, column):
        if self.permit_edit(item, column):
            self.editItem(item, column)
        else:
            tx_hash = str(item.data(0, Qt.UserRole).toString())
            if not tx_hash:
                return
            if len(tx_hash)!=64:
                return
            tx = self.wallet.transactions.get(tx_hash)
            self.parent.show_transaction(tx)

    def on_activated(self, item, column):
        # on 'enter' we show the menu
        pt = self.visualItemRect(item).bottomLeft()
        pt.setX(50)
        self.emit(SIGNAL('customContextMenuRequested(const QPoint&)'), pt)

    def createEditor(self, parent, option, index):
        self.editor = QStyledItemDelegate.createEditor(self.itemDelegate(),
                                                       parent, option, index)
        self.editor.connect(self.editor, SIGNAL("editingFinished()"),
                            self.editing_finished)

        self.editor.setContextMenuPolicy(Qt.CustomContextMenu)

        self.editor.customContextMenuRequested.connect(self.create_standard_menu)
        return self.editor

    def create_standard_menu(self, position):
        m = self.editor.createStandardContextMenu()
        acs = m.actions()
        for ac in acs:
            t = ac.text()
            if "Undo" in t:
                ac.setText(_("Undo        Ctrl+Z"))
                continue
            if "Redo" in t:
                ac.setText(_("Redo        Ctrl+Y"))
                continue
            if "Cu&t" in t:#
                ac.setText(_("Cut         Ctrl+X"))
                continue
            if "Copy" in t:
                ac.setText(_("Copy        Ctrl+C"))
                continue
            if "Paste" in t:
                ac.setText(_("Paste       Ctrl+V"))
                continue
            if "Delete" in t:
                ac.setText(_("Delete"))
                continue
            if "Select" in t:
                ac.setText(_("SelectAll   Ctrl+A"))
                continue
        m.exec_(QCursor.pos())
    def editing_finished(self):
        # Long-time QT bug - pressing Enter to finish editing signals
        # editingFinished twice.  If the item changed the sequence is
        # Enter key:  editingFinished, on_change, editingFinished
        # Mouse: on_change, editingFinished
        # This mess is the cleanest way to ensure we make the
        # on_edited callback with the updated item
        if self.editor:
            (item, column, prior_text) = self.editing_itemcol
            if self.editor.text() == prior_text:
                self.editor = None  # Unchanged - ignore any 2nd call
            elif item.text(column) == prior_text:
                pass # Buggy first call on Enter key, item not yet updated
            else:
                # What we want - the updated item
                self.on_edited(*self.editing_itemcol)
                self.editor = None

            # Now do any pending updates
            if self.editor is None and self.pending_update:
                self.pending_update = False
                self.on_update()

    def on_edited(self, item, column, prior):
        '''Called only when the text actually changes'''
        key = str(item.data(0, Qt.UserRole).toString())
        text = unicode(item.text(column))
        self.parent.wallet.set_label(key, text)
        self.parent.history_list.update()
        self.parent.update_completions()

    def update(self):
        # Defer updates if editing
        if self.editor:
            self.pending_update = True
        else:
            self.on_update()

    def on_update(self):
        pass

    def get_leaves(self, root):
        child_count = root.childCount()
        if child_count == 0:
            yield root
        for i in range(child_count):
            item = root.child(i)
            for x in self.get_leaves(item):
                yield x

    def filter(self, p, columns):
        p = unicode(p).lower()
        for item in self.get_leaves(self.invisibleRootItem()):
            item.setHidden(all([unicode(item.text(column)).lower().find(p) == -1
                                for column in columns]))


class ButtonsWidget(QWidget):

    def __init__(self):
        super(QWidget, self).__init__()
        self.buttons = []

    def resizeButtons(self):
        frameWidth = self.style().pixelMetric(QStyle.PM_DefaultFrameWidth)
        x = self.rect().right() - frameWidth
        y = self.rect().bottom() - frameWidth
        for button in self.buttons:
            sz = button.sizeHint()
            x -= sz.width()
            button.move(x, y - sz.height())

    def addButton(self, icon_name, on_click, tooltip):
        button = QToolButton(self)
        button.setIcon(QIcon(icon_name))
        button.setStyleSheet(
            "QToolButton { border: none; hover {border: 1px;border-image:ic_folder_pre.png;} pressed {border: 1px} padding: 0px; }")
        button.setVisible(True)
        button.setToolTip(tooltip)
        button.clicked.connect(on_click)
        self.buttons.append(button)
        return button

    def addCopyButton(self, app):
        self.app = app
        f = lambda: self.app.clipboard().setText(str(self.text()))
        button=self.addButton(":icons/ic_library_books_pre.png", f, _("Copy to clipboard"))
        button.setStyleSheet(
            "QToolButton { border: none; hover {border: 1px;border-image:ic_folder_pre.png;} pressed {border: 1px} padding: 0px; }")

class ButtonsLineEdit(QLineEdit, ButtonsWidget):
    def __init__(self, text=None):
        QLineEdit.__init__(self, text)
        self.buttons = []

    def resizeEvent(self, e):
        o = QLineEdit.resizeEvent(self, e)
        self.resizeButtons()
        return o

    def contextMenuEvent(self, e):
        m = self.createStandardContextMenu()
        acs = m.actions()
        for ac in acs:
            t = ac.text()
            if "Undo" in t:
                ac.setText(_("Undo        Ctrl+Z"))
                continue
            if "Redo" in t:
                ac.setText(_("Redo        Ctrl+Y"))
                continue
            if "Cu&t" in t:
                ac.setText(_("Cut         Ctrl+X"))
                continue
            if "Copy" in t:
                ac.setText(_("Copy        Ctrl+C"))
                continue
            if "Paste" in t:
                ac.setText(_("Paste       Ctrl+V"))
                continue
            if "Delete" in t:
                ac.setText(_("Delete"))
                continue
            if "Select" in t:
                ac.setText(_("SelectAll   Ctrl+A"))
                continue
        m.exec_(e.globalPos())

class ButtonsTextEdit(QPlainTextEdit, ButtonsWidget):
    def __init__(self, text=None):
        QPlainTextEdit.__init__(self, text)
        self.setText = self.setPlainText
        self.text = self.toPlainText
        self.buttons = []

    def resizeEvent(self, e):
        o = QPlainTextEdit.resizeEvent(self, e)
        self.resizeButtons()
        return o

    def contextMenuEvent(self, e):
        m = self.createStandardContextMenu()
        acs = m.actions()
        for ac in acs:
            t = ac.text()
            if "Undo" in t:
                ac.setText(_("Undo        Ctrl+Z"))
                continue
            if "Redo" in t:
                ac.setText(_("Redo        Ctrl+Y"))
                continue
            if "Cu&t" in t:
                ac.setText(_("Cut         Ctrl+X"))
                continue
            if "Copy" in t:
                ac.setText(_("Copy        Ctrl+C"))
                continue
            if "Paste" in t:
                ac.setText(_("Paste       Ctrl+V"))
                continue
            if "Delete" in t:
                ac.setText(_("Delete"))
                continue
            if "Select" in t:
                ac.setText(_("SelectAll   Ctrl+A"))
                continue
        m.exec_(e.globalPos())

class TaskThread(QThread):
    '''Thread that runs background tasks.  Callbacks are guaranteed
    to happen in the context of its parent.'''

    Task = namedtuple("Task", "task cb_success cb_done cb_error")
    doneSig = pyqtSignal(object, object, object)

    def __init__(self, parent, on_error=None):
        super(TaskThread, self).__init__(parent)
        self.on_error = on_error
        self.tasks = Queue.Queue()
        self.doneSig.connect(self.on_done)
        self.start()

    def add(self, task, on_success=None, on_done=None, on_error=None):
        on_error = on_error or self.on_error
        self.tasks.put(TaskThread.Task(task, on_success, on_done, on_error))

    def run(self):
        while True:
            task = self.tasks.get()
            if not task:
                break
            try:
                result = task.task()
                self.doneSig.emit(result, task.cb_done, task.cb_success)
            except BaseException:
                self.doneSig.emit(sys.exc_info(), task.cb_done, task.cb_error)

    def on_done(self, result, cb_done, cb):
        # This runs in the parent's thread.
        if cb_done:
            cb_done()
        if cb:
            cb(result)

    def stop(self):
        self.tasks.put(None)


if __name__ == "__main__":
    app = QApplication([])
    t = WaitingDialog(None, 'testing ...', lambda: [time.sleep(1)], lambda x: QMessageBoxEx.information(None, 'done', "done", _('OK')))
    t.start()
    app.exec_()
