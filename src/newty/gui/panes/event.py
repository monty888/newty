import asyncio
from abc import ABC, abstractmethod
from functools import partial

from PySide2.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton,
    QSizePolicy
)

from PySide2.QtGui import (
    Qt
)


from monstr.client.client import Client
from monstr.client.event_handlers import EventAccepter
from monstr.event.event import Event
from monstr.ident.profile import Profile
from monstr.encrypt import Keys
from monstr.signing.signing import SignerInterface, BasicKeySigner
from monstr.ident.event_handlers import NetworkedProfileEventHandler, ProfileEventHandlerInterface
from monstr.util import util_funcs
from newty.network.media import ResourceFetcher
from newty.gui.layout import FlowLayout
from newty.gui.nostr import VerticalScrollArea, LabelWithRemoteImage
from newty.gui.panes.panes import ViewPane
from newty.gui.nostr import Location
from newty.gui.event.acceptors import PostsOnlyAcceptor, RepliesOnlyAcceptor
# from monstr_qt.gui.event.views import CurrentUserFollowsPostsFilter, CurrentUserFollowsThreadsFilter


class DynamicFilter(ABC):
    """
            A filter that requires data from relay
        """
    @abstractmethod
    async def ainit_filter(self):
        pass


class UserContactsFilter(DynamicFilter):
    """
        TODO: this should also be changing on follower changes
    """
    def __init__(self,
                 base_filter: dict,
                 for_user: Keys,
                 profile_handler: NetworkedProfileEventHandler):
        self._base_filter = base_filter
        self._filter = None
        self._for_user = for_user
        self._profile_handler = profile_handler

    async def ainit_filter(self) -> dict:
        contacts = await self._profile_handler.aload_contacts(self._for_user.public_key_hex())
        self._filter = self._base_filter.copy()
        self._filter['authors'] = contacts.follow_keys()
        return self._filter

    @property
    def filter(self):
        # TODO: this should error if ainit_filter hasn't beem called
        return self._filter


class EventView:

    def __init__(self,
                 view_filter: [dict | DynamicFilter],
                 view_acceptor: EventAccepter = None):

        self._view_filter = view_filter
        self._view_acceptor = view_acceptor

    @property
    def view_filter(self):
        return self._view_filter

    @view_filter.setter
    def view_filter(self, view_filter):
        self._view_filter = view_filter

    @property
    def view_acceptor(self):
        return self._view_acceptor


