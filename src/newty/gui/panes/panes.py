from abc import abstractmethod
from PySide2.QtWidgets import (
    QWidget,
    QVBoxLayout
)

from newty.gui.nostr import Location


class ViewPane(QWidget):

    def __init__(self,
                 location: Location,
                 *args,
                 **kargs):
        super(ViewPane, self).__init__(*args, **kargs)
        self._location = location
        self._layout = QVBoxLayout()
        self.setLayout(self._layout)

    @abstractmethod
    def stop(self):
        """
        for example unregister any subscriptions and end anyother task, won't be restarted after this
        """

    @abstractmethod
    def pause(self):
        """
        for example unregister any subscriptions, can be restarted
        """

    @abstractmethod
    def restart(self):
        """
        for example re-register any subscriptions, call after pause
        """

    @property
    def location(self) -> Location:
        return self._location