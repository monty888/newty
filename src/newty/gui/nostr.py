import asyncio
from PySide2.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QLineEdit,
    QStyle
)

from PySide2.QtGui import (
    QPixmap,
    Qt
)

from monstr.ident.event_handlers import NetworkedProfileEventHandler
from monstr.encrypt import Keys
from newty.util import ResourceFetcher
from newty.gui.util import mask_image


class VerticalScrollArea(QScrollArea):

    def __init__(self,
                 *args, **kargs):
        super(VerticalScrollArea, self).__init__(*args, **kargs)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWidgetResizable(True)

        my_con = QWidget()
        self._layout = QVBoxLayout()
        my_con.setLayout(self._layout)

        self.setWidget(my_con)

    def addWidget(self, the_widget, **kargs):
        self._layout.addWidget(the_widget, **kargs)

    def insertTop(self, the_widget):
        self._layout.insertWidget(0, the_widget)

    def clear(self):
        for i in reversed(range(self._layout.count())):
            self._layout.itemAt(i).widget().setParent(None)


class LabelWithRemoteImage(QLabel):

    def __init__(self, *args,
                 image_url: str = None,
                 size=64,
                 resource_load: ResourceFetcher = None,
                 **kargs):

        if 'fixedWidth' not in kargs:
            kargs['fixedWidth'] = size
        if 'fixedHeight' not in kargs:
            kargs['fixedHeight'] = size

        super(LabelWithRemoteImage, self).__init__(*args, **kargs)
        self._image_url = image_url
        self._size = size
        self._resource_load = resource_load

        # set the image on the lbl or start to load it and set it when we have it
        self._set_image()

    @property
    def image_url(self):
        return self._image_url

    @image_url.setter
    def image_url(self, image_url:str):
        self._image_url = image_url
        self._set_image()

    def _set_image(self):
        ret = None
        if self._resource_load and \
                self._image_url is not None and \
                self._image_url.lower().startswith('http'):
            # we already have the image
            if self._image_url in self._resource_load:
                img_data = self._resource_load[self._image_url]
                if img_data:
                    self.setPixmap(self._pixmap_from_data(img_data))
            # we don't have it so we'll start a job to fetch and then update ourself
            else:
                asyncio.create_task(self._fetch_image())

        return ret

    def _pixmap_from_data(self, img_data: bytes):
        # we should change it so we save cache this translations also
        # and don't have to always work from the original img data
        pxmap = QPixmap()
        pxmap.loadFromData(img_data)
        # return mask_image(pxmap.scaled(self._size, self._size).toImage())
        return mask_image(pxmap, to_size=self._size)

    async def _fetch_image(self):
        img_data = await self._resource_load.get(self._image_url)
        if img_data:
            self.setPixmap(self._pixmap_from_data(img_data))


class LocationSource:

    def __init__(self,
                 name,
                 data_source,
                 profile_handler: NetworkedProfileEventHandler = None):
        self._name = name
        self._data_source = data_source
        self._profile_handler = profile_handler

    @property
    def name(self):
        return self._name

    @property
    def data_source(self):
        return self._data_source

    @property
    def profile_handler(self):
        return self._profile_handler


class Location:

    SOURCE_SEP = '://'
    PATH_SEP = '/'

    def __init__(self,
                 source: LocationSource,
                 identifier: str,
                 current_user: Keys = None,
                 data=None):

        self._source = source
        self._identifier = identifier
        self._context: str = ''
        self._cmd: str
        self._params: [[str]] = []
        self._current_user = current_user
        self._decode()
        self._data = data

    def _decode(self):
        address_parts = self._identifier.split('?')
        if len(address_parts) > 1:
            for c_param in address_parts[1].split('&'):
                n_v_split = c_param.split('=')
                if len(n_v_split) >= 2:
                    self._params.append([n_v_split[0]] + n_v_split[1].split(','))
                else:
                    # skip
                    pass

        context_parts = address_parts[0].split('/')

        self._cmd = context_parts[len(context_parts)-1]
        if len(context_parts) >= 1:
            self._context = '/'.join(context_parts[:len(context_parts)-1])

    @property
    def full_path(self):
        return f'{self._source.name}{Location.SOURCE_SEP}{self.resource_path}'

    @property
    def full_address(self):
        ret = self.full_path
        if self.params_str:
            ret += f'?{self.params_str}'
        return ret

    @property
    def params_str(self):
        ret = []
        if self._params:
            for c_param in self._params:
                ret.append(f'{c_param[0]}={",".join(c_param[1:])}')

        return '&'.join(ret)

    def get_param(self, name):
        ret = []
        for c_param in self._params:
            if c_param[0] == name:
                ret = c_param[1:]
                break
        return ret

    @property
    def resource_path(self):
        ret = self._context

        if ret:
            ret += Location.PATH_SEP

        ret += self._cmd
        return ret

    @property
    def cmd(self):
        return self._cmd

    @property
    def source(self) -> LocationSource:
        return self._source

    @property
    def context(self):
        return self._context

    @property
    def current_user(self):
        return self._current_user

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, data):
        self._data = data

    def __str__(self):
        return self.full_address


