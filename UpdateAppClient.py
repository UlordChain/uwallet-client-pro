#!/usr/bin/python
# -*- coding: UTF-8 -*-
# ：UpdateAppClient.py
# @Author       : QuPengcheng
# @Email        : 4514348@qq.com
# @Date         : 2018/06/04
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
import thread

down =0
all = 0

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
        global down
        global all



    def closeEvent(self, event):
        # print 'open uwallet'
        win32api.ShellExecute(0, 'open', r'uwallet.exe', '', '', 1)
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
        self.pbar.setMaximum(all)
        self.pbar.setValue(down)
        if self.language=="zh_CN":
            self.tq.setText(QString.fromUtf8("正在更新程序，请稍后...(%dm/%dm)" % (float(down)/1024.00/1024.00,float(all)/1024.00/1024.00)))
        else:
            self.tq.setText(QString.fromUtf8("Downloadding...(%dm/%dm)" % (float(down)/1024.00/1024.00,float(all)/1024.00/1024.00)))
        if down >= all:
            self.pbar.setMaximum(self.pbar.maximum())
            self.timer.stop()
            self.close()

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

    def __init__(self):
        self.state = "new"
        print 'Prepare for connecting...'
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(('118.190.145.8', 57888))#118.190.145.8
        self.bfsize =1024

    def update(self):
        global all
        global down
        file_name = 'temp.zip'
        self.sock.sendall('down')

        while True:
            f = open(file_name, 'wb')
            while True:
                data = self.sock.recv(self.bfsize)
                if not data:
                    print 'null data'
                    continue
                if data == 'EOF':
                    break
                f.write(data)

                down += len(data)
            f.flush()
            f.close()
            print 'download finished'
            break
        self.closeConnet()

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
        for names in zip_file.namelist():
            zip_file.extract(names, tempdir)
            down += 1
        zip_file.close()

        sourceDir = r"/temp_files"
        targetDir = r"./"
        # copyFileCounts = 0
        def copyFiles(sourceDir, targetDir):
            global down
            print sourceDir
            for f in os.listdir(sourceDir):
                sourceF = os.path.join(sourceDir, f)
                targetF = os.path.join(targetDir, f)
                if os.path.isfile(sourceF):
                    if not os.path.exists(targetDir):
                        os.makedirs(targetDir)
                    down += 1
                    open(targetF, "wb").write(open(sourceF, "rb").read())
                if os.path.isdir(sourceF):
                    copyFiles(sourceF, targetF)
        copyFiles(sourceDir,targetDir)

    def closeConnet(self):
        try:
            self.sock.sendall('bye')
            self.sock.close()
        except:
            return

    def InitNewVersion(self):
        global all
        while True:
            try:
                self.name = 'get_size'
                self.sock.sendall(self.name)
                self.response = self.sock.recv(8192)
                print 'size is:', self.response
                maxSize = int(self.response)

                self.name = 'get_file_count'
                self.sock.sendall(self.name)
                self.response = self.sock.recv(8192)
                print 'size is:', self.response
                fileCount = int(self.response)
                all = maxSize + fileCount * 2
                break
            except:
                raise Exception

if __name__ == '__main__':
    app = QApplication(sys.argv)
    try:
        progress = ProgressBar()
        socketClient = UpdateAppClient()
        socketClient.InitNewVersion()
        progress.show()
        thread.start_new_thread(socketClient.update,())
        sys.exit(app.exec_())
    except:
        win32api.ShellExecute(0, 'open', r'uwallet.exe', '', '', 1)
