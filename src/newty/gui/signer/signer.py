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
    QListWidgetItem, QGridLayout, QSizePolicy, QFrame, QTextEdit, QTextBrowser

)
from PySide2.QtGui import Qt
from PySide2.QtGui import QFont, QFontDatabase, QValidator
from PySide2.QtCore import Signal, QRegExp, QThread, Slot, QRunnable, QObject, QThreadPool, QEventLoop

from pathlib import Path
from getpass import getpass

from monstr.client.client import Client
from monstr.ident.keystore import SQLiteKeyStore, NIP49KeyDataEncrypter, NIP44KeyDataEncrypter, KeystoreInterface


class WorkerSignals(QObject):
    finished = Signal(str)

class Worker(QObject):
    def __init__(self, func: callable):
        super().__init__()
        self.signals = WorkerSignals()
        self._func = func

    @Slot()
    def start_task(self):
        asyncio.ensure_future(self._func())

class EditableDropdownWidget(QWidget):

    def __init__(self,
                 editable: bool = False,
                 *args, **kargs):
        super(EditableDropdownWidget, self).__init__(*args, **kargs)

        self._editable = editable

        self._create_gui()

    def _create_gui(self):
        # create the layout
        self._layout = QGridLayout()
        self.setLayout(self._layout)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setColumnStretch(1, 2)

        # create lbl and combo
        name_lbl = QLabel('name')
        self._sel_in = QComboBox()
        # self._sel_in.setContentsMargins(0,0,0,0)
        self._sel_in.setEditable(self._editable)
        self._sel_in.addItems(["Option 1", "Option 2", "Option 3"])
        name_lbl.setBuddy(self._sel_in)

        # add widgets to layout
        self._layout.addWidget(name_lbl, 0, 0, alignment=Qt.AlignTop)
        self._layout.addWidget(self._sel_in, 0, 1, alignment=Qt.AlignTop)
        print('drop was created')

    def set_min_label_width(self, width: int ):
        self._layout.setColumnMinimumWidth(0, width)


class SignerGUI(QWidget):

    def __init__(self,
                 signer_args: dict = None,
                 *args, **kargs):
        super(SignerGUI, self).__init__(*args, **kargs)

        self._user: NamedKeys = None
        self._key_store: KeystoreInterface = None

        # some args were handed in, if not user will have to set everything manually
        if signer_args:
            if 'user' in signer_args:
                self._user = signer_args['user']
            if 'key_store' in signer_args:
                self._key_store = signer_args['key_store']

        self._create_gui()

    def _create_gui(self):
        self._layout = QVBoxLayout()
        self.setLayout(self._layout)

        # input lbls to get atleast this much space
        min_lbl_width = 100


        # account name and signer relay
        con1 = QWidget()
        con1_layout = QGridLayout()
        con1_layout.setContentsMargins(0, 0, 0, 0)
        con1_layout.setColumnStretch(1, 2)
        con1_layout.setColumnMinimumWidth(0, min_lbl_width)
        con1.setLayout(con1_layout)

        s_relay_lbl = QLabel('signing relay(s)')
        self._relay_in = QLineEdit()
        s_relay_lbl.setBuddy(self._relay_in)

        con1_layout.addWidget(s_relay_lbl, 1, 0, alignment=Qt.AlignTop)
        con1_layout.addWidget(self._relay_in, 1, 1, alignment=Qt.AlignTop)

        my_drop = EditableDropdownWidget()
        my_drop.set_min_label_width(min_lbl_width)

        self._layout.addWidget(my_drop)
        self._layout.addWidget(con1)
        self._layout.addStretch()
        self._update_user()
        self._load_accounts()

    def _load_accounts(self):
        loop = asyncio.get_event_loop()
        asyncio.ensure_future(self._aload_accounts(), loop=loop)

    @asyncSlot()
    async def _aload_accounts(self):
        if self._key_store:
            accounts = await self._key_store.select()
            print('LOADED ACCOUNTS!!!!!!', len(accounts))

    def _update_user(self):
        user_display = 'no user'
        if self._user:
            user_display = self._user.name + ' npub' + util_funcs.str_tails(self._user.public_key_bech32()[4:])
        self.setWindowTitle(f'Signer for - {user_display}')

