Getting start
===============
Before compiling, create packages: `contrib/make_packages`

Commands::

    `make theming` to make a atlas out of a list of pngs

    `make apk` to make a apk


If modules included by the project are changed, like kivy or any other modules, rebuilding is needed:

  rm -rf .buildozer/android/platform/python-for-android/dist


Notes:


To use internal storage, python-for-android must be patched with:

  git pull git@github.com:denys-duchier/python-for-android.git fix-recursive-delete