class AddressBarPane(QWidget):

    def __init__(self, *args, on_action=None, **kargs):
        super(AddressBarPane, self).__init__(*args, **kargs)

        self._layout = QHBoxLayout()
        self.setLayout(self._layout)
        self._layout.setContentsMargins(0, 0, 0, 0)

        self._back_button = QPushButton()
        pixmap = getattr(QStyle, 'SP_ArrowBack')
        icon = self.style().standardIcon(pixmap)
        self._back_button.setIcon(icon)

        self._forward_button = QPushButton()
        pixmap = getattr(QStyle, 'SP_ArrowRight')
        icon = self.style().standardIcon(pixmap)
        self._forward_button.setIcon(icon)

        self._up_button = QPushButton()
        pixmap = getattr(QStyle, 'SP_ArrowUp')
        icon = self.style().standardIcon(pixmap)
        self._up_button.setIcon(icon)


        self._layout.addWidget(self._back_button)
        self._layout.addWidget(self._forward_button)
        self._layout.addWidget(self._up_button)

        self._address_bar = QLineEdit()

        self._address_bar.returnPressed.connect(self._address_entered)

        self._layout.addWidget(self._address_bar)

        self._locations = []
        self._current_index = None

        self._forward_button.clicked.connect(self._do_forward)
        self._back_button.clicked.connect(self._do_back)
        self._up_button.clicked.connect(self._do_up)

        self._on_action = on_action

    def _address_entered(self):
        if self._address_bar.text() != self.current_location.full_address:
            # hack for now - source will be seperate
            identifier = self._address_bar.text().replace(f'{self.current_location.source.name}://','')

            n_location = Location(source=self.current_location.source,
                                  identifier=identifier,
                                  current_user=self.current_location.current_user)

            if self._on_action:
                self.append(n_location)
                self._on_action({
                    'type': 'new',
                    'location': n_location
                })

    def _do_forward(self):
        self._current_index += 1
        n_location = self._locations[self._current_index]
        self._address_bar.setText(str(n_location))
        if self._on_action:
            self._on_action({
                'type': 'forward',
                'location': n_location
            })

        self._set_nav_btn_state()

    def _do_back(self):
        self._current_index -= 1

        n_location: Location = self._locations[self._current_index]
        self._address_bar.setText(n_location.full_address)

        if self._on_action:
            self._on_action({
                'type': 'back',
                'location': n_location
            })

        self._set_nav_btn_state()

    def _do_up(self):
        c_location = self.current_location
        context_split = c_location.context.split('/')

        context_split = context_split[:len(context_split)-1]
        if c_location.cmd:
            context_split += [c_location.cmd]
        n_identifier = '/'.join(context_split)

        if c_location.params_str:
            n_identifier += f'?{c_location.params_str}'

        n_location = Location(source=c_location.source,
                              identifier=n_identifier,
                              current_user=c_location.current_user)
        if self._on_action:
            self.append(n_location)

            self._on_action({
                'type': 'up',
                'location': n_location
            })

        self._set_nav_btn_state()

    def set_state(self, locations: [Location], index: int = 0):
        self._locations = locations
        self._current_index = index
        self._address_bar.setText(self.current_location.full_address)
        self._set_nav_btn_state()

    def get_state(self) -> ([Location], int):
        return self._locations, self._current_index

    def _set_nav_btn_state(self):
        self._back_button.setEnabled(self._current_index is not None
                                     and self._current_index != 0)

        self._forward_button.setEnabled(self._current_index is not None
                                        and self._current_index != len(self._locations)-1)

        c_location: Location = self._locations[self._current_index]
        self._up_button.setEnabled(c_location.context != '')

    # @property
    # def current_text(self):
    #     return self._locations[self._current_index]

    @property
    def current_location(self) -> Location:
        return self._locations[self._current_index]

    def append(self, location: Location):
        # we append to where we at, locations after that point are cut
        if self._current_index < len(self._locations)-1:
            self._locations = self._locations[:self._current_index+1]

        self._locations.append(location)
        self._current_index = len(self._locations)-1

        self._address_bar.setText(location.full_address)
        self._set_nav_btn_state()


if __name__ == "__main__":
    src = LocationSource('local', None)
    location = Location(source=src,
                        identifier='user/profile')

    print(location.full_path)