# ulord钱包编译运行打包指南

## 环境
- https://github.com/UlordChain/uwallet-client-pro utxo-merge分支
- Windows 10 x64
- Python 2.7 (32 bit)
> 由于`cryptohello_hash.pyd`模块编译为x86平台版本，因此必须Python以及下面的依赖必须安装win32版本

## 依赖
- vc_redist.x86:

下载链接：https://aka.ms/vs/16/release/vc_redist.x86.exe

下载页面：https://support.microsoft.com/en-us/help/2977003/the-latest-supported-visual-c-downloads
- Win32 OpenSSL

下载链接：http://slproweb.com/download/Win32OpenSSL-1_1_1g.msi

下载页面：http://slproweb.com/products/Win32OpenSSL.html
- PyQt4

下载链接：https://download.lfd.uci.edu/pythonlibs/w3jqiv8s/cp27/PyQt4-4.11.4-cp27-cp27m-win32.whl

下载页面：https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyqt4

- PyInstaller 3.6

```
pip install PyInstaller==3.6
```

- dnspython 1.12.0

```
pip install dnspython==1.12.0
```

## 步骤
1. 安装UWallet库
```
python setup.py install
```

2. `lib/cryptohello_hash.pyd`文件复制到UWallt库安装的路径

例如：`C:\Python27\Lib\site-packages\UWallet-2.0.2-py2.7.egg\uwallet`

3. 运行程序测试
```
python uwallet
```

4. 打包exe
```
python uwallet_pyinstaller.py
```
打包输出目录`dist/wallet`

5. `blockchain_headers`文件复制到`dist/wallet`

6. 封装安装文件

    1. 安装inno setup: https://jrsoftware.org/isinfo.php
    2. `package/dist_addon/`内文件复制至打包输出目录`dist/wallet`
    3. 运行inno setup，加载`package/wallet.iss`，修改版本号、源文件路径、输出路径，执行脚本