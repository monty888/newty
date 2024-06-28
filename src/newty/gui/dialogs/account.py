import asyncio
import qasync
from PySide2.QtCore import QSize
from qasync import asyncSlot, asyncClose, QApplication
from monstr.ident.keystore import NamedKeys
from monstr.encrypt import Keys
from monstr.util import util_funcs
import PySide2
# from PyQt5.QtWidgets import (
from PySide2.QtWidgets import (
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QMainWindow,
    QDialog,
    QDialogButtonBox,
    QListView,
    QAbstractItemView,
    QTabWidget,
    QListWidget,
    QListWidgetItem, QGridLayout, QSizePolicy, QFrame, QTextEdit

)
from PySide2.QtGui import Qt
from PySide2.QtGui import QFont, QFontDatabase, QValidator
from PySide2.QtCore import Signal, QRegExp

from pathlib import Path
from getpass import getpass

from monstr.client.client import Client
from monstr.ident.keystore import SQLiteKeyStore, KeyDataEncrypter

# TMP, keystore should be passed in
WORK_DIR = f'{Path.home()}/.nostrpy/'
# filename for key store
KEY_STORE_DB_FILE = 'keystore.db'


# class PasswordDialog(QDialog):
#
#     def __init__(self,
#                  *args, **kargs):
#
#         super(PasswordDialog, self).__init__(*args, **kargs)
#         self.create_gui()
#         self._accepted = False
#
#     def create_gui(self):
#         self.setWindowTitle('Keystore access')
#         self._layout = QVBoxLayout()
#         self.setLayout(self._layout)
#
#         self._password_txt = QLineEdit(placeholderText='password')
#         self._layout.addWidget(self._password_txt)
#
#         bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
#
#         bb.accepted.connect(self.accept)
#         bb.rejected.connect(self.reject)
#         self._layout.addWidget(bb)
#
#     async def ashow(self):
#         # self.show()
#         # while self.isVisible():
#         #     await asyncio.sleep(0.1)
#         loop = asyncio.get_event_loop()
#         self.setModal(True)  # Make the dialog modal
#         result = await loop.run_in_executor(None, self.exec_)
#         return result
#
#     @property
#     def password(self) -> str:
#         return self._password_txt.text()
#
#     @asyncClose
#     async def closeEvent(self, event):
#         self.finished.emit(0)

class ClickableLabel(QLabel):
    clicked = Signal()

    def __init__(self,
                 *args, **kargs):
        super(ClickableLabel, self).__init__(*args, **kargs)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()


# class ClickableLineEdit(QLineEdit):
#     clicked = Signal()
#
#     def __init__(self,
#                  *args, **kargs):
#         super(ClickableLineEdit, self).__init__(*args, **kargs)
#         # done slightly different to label as we want to get the clicks when the input is disabled
#         self.installEventFilter(self)
#
#     def eventFilter(self, source, event):
#         if event.type() == event.MouseButtonPress and source == self:
#             # only when disabled, assume when enabled we'd always just want normal input actions?
#             if not self.isEnabled() and event.button() == Qt.LeftButton:
#                 self.clicked.emit()
#                 return True
#         return super().eventFilter(source, event)


class SimpleTextValidator(QValidator):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.allowed_characters = QRegExp("[a-zA-Z0-9_]+")  # Allow letters, digits, and underscore

    def validate(self, input_str, pos):
        if self.allowed_characters.exactMatch(input_str):
            return self.Acceptable, input_str, pos
        elif input_str == "":
            return self.Intermediate, input_str, pos
        else:
            return self.Invalid, input_str, pos


# class KeyTextValidator(QValidator):
#     def __init__(self, parent=None):
#         super().__init__(parent)
#
#         self.allowed_prefix = QRegExp("[npuscNPUSC0-9A-Fa-f]+")
#         self.allowed_key = QRegExp("[0-9A-Fa-f]+")
#
#     def validate(self, input_str, pos):
#         prefix = input_str[:4]
#         the_rest = input_str[4:]
#         print('a',self.allowed_prefix.exactMatch(prefix), prefix)
#         print('b',self.allowed_key.exactMatch(the_rest), the_rest)
#
#         if self.allowed_prefix.exactMatch(prefix) and (the_rest=='' or self.allowed_key.exactMatch(the_rest)):
#             return self.Acceptable, input_str, pos
#         elif input_str == "":
#             return self.Intermediate, input_str, pos
#         else:
#             return self.Invalid, input_str, pos


