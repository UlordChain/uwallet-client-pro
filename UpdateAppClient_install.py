# -*- coding: utf-8 -*-
# @Author       : Shu
# @Email        : httpservlet@yeah.net
# @Date         : 2017/12/27
# @Description  : 打包python项目为exe

# coding=utf-8


# http://www.cnblogs.com/dcb3688/p/4211390.html
if __name__ == '__main__':
    from PyInstaller.__main__ import run

    # -w 纯窗口程序, 不带命令窗口
    # --icon 可执行文件图标
    # --version-file 可执行文件的文件信息
    # --upx-dir upx加壳压缩(需要单独下载upx), 放到此文件同目录下会自动找到upx.exe(都不需要专门注明此参数)
    # -y 打包生成的文件直接覆盖上一次生成
    # --add-data: 添加数据文件. 格式为 源;目标
    #params = ['-y', '-n=UlordWallet', 'deterministic.spec']
    #run(params)

    #params = ['-y', '-n=uwallet', 'deterministic.spec']
    params = ['UpdateAppClient.py','--icon=uwallet.ico','--hidden-import=queue','-w','-y']
    run(params)
#qt5.11