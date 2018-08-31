# -*- coding: utf-8 -*-
import sys
import os

from PyQt4.QtGui import *
from PyQt4.QtCore import *
import PyQt4.QtCore as QtCore

import uwallet
from uwallet.wallet import Wallet
from uwallet.util import UserCancelled
from uwallet.base_wizard import BaseWizard
from uwallet.i18n import _

from seed_dialog import SeedDisplayLayout, CreateSeedLayout, SeedInputLayout, TextInputLayout
from network_dialog import NetworkChoiceLayout
from util import *
from password_dialog import PasswordLayout, PW_NEW


class GoBack(Exception):
    pass

MSG_GENERATING_WAIT = _("UWalletLite is generating your addresses, please wait...")
MSG_ENTER_ANYTHING = _("Please enter a seed phrase, a master key, a list of "
                       "Ulord addresses, or a list of private keys")
MSG_ENTER_SEED_OR_MPK = _("Please enter a seed phrase or a master key (xpub or xprv):")
MSG_COSIGNER = _("Please enter the root public key of cosigner #%d:")
MSG_ENTER_PASSWORD = _("Choose a password to encrypt your wallet keys.") + '\n'\
                     + _("Leave this field empty if you want to disable encryption.")
MSG_RESTORE_PASSPHRASE = \
    _("Please enter your seed derivation passphrase. "
      "Note: this is NOT your encryption password. "
      "Leave this field empty if you did not use one or are unsure.")


class CosignWidget(QWidget):
    size = 120

    def __init__(self, m, n):
        QWidget.__init__(self)
        self.R = QRect(0, 0, self.size, self.size)
        self.setGeometry(self.R)
        self.setMinimumHeight(self.size)
        self.setMaximumHeight(self.size)
        self.m = m
        self.n = n

    def set_n(self, n):
        self.n = n
        self.update()

    def set_m(self, m):
        self.m = m
        self.update()

    def paintEvent(self, event):
        import math
        bgcolor = self.palette().color(QPalette.Background)
        pen = QPen(bgcolor, 7, QtCore.Qt.SolidLine)
        qp = QPainter()
        qp.begin(self)
        qp.setPen(pen)
        qp.setRenderHint(QPainter.Antialiasing)
        qp.setBrush(Qt.gray)
        for i in range(self.n):
            alpha = int(16* 360 * i/self.n)
            alpha2 = int(16* 360 * 1/self.n)
            qp.setBrush(Qt.green if i<self.m else Qt.gray)
            qp.drawPie(self.R, alpha, alpha2)
        qp.end()



def wizard_dialog(func):
    def func_wrapper(*args, **kwargs):
        run_next = kwargs['run_next']
        wizard = args[0]
        wizard.back_button.setText(_('Back') if wizard.can_go_back() else _('Cancel'))
        try:
            out = func(*args, **kwargs)
        except GoBack:
            wizard.go_back() if wizard.can_go_back() else wizard.close()
            return
        except UserCancelled:
            return
        # if out is None:
        #    out = ()
        if type(out) is not tuple:
            out = (out,)
        # if out[0]!='not seed':
        run_next(*out)

    return func_wrapper