class NewAccountDialog(QDialog):

    OP_GEN_NEW = 'generate new'
    OP_EXISTING = 'existing nsec/npub'

    def __init__(self,
                 *args, **kargs):

        super(NewAccountDialog, self).__init__(*args, **kargs)
        self.setMinimumWidth(610)
        self.create_gui()
        self._generated_keys = None
        self._regen_key()
        self._setView()

    def create_gui(self):
        self.setWindowTitle('Add account')
        self._layout = QVBoxLayout()
        self.setLayout(self._layout)

        # account name and entry type drop down
        con1 = QWidget()
        con1_layout = QGridLayout()
        con1_layout.setContentsMargins(0, 0, 0, 0)
        con1_layout.setColumnStretch(1, 2)
        con1_layout.setColumnMinimumWidth(0, 80)
        con1.setLayout(con1_layout)

        name_lbl = QLabel('name')
        self._name_in = QLineEdit(validator=SimpleTextValidator())
        name_lbl.setBuddy(self._name_in)
        con1_layout.addWidget(name_lbl, 0, 0, alignment=Qt.AlignTop)
        con1_layout.addWidget(self._name_in, 0, 1, alignment=Qt.AlignTop)

        type_lbl = QLabel('type')
        self._type_drop = QComboBox()
        self._type_drop.addItems([self.OP_GEN_NEW,
                                  self.OP_EXISTING])
        self._type_drop.currentIndexChanged.connect(self._type_changed)

        type_lbl.setBuddy(self._type_drop)
        con1_layout.addWidget(type_lbl, 1, 0, alignment=Qt.AlignTop)
        con1_layout.addWidget(self._type_drop, 1, 1, alignment=Qt.AlignTop)

        self._layout.addWidget(con1)

        # nsec and npub entry - nsec only editable if existing nsec
        # clicking either when in generate mode should randomly generate another key
        con2 = QWidget()
        con2_layout = QGridLayout()
        con2_layout.setContentsMargins(0, 0, 0, 0)
        con2_layout.setColumnStretch(1, 2)
        con2_layout.setColumnMinimumWidth(0, 80)
        con2.setLayout(con2_layout)

        mono_font = QFontDatabase.systemFont(QFontDatabase.FixedFont)

        # lbl style nsec - shows if gen new
        self._nsec_lbl = ClickableLabel('nsec')
        self._nsec_val = ClickableLabel(font=mono_font)
        self._nsec_lbl.setBuddy(self._nsec_val)

        con2_layout.addWidget(self._nsec_lbl, 0, 0, alignment=Qt.AlignTop)
        con2_layout.addWidget(self._nsec_val, 0, 1, alignment=Qt.AlignTop)

        # nsec/npub entry - shows if enter existing
        self._nsec_npub_in_lbl = ClickableLabel('nsec/npub', visible=False)
        self._nsec_npub_val = QLineEdit(font=mono_font, visible=False)
        self._nsec_npub_in_lbl.setBuddy(self._nsec_npub_val)

        con2_layout.addWidget(self._nsec_npub_in_lbl, 1, 0, alignment=Qt.AlignTop)
        con2_layout.addWidget(self._nsec_npub_val, 1, 1, alignment=Qt.AlignTop)

        npub_lbl = ClickableLabel('npub')
        self._npub_val = ClickableLabel('', font=mono_font)
        npub_lbl.setBuddy(self._npub_val)
        con2_layout.addWidget(npub_lbl, 2, 0, alignment=Qt.AlignTop)
        con2_layout.addWidget(self._npub_val, 2, 1, alignment=Qt.AlignTop)

        # add events  as needed to inputs
        self._name_in.textChanged.connect(self._setView)
        self._nsec_lbl.clicked.connect(self._regen_key)
        self._nsec_val.clicked.connect(self._regen_key)
        npub_lbl.clicked.connect(self._regen_key)
        self._npub_val.clicked.connect(self._regen_key)
        self._nsec_npub_val.textChanged.connect(self._key_input_changed)

        self._layout.addWidget(con2)

        # add the option buts
        self._diag_buts = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._ok_but = self._diag_buts.button(QDialogButtonBox.Ok)
        self._diag_buts.accepted.connect(self.accept)
        self._diag_buts.rejected.connect(self.reject)
        self._layout.addWidget(self._diag_buts)

    def _have_valid_name(self) -> bool:
        c_name = self._name_in.text()
        ret = False
        if c_name != '':
            ret = True
        return ret

    def _have_valid_key(self) -> bool:
        is_gen = self.OP_GEN_NEW == self._type_drop.currentText()
        if is_gen:
            ret = True
        else:
            ret = Keys.get_key(self._nsec_npub_val.text()) is not None

        return ret

    def _setView(self):
        is_gen = self.OP_GEN_NEW == self._type_drop.currentText()
        self._nsec_lbl.setVisible(is_gen)
        self._nsec_val.setVisible(is_gen)
        self._nsec_npub_in_lbl.setVisible(not is_gen)
        self._nsec_npub_val.setVisible(not is_gen)
        self._ok_but.setEnabled(self._have_valid_name() and self._have_valid_key())

        self.adjustSize()

    def _regen_key(self):
        if self.OP_GEN_NEW == self._type_drop.currentText():
            self._generated_keys = Keys()
            self._nsec_val.setText(self._generated_keys.private_key_bech32())
            self._npub_val.setText(self._generated_keys.public_key_bech32())

    def _key_input_changed(self, new_text):
        npub = Keys.get_key(new_text)
        if npub is None:
            self._npub_val.setText('not a valid key')
        elif npub.private_key_hex() is None:
            self._npub_val.setText('public key only')
        else:
            self._npub_val.setText(npub.public_key_bech32())
        self._setView()

    async def ashow(self):
        # self.show()
        # while self.isVisible():
        #     await asyncio.sleep(0.1)
        loop = asyncio.get_event_loop()
        self.setModal(True)  # Make the dialog modal
        result = await loop.run_in_executor(None, self.exec_)
        return result

    def _type_changed(self):
        if self.OP_EXISTING == self._type_drop.currentText():
            self._nsec_val.setText('')
            self._key_input_changed('')
        else:
            self._regen_key()

        self._setView()

    @property
    def account(self) -> NamedKeys:
        # safe only if user clicked ok to exit dialog
        if self.OP_EXISTING == self._type_drop.currentText():
            nk = Keys.get_key(self._nsec_npub_val.text())
        else:
            nk = Keys.get_key(self._nsec_val.text())
        return NamedKeys(name=self._name_in.text(),
                         priv_k=nk.private_key_hex(),
                         pub_k=nk.public_key_hex())

    @asyncClose
    async def closeEvent(self, event):
        self.finished.emit(0)


