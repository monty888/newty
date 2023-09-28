import asyncio

from PySide2.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton,
    QSizePolicy,
    QFormLayout,
    QLineEdit,
    QTextEdit,
    QSpacerItem
)

from PySide2.QtGui import (
    QPixmap,
    Qt,
    QPaintEvent,
    QPainter
)

from monstr.ident.event_handlers import NetworkedProfileEventHandler
from monstr_qt.gui.panes.panes import ViewPane
from monstr_qt.gui.nostr import Location
from monstr_qt.util import ResourceFetcher
from monstr_qt.gui.nostr import VerticalScrollArea
from monstr.ident.profile import Profile
from monstr.client.client import Client
from monstr.encrypt import Keys


class PictureArea(QWidget):
    def __init__(self,
                 profile: Profile,
                 resource_fetcher: ResourceFetcher = None,
                 *args,
                 **kargs):
        super(PictureArea, self).__init__(*args, **kargs)

        self._layout = QVBoxLayout()
        self.setLayout(self._layout)

        self._resource_fetcher = resource_fetcher
        self._profile = profile

        # TODO when we have media disabled something like this would be possible so
        #  we should have something for that case
        #

        self._picture_area = QLabel('loading...')
        self._layout.addWidget(self._picture_area)
        if resource_fetcher:
            asyncio.create_task(self.load_images())
        else:
            self._picture_area.setText('TODO --- media is disabled????')

    async def load_images(self):
        banner_img = None
        profile_img = None

        # we should send this off together, look into amd then wait for both to complete
        profile_img_url = self._profile.get_attr('picture')
        if profile_img_url:
            profile_img = await self._resource_fetcher.get(profile_img_url)

        banner_img_url = self._profile.get_attr('banner')
        if banner_img_url:
            banner_img = await self._resource_fetcher.get(banner_img_url)

        if banner_img and profile_img:
            # self._picture_area.setText('yeah man')

            pxmap = QPixmap()
            pxmap.loadFromData(banner_img)

            print(self.parent().width())

            # pxmap = pxmap.scaledToWidth(self.width(), Qt.SmoothTransformation)
            pxmap = pxmap.scaled(640, 128, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)


            self._picture_area.setPixmap(pxmap)


class ProfileFields(QWidget):

    def __init__(self,
                 profile: Profile,
                 *args,
                 **kargs):
        super(ProfileFields, self).__init__(*args, **kargs)

        self._layout = QFormLayout()

        self.setLayout(self._layout)

        self._profile = profile
        self._name = ''
        self._nip05 = ''
        self._about = ''
        self._picture = ''
        self._banner = ''

        # TODO: change Profile get_attr to have default value
        def get_attr(name):
            ret = self._profile.get_attr(name)
            if ret is None:
                ret = ''
            return ret

        others = []
        if self._profile:
            self._name = self._profile.name
            self._nip05 = self._profile.nip05
            self._about = get_attr('about')
            self._picture = get_attr('picture')
            self._banner = get_attr('banner')

            # add any other fields we see that are not included above
            for k,v in self._profile.attrs.items():
                if k not in ('name', 'nip05', 'about', 'picture', 'banner'):
                    others.append([k, v])


        self._layout.addRow('name', QLineEdit(self._name))
        self._layout.addRow('nip05', QLineEdit(self._nip05))

        self._about_text = QTextEdit(self._about)
        # self._about_text.setMaximumHeight(100)
        self._layout.addRow('about', self._about_text)

        self._layout.addRow('picture', QLineEdit(self._picture))
        self._layout.addRow('banner', QLineEdit(self._banner))

        for c_extras in others:
            self._layout.addRow(c_extras[0], QLineEdit(str(c_extras[1])))


class ProfileViewPane(ViewPane):

    def __init__(self,
                 location: Location,
                 on_actions=None,
                 resource_fetcher: ResourceFetcher = None,
                 *args,
                 **kargs):
        super(ProfileViewPane, self).__init__(location=location,
                                              *args, **kargs)

        self._location = location
        self._client = location.source.data_source
        self._profile_handler = location.source.profile_handler
        self._resource_fetcher = resource_fetcher

        self._context = location.context
        self._user = location.current_user
        context_split = self._context.split('/')
        self._context_leaf = context_split[len(context_split)-1]

        if context_split and (self._context_leaf == 'user' or self._context_leaf.startswith('npub')):
            asyncio.create_task(self._create_user())
        else:
            asyncio.create_task(self._create_view())

    async def _create_user(self):
        """
            create single page view when we're looking at an individual profile
        """
        for_key = self._user.public_key_hex()

        if self._context_leaf != 'user':
            for_key = Keys.get_key(self._context_leaf).public_key_hex()

        await self._client.wait_connect()
        my_profile: Profile = await self._profile_handler.aget_profile(for_key)


        scroll = VerticalScrollArea()
        self.layout().addWidget(scroll)


        scroll.addWidget(PictureArea(profile=my_profile,
                                     resource_fetcher=self._resource_fetcher))
        scroll.addWidget(ProfileFields(profile=my_profile))


    async def _create_view(self):
        """
            list view where new profile events comde in for example at source://profile
        """
        self._layout.addWidget(QLabel('scroller mother fucker!!!'))


    def stop(self):
        pass

    def pause(self):
        pass

    def restart(self):
        pass