class BasicEventDisplay(QWidget):

    def __init__(self,
                 *args,
                 event: Event,
                 callback,
                 profile_handler:ProfileEventHandlerInterface = None,
                 resource_loader: ResourceFetcher = None,
                 # should accept keys or a signer
                 current_user: Keys = None,
                 **kargs):
        super(BasicEventDisplay, self).__init__(*args, **kargs)

        self._event = event
        self._profile_handler = profile_handler
        self._callback = callback
        self._current_user = current_user
        self._signer = None
        if current_user and current_user.private_key_hex() is not None:
            self._signer = BasicKeySigner(current_user)

        # self._scaled_pixmap_cache = LRUCache(maxsize=10000)

        self._resource_load = resource_loader

        # self._event_layout = QGridLayout()
        # self._event_layout.setColumnStretch(0, 1)

        # try with vbox, maybe grid will be better?
        self._event_layout = QVBoxLayout()
        # three sections header, main body(content) and footer (actions?)
        self._create_panes()
        # create the widgets and fill with event data (that we have now)
        asyncio.create_task(self._create_widgets())

        self.setLayout(self._event_layout)



    def _create_panes(self):
        # create title container
        self._title_pane = QWidget()
        self._title_layout = QHBoxLayout()
        self._title_layout.setContentsMargins(0, 0, 0, 0)
        self._title_pane.setLayout(self._title_layout)
        self._event_layout.addWidget(self._title_pane)

        # create content area
        self._content_pane = QWidget()
        self._content_layout = QHBoxLayout()
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_pane.setLayout(self._content_layout)
        self._event_layout.addWidget(self._content_pane)

        # create the footer area
        self._foot_pane = QWidget()
        self._foot_layout = QHBoxLayout()
        self._foot_layout.setContentsMargins(0, 0, 0, 0)
        self._foot_pane.setLayout(self._foot_layout)
        self._event_layout.addWidget(self._foot_pane)

        # split footer into 2 panes one for tags, one for controls?
        self._hash_pane = QWidget()
        # self._hash_scroll = QScrollArea()
        # self._hash_scroll.setWidget(self._hash_pane)
        self._hash_layout = QHBoxLayout()

        self._hash_layout = FlowLayout()

        self._hash_layout.setContentsMargins(0, 0, 0, 0)
        self._hash_pane.setLayout(self._hash_layout)
        self._foot_layout.addWidget(self._hash_pane)

    async def _create_widgets(self):
        author_k = self._event.pub_key
        author_p: Profile = None

        #TODO - change to aget_profile?
        if self._profile_handler and self._profile_handler.have_profile(author_k):
            author_p = self._profile_handler.get_profile(author_k)

        # add
        user_display = util_funcs.str_tails(author_k)
        if author_p:
            user_display = author_p.display_name()
        self._pub_k_widget = QLabel(user_display)
        self._pub_k_widget.setStyleSheet('font-weight: bold;')
        self._title_layout.addWidget(self._pub_k_widget)

        # title_layout.addWidget(QSpacerItem())
        time_label = QLabel(str(self._event.created_at))
        time_label.setAlignment(Qt.AlignRight)

        self._title_layout.addWidget(time_label)

        # create text widget and fill with event content
        evt_content = self._event.content
        if self._event.kind == Event.KIND_ENCRYPT \
                and self._signer:
            try:
                evt_content = (await self._signer.nip4_decrypt_event(self._event)).content
            except Exception as e:
                print(e)
                # TODO fix monstr exception text this leaks private key!!!
                evt_content = str(e)


        my_text = QTextEdit(evt_content)
        my_text.setReadOnly(True)
        # my_text.setLineWrapMode(QTextEdit.FixedColumnWidth)
        # my_text.setLineWrapColumnOrWidth(160)
        my_text.setMaximumHeight(100)
        my_text.sizePolicy().setHorizontalPolicy(QSizePolicy.Expanding)

        # make placeholder images for if we can't load or aren't loading e.g. robbos
        author_img_url = None
        if author_p:
            author_img_url = author_p.get_attr('picture')


        # self._profile_img_lbl.setAlignment(Qt.AlignTop)
        # self._profile_img_lbl.setStyleSheet('border: 1px solid black; border-radius: 10px')
        if author_p:
            author_img_url = author_p.get_attr('picture')

        self._profile_img_lbl = LabelWithRemoteImage('[X]',
                                                     image_url=author_img_url,
                                                     size=64,
                                                     resource_load=self._resource_load)

        self._content_layout.addWidget(self._profile_img_lbl, alignment=Qt.AlignTop)
        self._content_layout.addWidget(my_text, alignment=Qt.AlignTop)

        # todo what to put here in the footer?
        hash_tags = self._event.get_tags_value('t')
        for v in hash_tags:
            tag_widget = QPushButton(f'#{v}')
            tag_widget.setFlat(True)
            tag_widget.setStyleSheet('color: blue;')
            tag_widget.clicked.connect(partial(self._tag_pressed, v))
            self._hash_layout.addWidget(tag_widget)

    def _tag_pressed(self, *args):
        self._callback({
            'type': 'hashtag_clicked',
            'name': args[0]
        })

    def updated_profiles(self, updated_profiles: set):
        if self._event.pub_key in updated_profiles:
            author_p: Profile = self._profile_handler.get_profile(self._event.pub_key)
            self._pub_k_widget.setText(author_p.display_name())
            self._profile_img_lbl.image_url = author_p.get_attr('picture')