class ToggleLabel(ClickableLabel):
    def __init__(self,
                 *args, **kargs):
        super(ClickableLabel, self).__init__(*args, **kargs)

        self._view_idx = 0
        self._values = []

    @property
    def values(self) -> list:
        return self._values

    @values.setter
    def values(self, values: list):
        self._values = values
        self._view_idx  = 0
        self.setText(self._values[0])

    def toggle(self):
        self._view_idx += 1
        if self._view_idx >= len(self._values):
            self._view_idx = 0
        self.setText(self._values[self._view_idx])


class AccountViewBasic(QWidget):

    def __init__(self,
                 *args, **kargs):
        super(AccountViewBasic, self).__init__(*args, **kargs)

        self._account: NamedKeys = None
        # self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        # self.sizePolicy().se
        self.create_gui()

    def create_gui(self):
        self._layout = QVBoxLayout()
        self.setLayout(self._layout)
        self._layout.setContentsMargins(0,0,0,0)

        self._no_selection_pane = QWidget()
        self._no_selection_pane_layout = QVBoxLayout()
        self._no_selection_pane_layout.setContentsMargins(0,0,0,0)
        self._no_selection_pane.setLayout(self._no_selection_pane_layout)
        self._layout.addWidget(self._no_selection_pane)
        self._no_selection_pane_layout.addWidget(QLabel('no account selected'))

        self._no_profile_pane = QWidget(visible=False)
        self._no_profile_pane_layout = QVBoxLayout()
        self._no_profile_pane_layout.setContentsMargins(0, 0, 0, 0)
        self._no_profile_pane.setLayout(self._no_profile_pane_layout)
        self._layout.addWidget(self._no_profile_pane)

        font = QFont()
        font.setBold(True)
        self._profile_name_lbl = QLabel()
        self._profile_name_lbl.setFont(font)
        self._no_profile_pane_layout.addWidget(self._profile_name_lbl)
        self._profile_pub_k_lbl = ToggleLabel()
        self._profile_pub_k_lbl.clicked.connect(self._key_clicked)
        self._no_profile_pane_layout.addWidget(self._profile_pub_k_lbl)


        #
        #
        # self._with_profile_pane = QWidget(visible=False)
        # self.setMaximumSize(self.sizeHint())

    def _key_clicked(self):
        self._profile_pub_k_lbl.toggle()

    def sizeHint(self):
        return self._layout.sizeHint()

    @property
    def account(self) -> NamedKeys:
        return self._pub_k

    @account.setter
    def account(self, account: NamedKeys):
        self._account = account
        if account is None:
            self._no_selection_pane.setVisible(True)
            self._no_profile_pane.setVisible(False)
        else:
            self._profile_name_lbl.setText(account.name)
            self._profile_pub_k_lbl.setText(account.public_key_hex())
            self._profile_pub_k_lbl.values = [account.public_key_hex(),
                                              account.public_key_bech32()]
            self._no_selection_pane.setVisible(False)
            self._no_profile_pane.setVisible(True)


