import asyncio
from functools import partial
import logging
import sys

from monstr.event.event import Event
from monstr.client.client import Client
from monstr.ident.profile import Profile
from monstr.event.event_handlers import EventHandler
from monstr.ident.event_handlers import NetworkedProfileEventHandler
import qasync
from qasync import asyncSlot, asyncClose, QApplication
from newty.util import ResourceFetcher
from newty.gui.nostr import AddressBarPane, Location, LocationSource
from newty.gui.panes.panes import ViewPane
from newty.gui.panes.event import EventViewPane
from newty.gui.panes.profile import ProfileViewPane

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
    QTabWidget
)

import PySide2.QtCore as QtCore
from PySide2.QtCore import (
    QSortFilterProxyModel
)

from PySide2.QtWebEngineWidgets import QWebEngineView

from PySide2.QtGui import (
    QStandardItem,
    QStandardItemModel,
    Qt,
    QPixmap
)

DEFAULT_URL = 'ws://localhost:8081'


class SeenProfiles(EventHandler):

    def __init__(self):
        self._seen_keys = set()

    def do_event(self, the_client: Client, sub_id, evt: Event):
        if isinstance(evt, Event):
            evt = [evt]

        for c_evt in evt:
            self._seen_keys.add(c_evt.pub_key)

    def seen(self):
        ret = list(self._seen_keys)
        ret.sort()
        return ret


class TestWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setCentralWidget(MainWindow())
        self.setWindowTitle('Testing stuff...')

    @asyncClose
    async def closeEvent(self, event):
        pass
        # self._client.end()


class MainWindow(QWidget):
    """Main window."""

    def __init__(self):

        super().__init__()
        self._layout = QVBoxLayout()
        self.setLayout(self._layout)

        self._select_user = QPushButton('select author')
        self._select_user.clicked.connect(partial(self.on_btnFetch_clicked, self._select_user))
        self._layout.addWidget(self._select_user)

        self._web_test = QPushButton('web test')
        self._web_test.clicked.connect(partial(self.on_btnFetch_clicked, self._web_test))
        self._layout.addWidget(self._web_test)

        self._scroll_test = QPushButton('scroll test')
        self._scroll_test.clicked.connect(partial(self.on_btnFetch_clicked, self._scroll_test))
        self._layout.addWidget(self._scroll_test)

        self._image_test = QPushButton('image test')
        self._image_test.clicked.connect(partial(self.on_btnFetch_clicked, self._image_test))
        self._layout.addWidget(self._image_test)

        self._client = Client('wss://nos.lol')
        self._profile_handler = NetworkedProfileEventHandler(client=self._client)

        self._seen_profiles = SeenProfiles()
        self._client.subscribe(handlers=self._seen_profiles,
                               filters={
                                   'kinds': [Event.KIND_TEXT_NOTE]
                               })

        self._select_user_dialog = None

        asyncio.create_task(self._client.run())

    @asyncClose
    async def closeEvent(self, event):
        pass

    def update_status(self):
        self._status_lbl.setText(self._run_status)

    def _set_run_status(self, status: str):
        pass

    @asyncSlot()
    async def on_text_scroll(self):
        pass

    # @asyncSlot()
    def on_btnFetch_clicked(self, *args):
        if args[0] == self._select_user:
            self._select_user_dialog = SelectUser(track_seen=self._seen_profiles,
                                                  profile_handler=self._profile_handler)
            # await self.exec_QDialog_async(SelectUser(track_seen=self._seen_profiles))

            self._select_user_dialog.accepted.connect(self._authors_accepted)
            self._select_user_dialog.exec_()

        elif args[0] == self._web_test:
            # hmmm gui doesn't work - maybe sort later but don't really want to go this route
            # anyhow...
            WebTest().exec_()
        elif args[0] == self._scroll_test:
            # EventViewDialog().exec_()
            EventViewWindow().show()


        elif args[0] == self._image_test:
            print('mother fucker')
            ImageView().exec_()


    @asyncSlot()
    async def _authors_accepted(self):
        print(self._select_user_dialog.selected_keys)
        self._select_user_dialog = None

    # async def exec_QDialog_async(self, the_dialog):
    #     # TODO: this isn't making modal like we expected....
    #     future = asyncio.Future()
    #     the_dialog.finished.connect(lambda r: future.set_result(r))
    #     the_dialog.open()
    #     the_dialog.show()
    #     return await future