def event_view_from_location(location: Location,
                             profile_handler: NetworkedProfileEventHandler) -> dict[str, str] | EventView:
    """
        good enough for now I guess....
        decoding the content is going to be the main pain...

    """

    # if user context user then error if we don't have a current_user
    if location.context == 'user':
        if location.current_user is None:
            return {
                'error': f'no user set for can\'t create view {location.full_path}'
            }

    param_args = {}
    hash_params = location.get_param('t')
    if hash_params:
        param_args['#t'] = hash_params

    if location.cmd == 'note':
        """
            this should contain posts and replies
        """
        filter_args = {
            'limit': 20,
            'kinds': [1]
        }

        filter_args.update(param_args)

        if location.context == 'user':
            filter_args['authors'] = [location.current_user.public_key_hex()]

        ret = EventView(view_filter=filter_args)

    elif location.cmd == 'post':
        # as not but we add an acceptor so that only posts are included

        filter_args = {
            'limit': 20,
            'kinds': [1]
        }

        filter_args.update(param_args)

        filter_tracker = None
        if location.context == 'user':
            filter_args['authors'] = [location.current_user.public_key_hex()]
        elif location.context == 'user/follows':
            filter_args['limit'] = 40
            filter_args = UserContactsFilter(base_filter=filter_args,
                                             for_user=location.current_user,
                                             profile_handler=profile_handler)

        ret = EventView(view_filter=filter_args,
                        view_acceptor=PostsOnlyAcceptor())

    elif location.cmd == 'reply':
        # only where we were replying to some other event

        filter_args = {
            'limit': 20,
            'kinds': [1]
        }

        filter_args.update(param_args)

        if location.context == 'user':
            filter_args['authors'] = [location.current_user.public_key_hex()]
        elif location.context == 'user/follows':
            filter_args['limit'] = 40
            filter_args = UserContactsFilter(base_filter=filter_args,
                                             for_user=location.current_user,
                                             profile_handler=profile_handler)

        ret = EventView(view_filter=filter_args,
                        view_acceptor=RepliesOnlyAcceptor())

    elif location.cmd == 'dm':
        filter_args = {
            'limit': 20,
            'kinds': [4]
        }
        if location.context == 'user':
            filter_args = [
                {
                    'kinds': [4],
                    'limit': 20,
                    'authors': [location.current_user.public_key_hex()]
                },
                {
                    'kinds': [4],
                    'limit': 20,
                    '#p': [location.current_user.public_key_hex()]
                }
            ]
        ret = EventView(view_filter=filter_args)
    else:
        ret = {
            'error': f'unknown command {location.cmd}'
        }

    return ret


