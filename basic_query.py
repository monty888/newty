import asyncio
import functools
import logging
import sys
from datetime import datetime
from asyncio.locks import BoundedSemaphore


import aiohttp
import markdown
from monstr.event.event import Event
from monstr.client.client import Client
from monstr.client.client import QueryTimeoutException
from monstr.util import util_funcs
from monstr.entities import Entities
from monstr.event.event_handlers import EventHandler
from monstr.client.event_handlers import LastEventHandler
from monstr.ident.event_handlers import NetworkedProfileEventHandler
from monstr.encrypt import Keys
import qasync
from qasync import asyncSlot, asyncClose, QApplication


# from PyQt5.QtWidgets import (
from PySide2.QtWidgets import (
    QWidget,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QVBoxLayout,
    QFormLayout,
    QHBoxLayout,
    QComboBox,
    QDateTimeEdit,
    QCheckBox,
    QSpinBox,
    QSizePolicy,
    QMainWindow,
    QScrollBar,
    QTextBrowser
)

from PySide2.QtCore import (
    QPoint
)

from PySide2.QtGui import (
    QTextCursor,
    QTextBlock,
    QTextBlockFormat
)


DEFAULT_URL = 'ws://localhost:8081'

class QueryEventHandlerText(EventHandler):

    def __init__(self,
                 textarea: QTextEdit,
                 text_func,
                 profile_handler = None):
        self._text_area = textarea
        self._text_func = text_func
        self._profile_handler: NetworkedProfileEventHandler = profile_handler

        self._wait_lock = BoundedSemaphore()

        super().__init__()

    def do_event(self, the_client: Client, sub_id, evt: Event):
        # TODO: probably we can get out of order draws, add some sort of lock...
        # we need to go async for profile fetches
        asyncio.create_task(self.ado_event(the_client, sub_id, evt))

    async def ado_event(self, the_client: Client, sub_id, evt: Event):
        async with self._wait_lock:
            c_evt: Event
            is_eose = True

            # we always get single events except via eose
            if isinstance(evt, Event):
                evt = [evt]
                is_eose = False


            # if we have one try to get the profile_handler to fetch profiles
            if self._profile_handler:
                pub_ks = [c_evt.pub_key
                          for c_evt in evt]

                await self._profile_handler.aget_profiles(pub_ks=pub_ks,
                                                          create_missing=True)

            # TODO add acceptance
            txt_arr = [await self._text_func(c_evt, self._profile_handler)
                       for c_evt in evt]

            the_text = ''.join(txt_arr)

            # wsa eose which means its a new q so just overwrite everything
            if is_eose:
                self._text_area.setHtml(the_text)
            # insert at the top
            else:
                my_cursor = self._text_area.textCursor()
                my_cursor.setPosition(0)
                self._text_area.setTextCursor(my_cursor)

                self._text_area.insertHtml(await self._text_func(evt[0], self._profile_handler))


class QueryFilterDate(QWidget):

    def __init__(self, init_date: datetime = None, day_point='now'):
        super().__init__()
        self._layout = QHBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)

        if init_date is None:
            init_date = datetime.now()
            if day_point == 'start':
                init_date = init_date.replace(hour=0,minute=0, second=0, microsecond=0)
            elif day_point == 'end':
                init_date = init_date.replace(hour=23,minute=59, second=59,microsecond=999)

        self._date_edit = QDateTimeEdit(enabled=False)
        self._date_edit.setDateTime(init_date)

        self._layout.addWidget(self._date_edit)

        self._enable_check = QCheckBox('enable')
        self._enable_check.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed))
        self._layout.addWidget(self._enable_check)

        # attach events
        self._enable_check.stateChanged.connect(self._on_enabled_changed)

    @asyncSlot()
    async def _on_enabled_changed(self, state):
        self._date_edit.setEnabled(state)

    def value(self):
        ret = None
        if self._enable_check.isChecked():
            ret = self._date_edit.dateTime().toPython()
        return ret


class QueryWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setCentralWidget(MainWindow())


class MyTextEdit(QTextEdit):

    def __init__(self, *args, **kargs):
        super(MyTextEdit, self).__init__(*args, **kargs)
        self.document()

        self._block_lookup = set()


    def mousePressEvent(self, e):
        fpos = e.localPos()

        pos = QPoint(int(fpos.x()), int(fpos.y()))

        cursor = self.cursorForPosition(pos)

        colN = cursor.positionInBlock()

        print('>>>>',cursor.block().text() in self._block_lookup)
        print(cursor.block().text())


    def insertHtml(self, text:str) -> None:
        self.textCursor().insertHtml(text)

        self._block_lookup.add(self.textCursor().block().text())





class MyTextBrowser(QTextBrowser):

    def __init__(self, *args, **kargs):
        super(MyTextBrowser, self).__init__(*args, **kargs)

    def mousePressEvent(self, e):
        fpos = e.localPos()

        pos = QPoint(int(fpos.x()), int(fpos.y()))

        cursor = self.cursorForPosition(pos)

        colN = cursor.positionInBlock()

        print(cursor.block().blockFormat())

        print('MOTHER FUCKER!!!')


class MainWindow(QWidget):
    """Main window."""

    def __init__(self):
        super().__init__()

        self._my_title = 'newty query'
        self._run_status = 'stopped'

        self.setWindowTitle(self._my_title)

        self._layout = QVBoxLayout()
        self.setLayout(self._layout)

        self._form_con = QWidget()
        self._form_layout = QFormLayout()
        self._form_con.setLayout(self._form_layout)

        # self._run_status = QLabel('stopped')
        # self._layout.addWidget(self._run_status)

        self._query_relay_url = QLineEdit(DEFAULT_URL)
        self._form_layout.addRow('relay url', self._query_relay_url)

        self._query_kinds = QLineEdit('')
        self._form_layout.addRow('kinds', self._query_kinds)

        self._query_authors_pane = QWidget()
        self._query_authors_pane_layout = QHBoxLayout()
        self._query_authors_pane_layout.setContentsMargins(0, 0, 0, 0)
        self._query_authors_pane.setLayout(self._query_authors_pane_layout)
        self._query_authors = QLineEdit('')
        self._query_authors_pane_layout.addWidget(self._query_authors)
        self._query_authors_sel_but = QPushButton('select')
        self._query_authors_pane_layout.addWidget(self._query_authors_sel_but)
        self._query_authors_sel_but.clicked.connect(self._open_authors_select)
        self._author_select_dialog = None

        self._form_layout.addRow('authors', self._query_authors_pane)

        self._query_ids = QLineEdit('')
        self._form_layout.addRow('ids', self._query_ids)

        self._query_e_tags = QLineEdit('')
        self._form_layout.addRow('#e', self._query_e_tags)

        self._query_hash_tags = QLineEdit('')
        self._form_layout.addRow('hash tags', self._query_hash_tags)

        self._query_limit = QSpinBox(value=20)
        self._form_layout.addRow('limit', self._query_limit)

        self._query_since = QueryFilterDate(day_point='start')
        self._form_layout.addRow('since', self._query_since)

        self._query_until = QueryFilterDate()
        self._form_layout.addRow('until', self._query_until)

        self._output_style = QComboBox()
        self._output_style.addItem('json')
        self._output_style.addItem('truncated text')
        self._output_style.addItem('full text')

        self._form_layout.addRow('output', self._output_style)

        self._keep_alive = QCheckBox('keep alive', self)
        self._form_layout.addRow(None, self._keep_alive)


        self._layout.addWidget(self._form_con)

        self._status_lbl = QLabel(self._run_status)
        self._form_layout.addRow('status', self._status_lbl)

        self._btnFetch = QPushButton("Fetch", self)
        self._btnFetch.clicked.connect(self.on_btnFetch_clicked)
        self._layout.addWidget(self._btnFetch)

        self._text_help = QTextEdit('', readOnly=True)


        # self._response_text = MyTextBrowser()
        self._response_text = MyTextEdit('', readOnly=True)

        self._response_text_vscroll = self._response_text.verticalScrollBar()

        self._response_text_vscroll.valueChanged.connect(self.on_text_scroll)
        self._at_top = True


        self._layout.addWidget(self._response_text)

        # client for running the queries
        self._query_client: Client = None
        self._query_running = False

        self._background_client = Client('wss://nos.lol')


        # hmmmm ...
        from my_tester import SeenProfiles
        self._client = Client('wss://nos.lol')
        self._profile_handler = NetworkedProfileEventHandler(client=self._client)

        self._seen_profiles = SeenProfiles()
        self._client.subscribe(handlers=self._seen_profiles,
                               filters={
                                   'kinds': [Event.KIND_TEXT_NOTE]
                               })

        self._select_user_dialog = None

        asyncio.create_task(self._client.run())




    def _test_add_menu(self):
        # self.add
        pass


    # @asyncSlot()
    def _open_authors_select(self):
        from my_tester import SelectUser
        self._select_user_dialog = SelectUser(track_seen=self._seen_profiles,
                                              profile_handler=self._profile_handler)
        # await self.exec_QDialog_async(SelectUser(track_seen=self._seen_profiles))

        self._select_user_dialog.accepted.connect(self._authors_accepted)
        self._select_user_dialog.exec_()

    @asyncSlot()
    async def _authors_accepted(self):
        self._query_authors.setText(','.join(self._select_user_dialog.selected_keys))
        self._select_user_dialog = None


    @asyncClose
    async def closeEvent(self, event):
        if self._query_client:
            self._query_client.end()

    # def updateTitle(self) -> None:
    #     super().setWindowTitle(f'{self._my_title} - {self._run_status}')

    def update_status(self):
        self._status_lbl.setText(self._run_status)

    def _set_run_status(self, status: str):
        self._run_status = status
        self.update_status()


    @staticmethod
    def _get_hex_fields(txt: str, for_field: str, max_length: int = 64) -> []:
        # helper function for extracting npub, nnote, hex type fields
        # do we ever expect anything other than max 64?..
        ret = []
        for c_v in txt.split(','):
            to_add = c_v
            if util_funcs.is_hex_part(c_v, max_length=max_length) is False:
                to_add = Entities.decode(c_v)

            if to_add is None:
                raise ValueError(f'bad value for {for_field} - {c_v}')
            ret.append(to_add)
        return ret

    def _get_query_values(self):
        outputs = {
            'json': self._json_event_print,
            'truncated text': self._basic_event_print,
            'full text': self._basic_event_print
        }

        ret = {
            'query_url': self._query_relay_url.text(),
            'filter': {},
            'output': outputs[self._output_style.currentText()],
            'keep_alive': self._keep_alive.isChecked()
        }

        kinds = self._query_kinds.text().strip()
        if kinds:
            ret['filter']['kinds'] = [int(i) for i in kinds.split(',')]

        authors = self._query_authors.text().strip()
        if authors:
            ret['filter']['authors'] = self._get_hex_fields(authors, 'authors')

        ids = self._query_ids.text().strip()
        if ids:
            ret['filter']['ids'] = self._get_hex_fields(ids, 'ids')

        e_tags = self._query_e_tags.text().strip()
        if e_tags:
            ret['filter']['#e'] = self._get_hex_fields(e_tags, '#e')

        hash_tags = self._query_hash_tags.text().strip()
        if hash_tags:
            ret['filter']['#t'] = hash_tags.split(',')

        since = self._query_since.value()
        if since:
            ret['filter']['since'] = util_funcs.date_as_ticks(since)

        until = self._query_until.value()
        if until:
            ret['filter']['until'] = util_funcs.date_as_ticks(until)

        ret['filter']['limit'] = self._query_limit.value()

        logging.info(f'MainWindow::_get_query_values filter = {ret["filter"]}')

        return ret

    async def _basic_event_print(self, evt: Event, profile_handler:NetworkedProfileEventHandler=None, **kargs) -> str:

        content = evt.content
        user = util_funcs.str_tails(evt.pub_key)
        if profile_handler and profile_handler.have_profile(evt.pub_key):
            user = (await profile_handler.aget_profile(evt.pub_key)).display_name()

        return f'<div><span style="color:blue">{user}</span>@{evt.created_at}</div>{content}<br>'

    async def _json_event_print(self, evt: Event, profile_handler=None, **kargs) -> str:
        return str(evt.event_data())

    def _stop_runnning_query(self):
        self._query_client.end()
        self._btnFetch.setText('Fetch')

    @asyncSlot()
    async def on_text_scroll(self):
        pos = self._response_text_vscroll.value()
        self._at_top = pos == 0
        if self._at_top:
            print('we can draw new events now')

        # elif pos == self._response_text_vscroll.maximum():
        #     print('at limits')

    @asyncSlot()
    async def on_btnFetch_clicked(self):
        if self._btnFetch.text() == 'Stop':
            self._stop_runnning_query()
            return

        self._btnFetch.setEnabled(False)
        self._set_run_status('running')

        try:
            use_values = self._get_query_values()
            # self.editResponse.setHtml('<b>test</b>test<div style="color:red">very nice</div>')
            self._query_client = Client(use_values['query_url'])

            # maybe option so can see if that relay can look up profiles
            profile_handler = NetworkedProfileEventHandler(client=self._query_client)

            # this should probably be default option (IS NOW!! )
            if True:
                profile_handler = self._profile_handler


            output_handler = QueryEventHandlerText(textarea=self._response_text,
                                                   text_func=use_values['output'],
                                                   profile_handler=profile_handler)





            self._response_text.clear()

            eose_done = False
            eose_time_out = 10.0
            def my_eose(the_client, sub_id, evt):
                nonlocal eose_done
                profile_handler.do_event(the_client=self._query_client,
                                         sub_id=None,
                                         evts=evt)
                self._seen_profiles.do_event(the_client=self._query_client,
                                             sub_id=None,
                                             evt=evt)
                output_handler.do_event(the_client=self._query_client,
                                        sub_id=None,
                                        evt=evt)
                eose_done = True

            async with self._query_client:
                # note added seen profiles
                self._query_client.subscribe(handlers=[profile_handler, self._seen_profiles, output_handler],
                                       filters=use_values['filter'],
                                       eose_func=my_eose)

                wait_time = 0
                while eose_done is False:
                    await asyncio.sleep(0.1)
                    wait_time += 0.1
                    if wait_time > eose_time_out:
                        raise QueryTimeoutException('query timed out mofo!!!!')

                if use_values['keep_alive']:
                    self._set_run_status('listening')
                    self._btnFetch.setText('Stop')
                    self._btnFetch.setEnabled(True)
                    while self._query_client.running:
                        await asyncio.sleep(0.1)
                        if 'until' in use_values['filter']:
                            if util_funcs.date_as_ticks(datetime.now()) > use_values['filter']['until']:
                                self._stop_runnning_query()


        except Exception as exc:
            self._set_run_status(f'Error: {exc}')
        else:
            self._set_run_status('success')
        finally:
            self._client = None
            self._btnFetch.setEnabled(True)
        print('done')

async def main():
    def close_future(future, loop):
        loop.call_later(10, future.cancel)
        future.cancel()

    loop = asyncio.get_event_loop()
    future = asyncio.Future()

    app = QApplication.instance()
    if hasattr(app, "aboutToQuit"):
        getattr(app, "aboutToQuit").connect(
            functools.partial(close_future, future, loop)
        )

    mainWindow = QueryWindow()
    mainWindow.show()

    await future
    return True


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    try:
        qasync.run(main())
    except asyncio.exceptions.CancelledError:
        sys.exit(0)