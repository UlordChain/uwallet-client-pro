#!/usr/bin/python
# -*- coding: UTF-8 -*-
# ：UpdateAppClient.py
import socket, time
import sys
from PyQt4.QtGui import *
from PyQt4.QtCore import *
import math
import os
import json
import zipfile
import shutil
import win32api

class ProgressBar(QWidget):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.setWindowTitle('ProgressBar')
        self.setWindowIcon(QIcon('Uwallet.ico'))
        self.setWindowFlags(Qt.Dialog|Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumWidth(500)
        self.setContentsMargins(15, 9, 15, 15)
        self.pbar = QProgressBar(self)
        self.pbar.setTextDirection(QProgressBar.BottomToTop)#
        vbox =QVBoxLayout()
        self.setLayout(vbox)
        vbox.addWidget(self.pbar)
        self.setTitleBar(vbox)
        self.timer = QBasicTimer()
        self.step = 0
        self.onStart()
        self.center()
        self.down = 0
        self.all = 0
        self.init_cntitle = QString.fromUtf8("正在更新程序，请稍后...")
        self.init_egtile = QString.fromUtf8("Downloadding...")
        self.prog_cntitle = QString.fromUtf8("正在更新程序，请稍后...(%d/%d)" % (self.down, self.all))
        self.prog_egtile = QString.fromUtf8("Downloadding...(%d/%d)" % (self.down, self.all))

    def closeEvent(self, event):

        print 'open uwallet'
        # win32api.ShellExecute(0, 'open', r'uwallet.exe', '', '', 1)
        sys.exit(0)


    def center(self):
        screen = QDesktopWidget().screenGeometry()
        size =  self.geometry()
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
        if self.down==0:
            if self.language=="zh_CN":
                self.tq.setText(self.init_cntitle)
            else:
                self.tq.setText(self.init_egtile)
        # self.setWindowTitle()
        self.pbar.setMaximum(self.all)
        self.pbar.setValue(self.down)
        if self.language=="zh_CN":
            self.tq.setText(self.prog_cntitle)
        else:
            self.tq.setText(self.prog_egtile)

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
            path.addRoundRect(m - i, m - i, self.width() - (
                    m - i) * 2, self.height() - (m - i) * 2, 1, 1)
            color.setAlpha(90 - math.sqrt(i) * 30)
            painter.setPen(QPen(color, 1, Qt.SolidLine))
            painter.drawRoundRect(QRect(m - i, m - i, self.width() - (m - i) * 2, self.height() - (m - i) * 2), 0, 0)


class UpdateAppClient:

    def __init__(self,progr):
        self.state = "new"
        self.progress = progr
        print 'Prepare for connecting...'

    def connect(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('118.190.145.8', 57888))#118.190.145.8
        self.down =False

        while True:
            self.name = 'get_version'
            sock.sendall(self.name)
            self.response = sock.recv(8192)
            print 'verson is:',self.response
            #todo:equal this app version if different set down = True
            with open("version") as f:
                version = f.readline()
                if version != str(self.response):
                    self.down = True
                    self.name = 'get_size'
                    sock.sendall(self.name)
                    self.response = sock.recv(8192)
                    print 'size is:',self.response
                    maxSize = int(self.response)
                    break
        if not self.down:
            print 'open uwallet1'
            # win32api.ShellExecute(0, 'open', r'uwallet.exe', '', '', 1)
            sock.sendall('bye')
            sock.close()
            sys.exit(0)
        else:
            file_name = 'temp.zip'
            sock.sendall('down')
            self.progress.all = maxSize
            # self.progress.show()
            while True:
                f = open(file_name, 'wb')
                while True:
                    data = sock.recv(1024)
                    self.progress.down += 1024
                    if data == 'EOF':
                        break
                    f.write(data)
                f.flush()
                f.close()
                print 'download finished'
                break
            sock.sendall('bye')
            sock.close()
        self.down =0
        self.all = 0
        self.init_cntitle = QString.fromUtf8("正在解压程序，请稍后...")
        self.init_egtile = QString.fromUtf8("Unzipping...")
        self.prog_cntitle = QString.fromUtf8("正在解压程序，请稍后...(%d/%d)" % (self.down, self.all))
        self.prog_egtile = QString.fromUtf8("Unzipping...(%d/%d)" % (self.down, self.all))
        """unzip zip file"""
        zip_file = zipfile.ZipFile(file_name)
        tempdir= "/temp_files"
        def removeDir():
            filelist = []
            filelist = os.listdir(tempdir)
            for f in filelist:
                filepath = os.path.join(tempdir, f)
                if os.path.isfile(filepath):
                    os.remove(filepath)
                    print filepath + " removed!"
                elif os.path.isdir(filepath):
                    shutil.rmtree(filepath, True)
                    print "dir " + filepath + " removed!"
        if os.path.isdir(tempdir):
            removeDir()
        else:
            os.mkdir(tempdir)
        self.all = zip_file.namelist().__len__()*2
        for names in zip_file.namelist():
            zip_file.extract(names, tempdir)
            self.down += 1
        zip_file.close()



        def copyfile(folder):
            folder = os.path.abspath(folder)
            os.chdir(folder)
            newFolder = os.path.abspath('..')
            for foldernames, subfolders, filenames in os.walk(folder):
                for filename in filenames:
                    self.down += 1
                    shutil.copy(filename, newFolder)

        # copyfile("/temp_files")
        copyfile("C:/zip")
        self.progress.timer.stop()
        self.progress.close()
        sys.exit(0)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    progress = ProgressBar()
    progress.show()
    # client = UpdateAppClient(progress)
    # client.connect()
    sys.exit(app.exec_())