class EventViewPane(ViewPane):
    """
        updating scroll view of events using BasicEventDisplay for each event

        TODO: change from QDialog to be on a widget
            working with client pool
            handing in the things it needs

    """
    def __init__(self,
                 *args,
                 location: Location,
                 on_actions=None,
                 resource_fetcher: ResourceFetcher = None,
                 **kargs):

        super(EventViewPane, self).__init__(location=location, *args, **kargs)

        # self._layout = QVBoxLayout()
        # self.setLayout(self._layout)
        # self.setFixedWidth(1000)

        self._scroll_pane = VerticalScrollArea()

        # should be handed in
        self._resource_fetch = resource_fetcher

        # self._scroll_pane = QWidget()
        # self._scroll_layout = QVBoxLayout()
        # self._scroll_pane.setLayout(self._scroll_layout)

        self._layout.addWidget(self._scroll_pane)

        # for now this is good enough, probably the actual source
        # will always be either Client/ClientPool which to us are identical
        self._location = location
        self._client = location.source.data_source

        self._profile_handler = location.source.profile_handler

        self._view = event_view_from_location(location=location,
                                              profile_handler=self._profile_handler)
        if isinstance(self._view, EventView):
            self._current_filter = self._view.view_filter
            self._event_acceptor = self._view.view_acceptor
            self._sub_id = None
            self._scroll_pane.addWidget(QLabel('loading...'), alignment=Qt.AlignTop)
            asyncio.create_task(self.fetch_events())
        else:
            self._scroll_pane.addWidget(QLabel(self._view['error']), alignment=Qt.AlignTop)

        # map events to widgets
        self._events_map = {}

        self._open = True
        self._on_actions = on_actions


    @property
    def current_filter(self):
        return self._current_filter

    @property
    def event_acceptor(self):
        return self._event_acceptor

    def stop(self):
        if self._sub_id:
            self._client.unsubscribe(self._sub_id)
            self._events_map = {}
            # self._scroll_pane.clear()

        self._open = False

    def pause(self):
        # should just be self._stop_current() but doesnt seem to work at the moment
        # looks like QT killed the pane? we might need to recreate pane
        pass

    def restart(self):
        if self._sub_id is None:
            asyncio.create_task(self.fetch_events())
        else:
            self._client.subscribe(sub_id=self._sub_id,
                                   filters=self._current_filter,
                                   eose_func=self.on_eose,
                                   handlers=self)

    async def fetch_events(self):
        await self._client.wait_connect()

        if isinstance(self._current_filter, DynamicFilter):
            await self._current_filter.ainit_filter()
            event_filter = self._current_filter.filter
        else:
            event_filter = self._current_filter

        self._scroll_pane.clear()
        self._sub_id = self._client.subscribe(filters=event_filter,
                                              eose_func=self.on_eose,
                                              handlers=self)
        while self._client.running and self._open is True:
            await asyncio.sleep(0.1)

    def _make_event_widget(self, evt):
        evt_widget = BasicEventDisplay(event=evt,
                                       profile_handler=self._profile_handler,
                                       resource_loader=self._resource_fetch,
                                       current_user=self._location.current_user,
                                       callback=self._do_actions)

        self._events_map[evt.id] = {
            'widget': evt_widget
        }

        return evt_widget

    def _do_actions(self, data):
        if self._on_actions:
            self._on_actions(data)

    async def _fetch_events_profile(self, evts: [Event]):
        if not self._profile_handler:
            return

        c_evt: Event

        to_fetch = set()
        for c_evt in evts:
            # if not self._profile_handler.have_profile(c_evt.pub_key):
            to_fetch.add(c_evt.pub_key)

        # to_fetch = list(to_fetch)
        #
        # if to_fetch:
        loaded_profiles = await self._profile_handler.aget_profiles(to_fetch, create_missing=True)
        # tell all our widgets that we loaded these profiles, up to then if they want to do
        # anything with it

        loaded_profiles = set([p.public_key for p in loaded_profiles])
        for c_item in self._events_map.values():
            c_widget = c_item['widget']
            c_widget.updated_profiles(loaded_profiles)

    def do_event(self, the_client: Client, sub_id, evt: Event):
        if self._event_acceptor is None or \
                self._event_acceptor.accept_event(the_client, sub_id, evt):
            self._scroll_pane.insertTop(self._make_event_widget(evt))
            asyncio.create_task(self._fetch_events_profile([evt]))

    def on_eose(self, the_client: Client, sub_id, evt: [Event]):
        Event.sort(evt, inplace=True, reverse=True)
        accepted_evts = []
        for c_evt in evt:
            if self._event_acceptor is None \
                    or self._event_acceptor.accept_event(the_client, sub_id, c_evt):
                accepted_evts.append(c_evt)
                self._scroll_pane.addWidget(self._make_event_widget(c_evt))

        asyncio.create_task(self._fetch_events_profile(accepted_evts))

    def closeEvent(self, event):
        self._open = False