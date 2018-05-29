#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import mmap
import contextlib
import time
from PyQt4.QtGui import *
from PyQt4.QtCore import *
import math
import os
import json

class ProgressBar(QWidget):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        # self.setGeometry(300, 300, 250, 150)
        self.setWindowTitle('ProgressBar')
        self.setWindowIcon(QIcon('Uwallet.ico'))
        self.setWindowFlags(Qt.Dialog|Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumWidth(500)
        self.setContentsMargins(15, 9, 15, 15)

        self.pbar = QProgressBar(self)
        self.pbar.setTextDirection(QProgressBar.BottomToTop)#
        # self.pbar.setGeometry(30, 40, 200, 25)
        vbox =QVBoxLayout()
        self.setLayout(vbox)
        vbox.addWidget(self.pbar)
        self.setTitleBar(vbox)
        self.timer = QBasicTimer()
        self.step = 0
        self.onStart()
        self.center()


    def center(self):
        screen = QDesktopWidget().screenGeometry()
        # 获取屏幕分辨率
        size =  self.geometry()
        # 获取组件大小
        self.move((screen.width()-size.width())/1.8, (screen.height()-size.height())/1.3)
        p = os.path.join(os.environ["APPDATA"], "UWallet")
        path = os.path.join(p, "config")
        try:
            if os.path.exists(path):
                with open(path, "r") as f:
                    data = f.read()
                result = json.loads(data)
                self.language = result["language"]
            else:
                self.language="zh_CN"
        except:
            self.language = "zh_CN"


    def timerEvent(self, event):
            with open("process.dat", 'r') as f:
                with contextlib.closing(mmap.mmap(f.fileno(), 1024, access=mmap.ACCESS_READ)) as m:
                    s = m.read(1024).replace('\x00', '')
                    strs = s.split('/', 1);
                    if len(strs)!=2:
                        return
                    down = int(strs[0])
                    all = int(strs[1])
                    # all = all-all%96
                    if down==0:
                        if self.language=="zh_CN":
                            self.tq.setText(QString.fromUtf8("正在下载区块数据，请稍后..."))
                        else:
                            self.tq.setText(QString.fromUtf8("Synchronizing BlockHeader..."))
                    self.setWindowTitle(s)

                    self.pbar.setMaximum(int(all))
                    self.pbar.setValue(down)
                    if self.language=="zh_CN":
                        self.tq.setText(QString.fromUtf8("正在同步区块数据，请稍后...(%d/%d)" % (down, all)))
                    else:
                        self.tq.setText(QString.fromUtf8("Synchronizing BlockHeader...(%d/%d)" % (down, all)))
                    if down>=all:
                    # if (all-down)<=96:
                        self.pbar.setMaximum(self.pbar.maximum())
                        self.timer.stop()
                        sys.exit(0)

    def onStart(self):
        if self.timer.isActive():
            self.timer.stop()
        else:
            self.timer.start(800, self)

    def setTitleBar(self,vbox):
        self.tq = QLabel()
        self.tq.setStyleSheet("font-family: \"Arial\";font:bold;font-size:15px;border-bottom: 2px solid #FFD100;border-color:rgb(200,200,200);")
        self.btn_close = QPushButton()
        self.btn_close.setMinimumSize(QSize(21, 21))
        self.btn_close.setMaximumSize(QSize(21, 21))
        self.btn_close.setObjectName("btn_close")
        self.btn_close.clicked.connect(self.close)
        self.btn_close.setStyleSheet("QPushButton{border: 1px solid #333333;width: 78px;height: 25px;border-top-left-radius: 3px;border-top-right-radius: 3px;border-bottom-left-radius: 3px;border-bottom-right-radius: 3px;background: white;}QPushButton#btn_close{border:0px;background:url(ic_clear.png) center no-repeat;}QPushButton#btn_close:hover{border:0px;background:url(ic_clear_copy_pre.png) center no-repeat;}QPushButton#btn_close:pressed{border:0px;background:url(ic_clear.png) center no-repeat;}")
        hbox = QHBoxLayout()
        hbox.addWidget(self.tq)
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

if __name__ == '__main__':
    app = QApplication(sys.argv)
    icon = ProgressBar()
    icon.show()

    sys.exit(app.exec_())