class AuthorCombo(QComboBox):

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)

    def paintEvent(self, event):
        super(AuthorCombo, self).paintEvent(event)


# class SimpleDataItem(QStandardItem):
#
#     def __init__(self, *args, link_data, **kargs):
#         self._link_data = link_data
#         super(SimpleDataItem, self).__init__(*args, **kargs)
#

class MyUserProxyFilterModel(QSortFilterProxyModel):

    def __init__(self, *args, **kargs):
        super(MyUserProxyFilterModel, self).__init__(*args, **kargs)
        self._filter_str = ''

    def filterAcceptsRow(self, source_row:int, source_parent:PySide2.QtCore.QModelIndex) -> bool:
        idx = self.sourceModel().index(source_row, 0)
        search_str = self.sourceModel().data(idx)
        p: Profile
        item_data = self.sourceModel().itemData(idx)

        # role - todo look into this shit and what is role 257?!
        if 257 in item_data:
            item_data = item_data[257]
            p = item_data['profile']
            if not 'search_str' in item_data:
                search_str = f'{p.public_key}:{p.display_name()}'
                about = p.get_attr('about')
                if about:
                    search_str += f':{about}'

                search_str = item_data['search_str'] = search_str.casefold()

                self.sourceModel().setData(idx, item_data, 257)


            else:
                search_str = item_data['search_str']

        return self.filter_str == '' or self.filter_str in search_str

    @property
    def filter_str(self):
        return self._filter_str

    @filter_str.setter
    def filter_str(self, filter_str):
        self._filter_str = filter_str.lower()


class WebTest(QDialog):

    def __init__(self,
                 *args, **kargs):

        super(WebTest, self).__init__(*args, **kargs)

        self.setWindowTitle('fucks sake')
        self._layout = QVBoxLayout()
        self.setLayout(self._layout)

        self._url_text = QLineEdit(placeholderText='url')
        self._layout.addWidget(self._url_text)
        webview = QWebEngineView()
        webview.setUrl('www.google.co.uk')
        webview.show()
        self._layout.addWidget(webview)