# WindowModalDialog must come first as it overrides show_error
class InstallWizard(QDialog, MessageBoxMixin, BaseWizard):

    def __init__(self, config, app, plugins, network, storage):

        BaseWizard.__init__(self, config, network, storage)
        QDialog.__init__(self, None)

        self.MSG_GENERATING_WAIT = _("UWalletLite is generating your addresses, please wait...")
        self.MSG_ENTER_ANYTHING = _(
            "Please enter a seed phrase, a master key, a list of Ulord addresses, or a list of private keys")
        self.MSG_ENTER_SEED_OR_MPK = _("Please enter a seed phrase or a master key (xpub or xprv):")
        self.MSG_COSIGNER = _("Please enter the root public key of cosigner #%d:")
        self.MSG_ENTER_PASSWORD = _(
            "Set your password to protect your UT.")
        self.MSG_RESTORE_PASSPHRASE = \
            _(
                "Please enter your seed derivation passphrase.Note: this is NOT your encryption password.Leave this field empty if you did not use one or are unsure.")

        self.setWindowTitle('UWalletLite  -  ' + _('Install Wizard'))
        self.app = app
        self.config = config
        f = QFile("wallet.qss")
        # f = QFile("F:\MyProject\Ulord\uwallet-client-pro\gui\qt\ui\wallet.qss")
        f.open(QFile.ReadOnly)
        styleSheet = unicode(f.readAll(), encoding='utf8')
        self.setStyleSheet(styleSheet)
        f.close()
        self.setWindowIcon(QIcon(':icons/electrum_light_icon.png'))
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setContentsMargins(15, 9, 15, 15)

        # Set for base base class
        self.plugins = plugins
        self.language_for_seed = config.get('language')
        self.setMinimumSize(600, 400)
        self.connect(self, QtCore.SIGNAL('accept'), self.accept)
        self.title = QLabel()
        self.main_widget = QWidget()
        self.back_button = QPushButton(_("Back"), self)
        self.back_button.setText(_('Back') if self.can_go_back() else _('Cancel'))
        self.next_button = QPushButton(_("Next"), self)
        self.next_button.setDefault(True)
        self.logo = QLabel()
        self.please_wait = QLabel(_("Please wait..."))
        self.please_wait.setAlignment(Qt.AlignCenter)
        self.icon_filename = None
        self.loop = QEventLoop()
        self.rejected.connect(lambda: self.loop.exit(0))
        self.back_button.clicked.connect(lambda: self.loop.exit(1))
        self.next_button.clicked.connect(lambda: self.loop.exit(2))
        outer_vbox = QVBoxLayout(self)
        self.setTitleBar(outer_vbox)
        inner_vbox = QVBoxLayout()
        inner_vbox = QVBoxLayout()
        inner_vbox.addWidget(self.title)
        inner_vbox.addWidget(self.main_widget)
        inner_vbox.addStretch(1)
        inner_vbox.addWidget(self.please_wait)
        inner_vbox.addStretch(1)
        icon_vbox = QVBoxLayout()
        icon_vbox.addWidget(self.logo)
        icon_vbox.addStretch(1)
        hbox = QHBoxLayout()
        hbox.addLayout(icon_vbox)
        hbox.addSpacing(5)
        hbox.addLayout(inner_vbox)
        hbox.setStretchFactor(inner_vbox, 1)
        outer_vbox.addLayout(hbox)
        outer_vbox.addLayout(Buttons(self.back_button, self.next_button))
        # self.set_icon(':icons/electrum.png')
        self.show()
        self.raise_()
        self.refresh_gui()  # Need for QT on MacOSX.  Lame.

    def setTitleBar(self,vbox):
        tq = QLabel('UWalletLite  -  ' + _('Install Wizard'))
        tq.setObjectName("QDialogTitle")
        tq.setStyleSheet("font-family: \"Arial\";font:bold;font-size:18px;border-bottom: 2px solid #FFD100;border-color:rgb(200,200,200);")
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

    def run_and_get_wallet(self):
        # Show network dialog if config does not exist
        if self.network:
            if self.config.get('auto_connect') is None:
                self.choose_server(self.network)

        path = self.storage.path
        if self.storage.requires_split():
            self.hide()
            msg = _("The wallet '%s' contains multiple accounts, which are no longer supported in UWalletLite 2.7.\n\n"
                    "Do you want to split your wallet into multiple files?" % path)
            if not self.question(msg):
                return
            file_list = '\n'.join(self.storage.split_accounts())
            msg = _('Your accounts have been moved to') + ':\n' + file_list + '\n\n' + _(
                'Do you want to delete the old file') + ':\n' + path
            if self.question(msg):
                os.remove(path)
                self.show_warning(_('The file was removed'))
            return

        if self.storage.requires_upgrade():
            self.hide()
            msg = _(
                "The format of your wallet '%s' must be upgraded for UWalletLite. This change will not be backward compatible" % path)
            if not self.question(msg):
                return
            self.storage.upgrade()
            self.show_warning(_('Your wallet was upgraded successfully'))
            self.wallet = Wallet(self.storage)
            self.terminate()
            return self.wallet

        action = self.storage.get_action()
        if action and action != 'new':
            self.hide()
            msg = _("The file '%s' contains an incompletely created wallet.\n"
                    "Do you want to complete its creation now?") % path
            if not self.question(msg):
                if self.question(_("Do you want to delete '%s'?") % path):
                    os.remove(path)
                    self.show_warning(_('The file was removed'))
                return
            self.show()
        if action:
            # self.wallet is set in run
            self.run(action)
            return self.wallet

    def finished(self):
        """Called in hardware client wrapper, in order to close popups."""
        return

    def on_error(self, exc_info):
        if not isinstance(exc_info[1], UserCancelled):
            traceback.print_exception(*exc_info)
            self.show_error(str(exc_info[1]))

    def set_icon(self, filename):
        prior_filename, self.icon_filename = self.icon_filename, filename
        self.logo.setPixmap(QPixmap(filename).scaledToWidth(60))
        return prior_filename

    def set_main_layout(self, layout, title=None, raise_on_cancel=True,
                        next_enabled=True):
        self.title.setText("<b>%s</b>" % title if title else "")
        self.title.setVisible(bool(title))
        # Get rid of any prior layout by assigning it to a temporary widget
        prior_layout = self.main_widget.layout()
        if prior_layout:
            QWidget().setLayout(prior_layout)
        self.main_widget.setLayout(layout)
        if _('encrypt wallet') == title:
            self.back_button.setEnabled(False)
            next_enabled = False
        else:
            self.back_button.setEnabled(True)
        self.next_button.setEnabled(next_enabled)
        if next_enabled:
            self.next_button.setFocus()
        self.main_widget.setVisible(True)
        self.please_wait.setVisible(False)
        result = self.loop.exec_()
        if not result and raise_on_cancel:
            raise UserCancelled
        if result == 1:
            raise GoBack
        self.title.setVisible(False)
        self.back_button.setEnabled(False)
        self.next_button.setEnabled(False)
        self.main_widget.setVisible(False)
        self.please_wait.setVisible(True)
        self.refresh_gui()
        return result

    def refresh_gui(self):
        # For some reason, to refresh the GUI this needs to be called twice
        self.app.processEvents()
        self.app.processEvents()

    def remove_from_recently_open(self, filename):
        self.config.remove_from_recently_open(filename)

    def text_input(self, title, message, is_valid):
        slayout = TextInputLayout(self, message, is_valid)
        self.set_main_layout(slayout.layout(), title, next_enabled=False)
        return slayout.get_text()

    def seed_input(self, title, message, is_seed):
        slayout = SeedInputLayout(self, message, is_seed)
        vbox = QVBoxLayout()
        vbox.addLayout(slayout.layout())
        if self.opt_ext or self.opt_bip39:
            vbox.addStretch(1)
            # vbox.addWidget(QLabel(_('Options') + ':'))
        if self.opt_ext:
            cb_pass = QCheckBox(_('Add a passphrase to this seed'))
            # vbox.addWidget(cb_pass)
        if self.opt_bip39:
            def f(b):
                if b:
                    msg = ' '.join([
                        '<b>' + _('Warning') + '</b>' + ': ',
                        _('BIP39 seeds may not be supported in the future.'),
                        '<br/><br/>',
                        _('As technology matures, Ulord address generation may change.'),
                        _('However, BIP39 seeds do not include a version number.'),
                        _('As a result, it is not possible to infer your wallet type from a BIP39 seed.'),
                        '<br/><br/>',
                        _('We do not guarantee that BIP39 seeds will be supported in future versions of UWalletLite.'),
                        _('We recommend to use seeds generated by UWalletLite or compatible wallets.'),
                    ])
                    # self.show_warning(msg)
                slayout.seed_type_label.setVisible(not b)
                slayout.is_seed = (lambda x: bool(x)) if b else is_seed
                slayout.on_edit()

            cb_bip39 = QCheckBox(_('BIP39 seed'))
            cb_bip39.toggled.connect(f)
            f(True)
            # vbox.addWidget(cb_bip39)
        self.set_main_layout(vbox, title, next_enabled=False)
        seed = slayout.get_seed()

        # if str(seed).split() != 12:
        #     title = "UWalletLite"
        #     text = _("Incorrect seed")
        #     icontype = "warm"
        #     qm = QMessageBoxEx(title, text, self, icontype)
        #     qm.exec_()
        #     return 'not seed'
        is_bip39 = cb_bip39.isChecked() if self.opt_bip39 else False
        is_ext = cb_pass.isChecked() if self.opt_ext else False
        return seed, True, is_ext

    def seed_input_bip39(self, title, message, is_seed):
        slayout = SeedInputLayout(self, message, is_seed)
        vbox = QVBoxLayout()
        vbox.addLayout(slayout.layout())
        if self.opt_ext or self.opt_bip39:
            vbox.addStretch(1)
            # vbox.addWidget(QLabel(_('Options') + ':'))
        if self.opt_ext:
            cb_pass = QCheckBox(_('Add a passphrase to this seed'))
            # vbox.addWidget(cb_pass)
        if self.opt_bip39:
            def f(b):
                if b:
                    msg = ' '.join([
                        '<b>' + _('Warning') + '</b>' + ': ',
                        _('BIP39 seeds may not be supported in the future.'),
                        '<br/><br/>',
                        _('As technology matures, Ulord address generation may change.'),
                        _('However, BIP39 seeds do not include a version number.'),
                        _('As a result, it is not possible to infer your wallet type from a BIP39 seed.'),
                        '<br/><br/>',
                        _('We do not guarantee that BIP39 seeds will be supported in future versions of UWalletLite.'),
                        _('We recommend to use seeds generated by UWalletLite or compatible wallets.'),
                    ])
                    # self.show_warning(msg)
                slayout.seed_type_label.setVisible(not b)
                slayout.is_seed = (lambda x: bool(x)) if b else is_seed
                slayout.on_edit()

            cb_bip39 = QCheckBox(_('BIP39 seed'))
            cb_bip39.toggled.connect(f)
            f(True)
            # vbox.addWidget(cb_bip39)
        self.set_main_layout(vbox, title, next_enabled=False)
        seed = slayout.get_seed()
        # is_bip39 = cb_bip39.isChecked() if self.opt_bip39 else False
        # is_ext = cb_pass.isChecked() if self.opt_ext else False
        # return seed, True, is_ext

    @wizard_dialog
    def add_xpub_dialog(self, title, message, is_valid, run_next):
        return self.text_input(title, message, is_valid)

    @wizard_dialog
    def add_cosigner_dialog(self, run_next, index, is_valid):
        title = _("Cosigner %d root public key")%index
        message = ' '.join([
            _('Please enter the root public key (xpub) of your cosigner.'),
            # _('Enter their master private key (xprv) if you want to be able to sign for them.')
        ])
        return self.text_input(title, message, is_valid)

    @wizard_dialog
    def restore_seed_dialog(self, run_next, test):
        title = _("Import mnemonic")
        message = _("Please enter your backup mnemonic.")
        # return self.seed_input(title, message, test)
        return self.seed_input(title, message, test)

    @wizard_dialog
    def restore_seed_dialog_bip39(self, run_next, test):
        title = _("Import mnemonic")
        message = ' '.join([
            _("Please enter your backup mnemonic."),
            # _('If you lose your seed, your money will be permanently lost.'),
            # _('To make sure that you have properly saved your seed, please retype it here.')
        ])
        return self.seed_input_bip39(title, message, test)

    @wizard_dialog
    def confirm_seed_dialog(self, run_next, test):
        self.app.clipboard().clear()
        title = _('Confirm Seed')
        message = ' '.join([
            _('Your seed is important!'),
            _('If you lose your seed, your money will be permanently lost.'),
            _('To make sure that you have properly saved your seed, please retype it here.')
        ])
        self.opt_ext = True
        self.opt_bip39 = True
        seed, is_bip39, is_ext = self.seed_input(title, message, test)
        return seed

    @wizard_dialog
    def show_seed_dialog(self, run_next, seed_text):
        vbox = QVBoxLayout()
        slayout = CreateSeedLayout(seed_text)
        vbox.addLayout(slayout.layout())
        vbox.addStretch(1)
        # vbox.addWidget(QLabel(_('Option') + ':'))
        cb_pass = QCheckBox(_('Add a passphrase to this seed'))
        # vbox.addWidget(cb_pass)
        title = _("Mnemonic")
        self.set_main_layout(vbox,title)
        return cb_pass.isChecked()

    def pw_layout(self, msg, kind):
        playout = PasswordLayout(None, msg, kind, self.next_button)
        self.set_main_layout(playout.layout(),_('encrypt wallet'))
        return playout.new_password()

    @wizard_dialog
    def request_password(self, run_next):
        """Request the user enter a new password and confirm it.
        the password or None for no password."""
        return self.pw_layout(self.MSG_ENTER_PASSWORD, PW_NEW)

    def show_restore(self, wallet, network):
        # FIXME: these messages are shown after the install wizard is
        # finished and the window closed.  On MacOSX they appear parented
        # with a re-appeared ghost install wizard window...
        if network:
            def task():
                wallet.wait_until_synchronized()
                if wallet.is_found():
                    msg = _("Recovery successful")
                else:
                    msg = _("No transactions found for this seed")
                self.emit(QtCore.SIGNAL('synchronized'), msg)

            self.connect(self, QtCore.SIGNAL('synchronized'), self.show_message)
            t = threading.Thread(target=task)
            t.daemon = True
            t.start()
        else:
            msg = _("This wallet was restored offline. It may "
                    "contain more addresses than displayed.")
            self.show_message(msg)

    @wizard_dialog
    def confirm_dialog(self, title, message, run_next):
        self.confirm(message, title)

    def confirm(self, message, title):
        vbox = QVBoxLayout()
        vbox.addWidget(WWLabel(message))
        self.set_main_layout(vbox, title)

    @wizard_dialog
    def action_dialog(self, action, run_next):
        self.run(action)

    def terminate(self):
        self.wallet.start_threads(self.network)
        self.emit(QtCore.SIGNAL('accept'))

    def waiting_dialog(self, task, msg):
        self.please_wait.setText(self.MSG_GENERATING_WAIT)
        self.refresh_gui()
        # self.please_wait.hide()
        t = threading.Thread(target=task)
        t.start()
        t.join()
