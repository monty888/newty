import asyncio
import qasync
from qasync import asyncSlot, asyncClose, QApplication
from monstr.ident.keystore import NamedKeys
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
    QListWidgetItem

)
from PySide2.QtGui import Qt

from pathlib import Path
from getpass import getpass

from monstr.client.client import Client
from monstr.ident.keystore import SQLiteKeyStore, KeyDataEncrypter

# TMP, keystore should be passed in
WORK_DIR = f'{Path.home()}/.nostrpy/'
# filename for key store
KEY_STORE_DB_FILE = 'keystore.db'


class PasswordDialog(QDialog):

    def __init__(self,
                 *args, **kargs):

        super(PasswordDialog, self).__init__(*args, **kargs)
        self.create_gui()
        self._accepted = False

    def create_gui(self):
        self.setWindowTitle('Keystore access')
        self._layout = QVBoxLayout()
        self.setLayout(self._layout)

        self._password_txt = QLineEdit(placeholderText='password')
        self._layout.addWidget(self._password_txt)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        self._layout.addWidget(bb)

    async def ashow(self):
        # self.show()
        # while self.isVisible():
        #     await asyncio.sleep(0.1)
        loop = asyncio.get_event_loop()
        self.setModal(True)  # Make the dialog modal
        result = await loop.run_in_executor(None, self.exec_)
        return result

    @property
    def password(self) -> str:
        return self._password_txt.text()

    @asyncClose
    async def closeEvent(self, event):
        self.finished.emit(0)


# def get_sqlite_key_store(db_file, password: str = None):
#     # human alias to keys
#     # keystore for user key aliases
#     # TMP - borrowed from terminal - obvs we want to show a dialog
#     async def get_key() -> str:
#         ret = password
#         if password is None:
#             future = asyncio.Future()
#             dialog = PasswordDialog()
#             dialog.finished.connect(lambda r: future.set_result(r))
#             dialog.show()
#             await future
#             dialog.hide()
#             return ''
#         return ret
#
#     key_enc = KeyDataEncrypter(get_key=get_key)
#     return SQLiteKeyStore(file_name=db_file,
#                           encrypter=key_enc)


class AccountManager(QWidget):

    def __init__(self,
                 *args, **kargs):

        super(AccountManager, self).__init__(*args, **kargs)

        self.create_gui()
        self._key_store = self.get_sqlite_key_store(db_file=WORK_DIR + KEY_STORE_DB_FILE)

        self.setFixedWidth(400)
        self.setFixedHeight(200)
        self.show()
        self._password_dialog = PasswordDialog(parent=self)

        # self.btn_fetch = QPushButton("Fetch", self)
        # self.btn_fetch.clicked.connect(self.on_btn_fetch_clicked)
        # self.layout().addWidget(self.btn_fetch)

        # asyncio.create_task(self.run())

    def create_gui(self):
        self.setWindowTitle('Account management')
        self._layout = QVBoxLayout()
        self.setLayout(self._layout)
        self._acc_list = QListWidget()
        # self._url_text = QLineEdit(placeholderText='something')
        self._layout.addWidget(self._acc_list)

    def closeEvent(self, event):
        self._run = False
        self._password_dialog.close()

    def get_sqlite_key_store(self, db_file: str, password: str = None):
        # human alias to keys
        # keystore for user key aliases
        # TMP - borrowed from terminal - obvs we want to show a dialog
        async def get_key() -> str:
            ret = password
            if password is None:
                self.setDisabled(True)
                self._password_dialog.setEnabled(True)
                if await self._password_dialog.ashow():
                    ret = self._password_dialog.password
                else:
                    ret = ''
                self.setDisabled(False)
                return ret

            return ret

        key_enc = KeyDataEncrypter(get_key=get_key)
        return SQLiteKeyStore(file_name=db_file,
                              encrypter=key_enc)

    async def ashow(self):
        try:
            accounts = await self._key_store.select()
            c_acc: NamedKeys
            for c_acc in accounts:
                item = QListWidgetItem(util_funcs.str_tails(c_acc.public_key_hex()).ljust(20) + c_acc.name.ljust(44))
                self._acc_list.addItem(item)

            while self.isVisible():
                # print('runnming')
                await asyncio.sleep(0.1)
            print('we closed!!')

        except Exception as e:
            print(e)
            self.hide()