class EventViewWindow(QWidget):

    def __init__(self,
                 *args, **kargs):

        super(EventViewWindow, self).__init__(*args, **kargs)

        self.setWindowTitle('view events')
        self._layout = QVBoxLayout()
        self.setLayout(self._layout)

        self._client = Client('wss://nos.lol')
        self._profile_handler = NetworkedProfileEventHandler(client=self._client)

        self._resource_loader = ResourceFetcher()

        self._current_source = LocationSource(name='local',
                                              data_source=self._client,
                                              profile_handler=self._profile_handler)
        # self._current_user = Keys(pub_k='5c4bf3e548683d61fb72be5f48c2dff0cf51901b9dd98ee8db178efe522e325f')


        # hacky load so we have a user
        from monstr.ident.alias import ProfileFileAlias
        my_profileLoader = ProfileFileAlias('/home/monty/.nostrpy/profiles.csv')
        self._current_user = my_profileLoader.get_profile('monty').keys
        asyncio.create_task(self._client.run())
        #####

        # tab container
        self._tabs = QTabWidget()
        self._tab_info = []

        # basic event view
        # self._create_new_tab('post')

        # testing ....
        self._create_new_tab('user/dm')

        self._create_new_tab('user/post')
        self._create_new_tab('user/reply')

        # another type of tab, we'll need to merga how this works with standard event tabs
        # done at end because currently it'll break other tabs as is...

        self._create_new_tab('user/follows/post')
        self._create_new_tab('user/follows/reply')
        self._create_new_tab('user/profile')


        self._address_bar = AddressBarPane(on_action=self._address_change)

        self._layout.addWidget(self._address_bar)

        self._layout.addWidget(self._tabs)

        self._tabs.currentChanged.connect(self._tabChanged)

        self.set_tab_state(0)

    def set_tab_state(self, tab_idx):
        tab_info: dict = self._tab_info[tab_idx]
        self._address_bar.set_state(locations=tab_info['locations'],
                                    index=tab_info['location_index'])

    def _address_change(self, data):
        tab_idx = self._tabs.currentIndex()
        tab_info: dict = self._tab_info[tab_idx]
        the_pane: ViewPane = self._get_current_view_pane(tab_idx)

        # stop current pane
        the_pane.stop()
        c_location: Location = tab_info['locations'][tab_info['location_index']]
        c_location.data = None

        n_location = data['location']
        change_type = data['type']


        tab_con: QWidget = tab_info['tab_con']

        item = tab_con.layout().takeAt(0)
        item.widget().setParent(None)

        # now start new view
        n_pane: ViewPane = n_location.data

        if n_pane is None:
            n_pane = self._create_pane_from_location(n_location)
            n_location.data = n_pane

        else:
            # at the moment as will stop and kill panes as we move away we should never get here
            # this would exist if we paused and were going to restart
            pass

        tab_con.layout().addWidget(n_pane)
        self._update_tab_state()

    def _get_current_location(self, tab_idx: int = None) -> Location:
        if tab_idx is None:
            tab_idx = self._tabs.currentIndex()

        tab_info: dict = self._tab_info[tab_idx]

        c_loc: Location

        print(tab_info['location_index'])
        for c_loc in tab_info['locations']:
            print(c_loc.full_address, c_loc.data)

        return tab_info['locations'][tab_info['location_index']]

    def _get_current_view_pane(self, tab_idx: int = None) -> ViewPane:
        return self._get_current_location(tab_idx).data

    def _do_actions(self, data):
        type = data['type']
        if type == 'hashtag_clicked':
            tab_idx = self._tabs.currentIndex()
            tab_info: dict = self._tab_info[tab_idx]
            the_pane: ViewPane = self._get_current_view_pane(tab_idx)
            # stop current pane
            the_pane.stop()

            c_location: Location = tab_info['locations'][tab_info['location_index']]
            c_location.data = None

            tab_con: QWidget = tab_info['tab_con']
            tab_con.layout().takeAt(0)

            context = c_location.context

            location = self._get_new_location(f'{context}/post?t={data["name"]}')
            n_pane = self._create_pane_from_location(location)
            location.data = n_pane

            tab_con.layout().addWidget(n_pane)

            # hash_view = HashView(data["name"])
            #
            # # TODO: this should just take view obj surely?
            # event_pane.set_view(new_filter=hash_view.view_filter,
            #                     event_acceptor=hash_view.view_acceptor)
            #
            self._address_bar.append(location)
            self._update_tab_state()

    def _update_tab_state(self):
        tab_idx = self._tabs.currentIndex()
        tab_info: dict = self._tab_info[tab_idx]
        locations, idx = self._address_bar.get_state()
        tab_info['location_index'] = idx
        tab_info['locations'] = locations

        print('we now have n locations ----', len(locations))

        self._tabs.setTabText(tab_idx, self._get_tab_name_for_location(locations[idx]))

    @staticmethod
    def _get_tab_name_for_location(location: Location):
        ret = location.resource_path
        hash = location.get_param('t')
        if hash:
            ret += f'#{"-".join(hash)}'
        return ret

    def _create_pane_from_location(self, location: Location):
        """
         think about these mappings e.g.
         local://          - just src, default to posts ?
         local://{pubkey}  - default to profile page

         should that be handled here or should the location automaticlly add a default cmd?
         (the location should probably needs improving so that if the last word isn't a commnad then its context?)
        """

        create_map = {
            'profile': self._create_profile_pane,
            'note': self._create_event_pane,
            'post': self._create_event_pane,
            'reply': self._create_event_pane,
            'dm': self._create_event_pane
        }

        return create_map[location.cmd](location)

    def _create_profile_pane(self, location: Location) -> ProfileViewPane:
        return ProfileViewPane(location=location,
                               on_actions=None,
                               resource_fetcher=self._resource_loader)

    def _create_event_pane(self, location: Location) -> EventViewPane:
        return EventViewPane(location=location,
                             on_actions=self._do_actions,
                             resource_fetcher=self._resource_loader)

    def _get_new_location(self, identifier:str,
                          data_source: LocationSource = None):
        if data_source is None:
            data_source = self._current_source

        return Location(source=data_source,
                        identifier=identifier,
                        current_user=self._current_user)

    def _create_new_tab(self, identifier: str,
                        data_source: LocationSource = None):

        location = self._get_new_location(identifier=identifier,
                                          data_source=data_source)

        n_pane = self._create_pane_from_location(location)
        location.data = n_pane

        # instead of adding n_pane directly to tab we create tab_con
        # as user moves adround in this tab panes are removed(stoped)
        # restarted or created into here
        tab_con = QWidget()
        tab_con_layout = QVBoxLayout()
        tab_con_layout.setContentsMargins(0,0,0,0)
        tab_con.setLayout(tab_con_layout)
        tab_con_layout.addWidget(n_pane)

        self._tabs.addTab(tab_con, location.resource_path)

        self._tab_info.append({
            'tab_con': tab_con,
            'location_index': 0,
            'locations': [location]
        })


    @asyncSlot()
    async def _tabChanged(self):
        self.set_tab_state(self._tabs.currentIndex())

    def closeEvent(self, event):
        self._client.end()
        for c_tab_info in self._tab_info:
            active_view: ViewPane = c_tab_info['locations'][c_tab_info['location_index']].data
            if active_view:
                active_view.stop()


