Lightweight ulord client
=====================================

::

  Licence: MIT Licence
  Language: Python



Getting started
===============

uwallet is a pure python application. However, if you want to use the
Qt interface, then you need to install the Qt dependencies::

    sudo apt-get install python-qt4

If you downloaded the official package (tar.gz), then you can run
uwallet from its root directory, without installing it on your
system; all the python dependencies are included in the 'packages'
directory. To run uwallet from its root directory, just do::

    ./uwallet

If you cloned the git repository, then you need to compile extra files
before you can run uwallet. Read the next section, "Development
Version".



Development version
===================

Run install (this should install dependencies)::

    python setup.py install

Compile the icons file for Qt::

    sudo apt-get install pyqt4-dev-tools
    pyrcc4 icons.qrc -o gui/qt/icons_rc.py

Compile the protobuf description file::

    sudo apt-get install protobuf-compiler
    protoc --proto_path=lib/ --python_out=lib/ lib/paymentrequest.proto

Create translations::

    sudo apt-get install python-pycurl gettext
    ./contrib/make_locale



Install on Linux systems
========================

If you install uwallet on your system, you can run it from any
directory.



If you don't have pip, install with::

    python setup.py sdist
    sudo python setup.py install



Creating Binaries
=================


In order to create binaries, you must create the 'packages' directory::

    ./contrib/make_packages

This directory contains the python dependencies used by uwallet.


Windows
-------

See `contrib/build-wine/README` file.


Android
-------

See `gui/kivy/Readme.txt` file.
