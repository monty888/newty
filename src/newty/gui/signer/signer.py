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
from PySide2.QtGui import Qt, QClipboard
from PySide2.QtGui import QFont, QFontDatabase, QValidator
from PySide2.QtCore import Signal, QRegExp, QThread, Slot, QRunnable, QObject, QThreadPool, QEventLoop

from pathlib import Path
from getpass import getpass

from monstr.client.client import Client, ClientPool
from monstr.ident.keystore import SQLiteKeyStore, NIP49KeyDataEncrypter, NIP44KeyDataEncrypter, KeystoreInterface
from monstr.signing.signing import BasicKeySigner
from monstr.signing.nip46 import NIP46ServerConnection


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
                 value: str = '',
                 editable: bool = False,
                 *args, **kargs):
        super(EditableDropdownWidget, self).__init__(*args, **kargs)

        self._value = value
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
        name_lbl.setBuddy(self._sel_in)

        # set the selection if any, if we don't have any items - which at the moment as we don't support items
        # (easy add though) on creation we won't then we'll add just the single item so it can be selected and expect
        # that if there are to be other items they'll be added in time via set_items
        if self._value:
            self._sel_in.addItems([self._value])
            self._sel_in.setCurrentText(self._value)


        # add widgets to layout
        self._layout.addWidget(name_lbl, 0, 0, alignment=Qt.AlignTop)
        self._layout.addWidget(self._sel_in, 0, 1, alignment=Qt.AlignTop)

    def set_min_label_width(self, width: int ):
        self._layout.setColumnMinimumWidth(0, width)

    def set_enable(self, enabled:bool):
        self._sel_in.setEnabled(enabled)

    def set_items(self, items: [str]):
        sel_text = self._sel_in.currentText()
        self._sel_in.clear()
        self._sel_in.addItems(items)

        # keep same selected text
        if sel_text:
            self._sel_in.setCurrentText(sel_text)

    def selected_text(self):
        return self._sel_in.currentText()



class SignerGUI(QWidget):

    def __init__(self,
                 signer_args: dict = None,
                 *args, **kargs):
        super(SignerGUI, self).__init__(*args, **kargs)

        self._user: NamedKeys = None
        self._key_store: KeystoreInterface = None

        self._signer: NIP46ServerConnection = None

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
        # TODO: simple relay add/rem widget
        self._relay_in = QLineEdit(text='ws://localhost:8081')
        s_relay_lbl.setBuddy(self._relay_in)

        con1_layout.addWidget(s_relay_lbl, 1, 0, alignment=Qt.AlignTop)
        con1_layout.addWidget(self._relay_in, 1, 1, alignment=Qt.AlignTop)

        sel_name = None
        if self._user:
            sel_name = self._user.name
        self._acc_sel = EditableDropdownWidget(value=sel_name)
        self._acc_sel.set_min_label_width(min_lbl_width)

        self._layout.addWidget(self._acc_sel)
        self._layout.addWidget(con1)
        self._layout.addStretch()

        self._run_button = QPushButton('start')
        self._run_button.clicked.connect(self._run_clicked)

        self._connect_lbl = QLabel(visible=False)
        self._connect_lbl.setCursor(Qt.PointingHandCursor)
        self._connect_lbl.mousePressEvent = self._connect_str_to_clipboard

        self._layout.addWidget(self._connect_lbl)

        self._layout.addWidget(self._run_button)

        # Add a status bar at the bottom
        status_layout = QHBoxLayout()
        self._layout.addLayout(status_layout)

        self._status_label = QLabel("not running")


        # Style the status label to look like a status bar
        self._status_label.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0; /* Light grey background */
                border: 1px solid #dcdcdc; /* Light grey border */
                padding: 2px; /* Padding to make it look like a status bar */
            }
        """)
        status_layout.addWidget(self._status_label)

        self._update_user()
        self._load_accounts()

    def _load_accounts(self):
        loop = asyncio.get_event_loop()
        asyncio.ensure_future(self._aload_accounts(), loop=loop)

    def _run_clicked(self):
        run_text = self._run_button.text()
        # start or stop toggle
        if run_text == 'start':
            self._run_button.setText('stop')
            self._set_enable(False)
            self._status_label.setText('starting')

            def my_status(status):
                if status['connected'] == True:
                    self._status_label.setText('connected')
                else:
                    # give more info here
                    self._status_label.setText('connection problem')

            # self._client = ClientPool(self._relay_in.text().split(','),
            #                           on_status=my_status)
            # asyncio.create_task(self._client.run())

            async def start_signer():
                sel_user = await self._key_store.get(self._acc_sel.selected_text())


                self._signer = NIP46ServerConnection(signer=BasicKeySigner(sel_user),
                                                     relay=self._relay_in.text())
                asyncio.create_task(self._signer.run(on_status=my_status))
                self._connect_lbl.setVisible(True)
                self._connect_lbl.setText(await self._signer.bunker_url)
            asyncio.create_task(start_signer())


        else:
            self._run_button.setText('start')
            self._connect_lbl.setVisible(False)
            self._set_enable(True)
            self._signer.client.set_on_status(None)
            self._signer.end()
            self._status_label.setText('not running')
            self.adjustSize()
            # self._client.end()


    def _connect_str_to_clipboard(self, evt):
        clipboard = QApplication.clipboard()
        clipboard.setText(self._connect_lbl.text())

    def _set_enable(self, enable:bool):
        self._acc_sel.set_enable(enable)
        self._relay_in.setEnabled(enable)

    @asyncSlot()
    async def _aload_accounts(self):
        if self._key_store:
            accounts = await self._key_store.select()
            items = [c_acc.name for c_acc in accounts]
            items.sort()
            self._acc_sel.set_items(items)

    def _update_user(self):
        user_display = 'no user'
        if self._user:
            user_display = self._user.name + ' npub' + util_funcs.str_tails(self._user.public_key_bech32()[4:])
        self.setWindowTitle(f'Signer for - {user_display}')