#
    @wizard_dialog
    def choice_dialog(self, title, message, choices, run_next):
        c_values = map(lambda x: x[0], choices)
        if c_values[0]=='restore_from_key':
            return 'restore_from_key' #remve selection windows
        c_titles = map(lambda x: x[1], choices)
        clayout = ChoicesLayout(message, c_titles)
        vbox = QVBoxLayout()
        vbox.addLayout(clayout.layout())
        self.set_main_layout(vbox, title)
        action = c_values[clayout.selected_index()]
        return action

    def query_choice(self, msg, choices):
        """called by hardware wallets"""
        clayout = ChoicesLayout(msg, choices)
        vbox = QVBoxLayout()
        vbox.addLayout(clayout.layout())
        self.set_main_layout(vbox, '')
        return clayout.selected_index()

    @wizard_dialog
    def line_dialog(self, run_next, title, message, default, test, warning=''):
        vbox = QVBoxLayout()
        vbox.addWidget(WWLabel(message))
        line = QLineEditEx()
        line.setText(default)

        def f(text):
            self.next_button.setEnabled(test(text))

        line.textEdited.connect(f)
        vbox.addWidget(line)
        vbox.addWidget(WWLabel(warning))
        self.set_main_layout(vbox, title, next_enabled=test(default))
        return ' '.join(unicode(line.text()).split())

    @wizard_dialog
    def show_xpub_dialog(self, xpub, run_next):
        msg = ' '.join([
            _("Here is your master public key."),
            _("Please share it with your cosigners.")
        ])
        vbox = QVBoxLayout()
        layout = SeedDisplayLayout(xpub, title=msg, icon=False)
        vbox.addLayout(layout.layout())
        self.set_main_layout(vbox, _('Master Public Key'))
        return None

    def choose_server(self, network):
        title = _("UWalletLite communicates with remote servers to get information about your transactions and addresses.\r\n The servers all fulfil the same purpose only differing in hardware. In most cases you simply want to let Uwallet pick one at random.\r\nHowever if you prefer feel free to select a server manually.")
        choices = [_("Auto connect"), _("Select server manually")]
        choices_title = _("How do you want to connect to a server? ")
        clayout = ChoicesLayout(choices_title, choices)
        self.set_main_layout(clayout.layout(), title)
        auto_connect = True
        if clayout.selected_index() == 1:
            nlayout = NetworkChoiceLayout(network, self.config, wizard=True)
            if self.set_main_layout(nlayout.layout(), raise_on_cancel=False):
                nlayout.accept()
                auto_connect = False
        self.config.set_key('auto_connect', auto_connect, True)
        network.auto_connect = auto_connect

    @wizard_dialog
    def multisig_dialog(self, run_next):
        cw = CosignWidget(2, 2)
        m_edit = QSlider(Qt.Horizontal, self)
        n_edit = QSlider(Qt.Horizontal, self)
        n_edit.setMinimum(2)
        n_edit.setMaximum(15)
        m_edit.setMinimum(1)
        m_edit.setMaximum(2)
        n_edit.setValue(2)
        m_edit.setValue(2)
        n_label = QLabel()
        m_label = QLabel()
        grid = QGridLayout()
        grid.addWidget(n_label, 0, 0)
        grid.addWidget(n_edit, 0, 1)
        grid.addWidget(m_label, 1, 0)
        grid.addWidget(m_edit, 1, 1)

        def on_m(m):
            # m_label.setText('2')
            m_label.setText(_('Require %d signatures')%m)
            cw.set_m(m)
        def on_n(n):
            # n_label.setText('2')
            n_label.setText(_('From %d cosigners')%n)
            cw.set_n(n)
            m_edit.setMaximum(n)

        n_edit.valueChanged.connect(on_n)
        m_edit.valueChanged.connect(on_m)
        on_n(2)
        on_m(2)
        vbox = QVBoxLayout()
        vbox.addWidget(cw)
        vbox.addWidget(WWLabel(_("Select the number of cosigners and signatures to unlock")))
        vbox.addLayout(grid)
        self.set_main_layout(vbox, _("Set multiple signatures"))
        m = int(m_edit.value())
        n = int(n_edit.value())
        return (m, n)