class ImageView(QDialog):

    def __init__(self,
                 *args, **kargs):

        super(ImageView, self).__init__(*args, **kargs)
        self.setWindowTitle('load images')

        self._layout = QVBoxLayout()
        self.setLayout(self._layout)

        self._url_text = QLineEdit(placeholderText='url')
        self._layout.addWidget(self._url_text)

        do_btn = QPushButton('do it!!!')
        self._layout.addWidget(do_btn)
        do_btn.clicked.connect(self._do_load)

        self._image = QPixmap()
        self._image_lbl = QLabel()
        self._image_lbl.setFixedWidth(64)
        self._image_lbl.setFixedHeight(64)

        self._layout.addWidget(self._image_lbl)

        self._loader = ResourceFetcher()

    @asyncSlot()
    async def _do_load(self):
        data = await self._loader.get(self._url_text.text())
        self._image.loadFromData(data)
        self._image_lbl.setPixmap(self._image.scaled(64,64))


class SelectUser(QDialog):

    def __init__(self,
                 track_seen: SeenProfiles,
                 title='select profiles',
                 profile_handler=None,
                 *args, **kargs):

        super(SelectUser, self).__init__(*args, **kargs)

        self.setWindowTitle(title)

        # we couldn't show anything if this doesnt exists so we'll just let this err in that case
        self._seen = track_seen
        self._profile_handler: NetworkedProfileEventHandler = profile_handler

        self._layout = QVBoxLayout()
        self.setLayout(self._layout)

        self._select_text = QLineEdit(placeholderText='npub, hex or name')
        self._select_text.textChanged.connect(self._search_changed)
        self._layout.addWidget(self._select_text)

        # mid pane that'll contain sector area and selected list
        self._mid_pane = QWidget()
        self._mid_pane_layout = QHBoxLayout()
        self._mid_pane.setLayout(self._mid_pane_layout)
        self._layout.addWidget(self._mid_pane)



        # make select list
        self._list_view = QListView()

        all_items = self._seen.seen()
        # all_items = ['93cccf9fea855caa331d6263266928276c4c3ee1f9b05764f7c1f72ebf0bf643']
        self._list_model = self._init_list_model(all_items)

        self._sort_proxy = MyUserProxyFilterModel()
        self._sort_proxy.setSourceModel(self._list_model)
        self._sort_proxy.setSortCaseSensitivity(Qt.CaseInsensitive)
        self._list_view.setModel(self._sort_proxy)
        self._list_view.setSelectionMode(QAbstractItemView.MultiSelection)


        self._mid_pane_layout.addWidget(self._list_view)
        self._list_view.selectionModel().selectionChanged.connect(self._list_selection_changed)


        # create the area between select and selected lists
        # self._mid_mid_pane = QWidget()
        # self._mid_mid_layout = QVBoxLayout()
        # self._mid_mid_pane.setLayout(self._mid_mid_layout)
        # self._mid_mid_layout.addWidget(QPushButton('>'))
        # self._mid_mid_layout.addWidget(QPushButton('<'))
        # self._mid_pane_layout.addWidget(self._mid_mid_pane)

        self._mid_mid_pane = QDialogButtonBox(orientation=Qt.Vertical)
        self._mid_mid_layout = self._mid_mid_pane.layout()
        self._add_sel_but = QPushButton('>', enabled=False)
        self._add_sel_but.clicked.connect(self._move_selection_selected)


        self._mid_mid_layout.addWidget(self._add_sel_but)
        self._mid_mid_layout.addWidget(QPushButton('<'))
        self._mid_mid_layout.addWidget(QPushButton('clear &all'))
        self._mid_mid_layout.addWidget(QPushButton('&reset'))


        # self._mid_mid_layout = QVBoxLayout()
        # self._mid_mid_pane.setLayout(self._mid_mid_layout)
        # self._mid_mid_layout.addWidget(QPushButton('>'))
        # self._mid_mid_layout.addWidget(QPushButton('<'))
        self._mid_pane_layout.addWidget(self._mid_mid_pane)

        self._selected_list = QListView(model=QStandardItemModel(0, 0))
        self._mid_pane_layout.addWidget(self._selected_list)

        # add the ok/cancle buttons, connect ok/cancle actions
        self._action_buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._layout.addWidget(self._action_buttons)
        self._action_buttons.accepted.connect(self.accept)
        self._action_buttons.rejected.connect(self.reject)

        async def init_profiles():
            await self._profile_handler.aget_profiles(pub_ks=all_items,
                                                      create_missing=True)
            n_rows = len(all_items)
            p: Profile

            # self._sort_proxy.setSourceModel(None)
            for r in range(n_rows):
                pub_k = all_items[r]
                p = self._profile_handler.get_profile(pub_k)
                if p:
                    n_item = QStandardItem(p.display_name())
                    n_item.setData({
                        'profile': p
                    })

                    self._list_model.setItem(r, 0, n_item)

            self._sort_proxy.sort(0)
            # self._list_model.sort(0)

        if self._profile_handler:
            asyncio.create_task(init_profiles())


    @asyncSlot()
    async def _search_changed(self):
        search_text = self._select_text.text()
        self._sort_proxy.filter_str = search_text
        # force filter to happen
        self._sort_proxy.setFilterKeyColumn(0)

    @asyncSlot()
    async def _list_selection_changed(self):
        the_selection = self._list_view.selectionModel().selection()
        self._add_sel_but.setEnabled(the_selection.count())


    @asyncSlot()
    async def _move_selection_selected(self):
        dest_r = self._selected_list.model().rowCount()

        the_selection = self._list_view.selectionModel().selectedIndexes()
        to_delete = []

        # this is shit, we must be doing something wrong or not understanding
        # somehting about how selection works.... when select from ctrl-a
        # we seem to get row * row selection when we should only have row * col(0)
        # all works fine selecting by mouse WTF?!
        did_row = set()

        if the_selection:
            for idx in the_selection:
                sel_row = idx.row()
                if sel_row not in did_row:
                    item = self._list_model.item(idx.row(),0)
                    src_r = self._sort_proxy.mapToSource(idx).row()
                    item = self._list_model.takeItem(src_r,0)

                    self._selected_list.model().setItem(dest_r, 0, item)
                    dest_r += 1
                    to_delete.append(src_r)
                    did_row.add(sel_row)

            # now delete the empty rows, probably better way of doing this....
            to_delete.sort(reverse=True)
            for r in to_delete:
                self._list_model.removeRow(r)

    # this can probably abstacted out to model with data or something similar...
    def _init_list_model(self, pub_keys: [str]) -> QStandardItemModel:
        n_rows = len(pub_keys*5)
        ret = QStandardItemModel(1, n_rows)

        for r in range(len(pub_keys)):
            pub_k = pub_keys[r]
            # create a new item and add it to the model
            n_item = QStandardItem(pub_k)

            ret.setItem(r, 0, n_item)

        return ret

    @asyncClose
    async def closeEvent(self, event):
        self.finished.emit(0)

    @property
    def selected_keys(self):
        sel_model = self._selected_list.model()
        return [
            sel_model.item(idx).data()['profile'].public_key
            for idx in range(sel_model.rowCount())
        ]


async def main():
    def close_future(future, loop):
        loop.call_later(10, future.cancel)
        future.cancel()

    loop = asyncio.get_event_loop()
    future = asyncio.Future()

    app = QApplication.instance()

    # from PySide2.QtCore import QUrl
    # view = QWebEngineView()
    # view.load(QUrl("https://qt-project.org/"))
    # view.resize(1024, 750)
    # view.show()


    if hasattr(app, "aboutToQuit"):
        getattr(app, "aboutToQuit").connect(
            partial(close_future, future, loop)
        )

    mainWindow = TestWindow()
    mainWindow.show()

    await future
    return True


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    try:
        qasync.run(main())
    except asyncio.exceptions.CancelledError:
        sys.exit(0)