class AccountManager(QWidget):

    def __init__(self,
                 *args, **kargs):

        super(AccountManager, self).__init__(*args, **kargs)

        self.create_gui()

        self._key_store = None
        self._relist_accounts = True

        async def get_key() -> str:
            self._relist_accounts = True
            return self._password_in.text()
        self._key_enc = KeyDataEncrypter(get_key=get_key)
        self._key_store = SQLiteKeyStore(file_name=WORK_DIR+ KEY_STORE_DB_FILE,
                                         encrypter=self._key_enc)

        self.setFixedWidth(600)
        self.setFixedHeight(480)
        self.show()
        self._new_acc_dialog = NewAccountDialog(parent=self)

        # self.btn_fetch = QPushButton("Fetch", self)
        # self.btn_fetch.clicked.connect(self.on_btn_fetch_clicked)
        # self.layout().addWidget(self.btn_fetch)

        # asyncio.create_task(self.run())

    def create_gui(self):
        mono_font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        self.setWindowTitle('Account management')
        self._layout = QVBoxLayout()
        self.setLayout(self._layout)
        self._tabs = QTabWidget()
        self._tabs.currentChanged.connect(self._tabs_changed)

        tab1 = QWidget()
        tab1_layout = QVBoxLayout()
        tab1.setLayout(tab1_layout)

        settings_con = QWidget()
        settings_con_layout = QGridLayout()
        settings_con_layout.setColumnStretch(1, 2)
        settings_con_layout.setColumnMinimumWidth(0, 140)
        settings_con.setLayout(settings_con_layout)

        file_lbl = QLabel('file')
        file = QLineEdit()
        file_lbl.setBuddy(file)
        settings_con_layout.addWidget(file_lbl,0,0, alignment=Qt.AlignTop)
        settings_con_layout.addWidget(file,0,1, alignment=Qt.AlignTop)

        password_lbl = QLabel('password')
        self._password_in = password = QLineEdit()
        self._password_in.textChanged.connect(self._password_changed)
        password_lbl.setBuddy(file)
        settings_con_layout.addWidget(password_lbl, 1, 0, alignment=Qt.AlignTop)
        settings_con_layout.addWidget(password, 1, 1, alignment=Qt.AlignTop)

        tab1_layout.addWidget(settings_con)
        settings_con_layout.setRowStretch(2, 1)

        self._tabs.addTab(tab1, 'settings')
        # self._url_text = QLineEdit(placeholderText='something')
        self._layout.addWidget(self._tabs)


        self._tab2 = QWidget()
        tab2_layout = QVBoxLayout()
        self._tab2.setLayout(tab2_layout)

        self._tab2_main_con = QWidget()
        tab2_main_con_layout = QVBoxLayout()
        self._tab2_main_con.setLayout(tab2_main_con_layout)
        tab2_layout.addWidget(self._tab2_main_con)
        self._tab2_err_con = QWidget()
        tab2_err_con_layout = QVBoxLayout()
        self._tab2_err_con.setLayout(tab2_err_con_layout)
        tab2_layout.addWidget(self._tab2_err_con)

        # sel_view_con = QWidget()
        # sel_view_con_layout = QVBoxLayout()
        # sel_view_con.setLayout(sel_view_con_layout)
        # sel_view_con_layout.addWidget(QLabel('about current selection'))
        self._acc_view_basic = AccountViewBasic()
        tab2_main_con_layout.addWidget(self._acc_view_basic)
        # tab2_main_con_layout.addWidget(QWidget())

        self._acc_list = QListWidget()
        self._acc_list.setFont(mono_font)
        self._acc_list.itemSelectionChanged.connect(self.account_select)
        tab2_main_con_layout.addWidget(self._acc_list)

        self._new_btn = QPushButton('New')
        self._new_btn.clicked.connect(self.new_account)
        tab2_main_con_layout.addWidget(self._new_btn)

        self._tab2_err = QLabel()
        tab2_err_con_layout.addWidget(self._tab2_err)


        self._tabs.addTab(self._tab2, 'accounts')
        # self._url_text = QLineEdit(placeholderText='something')
        self._layout.addWidget(self._tabs)

    def closeEvent(self, event):
        pass
        # self._run = False
        # self._new_acc_dialog.close()

    @asyncSlot()
    async def new_account(self):
        result = await self._new_acc_dialog.ashow()
        if result:
            await self._key_store.add(self._new_acc_dialog.account)
            # probably we should just push on end of list rather than this ...
            await self._update_account_list()

    def account_select(self):
        selected_items = self._acc_list.selectedItems()
        if selected_items:
            self._acc_view_basic.account = selected_items[0].data(Qt.UserRole)
        else:
            self._acc_view_basic.account = None

    def _password_changed(self):
        self._key_enc.clear_key()

    @asyncSlot()
    async def _tabs_changed(self, idx):
        if idx == 1:
            await self._update_account_list()

    async def _update_account_list(self):
        try:
            if self._relist_accounts:
                self._acc_list.clear()
                accounts = await self._key_store.select()
                c_acc: NamedKeys
                for c_acc in accounts:
                    item = QListWidgetItem(util_funcs.str_tails(c_acc.public_key_hex()).ljust(12) + c_acc.name)
                    item.setData(Qt.UserRole, c_acc)
                    self._acc_list.addItem(item)
            self._tab2_main_con.setDisabled(False)
            self._tab2_err_con.setVisible(False)
        except Exception as e:
            self._tab2_main_con.setDisabled(True)
            self._show_tab2_err('problem decrypting key store, bad password?')

    def _show_tab2_err(self, txt: str):
        self._tab2_err_con.setVisible(True)
        self._tab2_err.setText(txt)

    def get_sqlite_key_store(self, db_file: str, password: str = None):
        # human alias to keys
        # keystore for user key aliases
        # TMP - borrowed from terminal - obvs we want to show a dialog
        async def get_key() -> str:
            # ret = password
            # if password is None:
            #     self.setDisabled(True)
            #     self._password_dialog.setEnabled(True)
            #     if await self._password_dialog.ashow():
            #         ret = self._password_dialog.password
            #     else:
            #         ret = ''
            #     self.setDisabled(False)
            #     return ret
            return self._password_in.text()

        key_enc = KeyDataEncrypter(get_key=get_key)
        return SQLiteKeyStore(file_name=db_file,
                              encrypter=key_enc)

    async def ashow(self):
        try:


            while self.isVisible():
                # print('runnming')
                await asyncio.sleep(0.1)
            print('we closed!!')

        except Exception as e:
            print(e)
            self.hide()




