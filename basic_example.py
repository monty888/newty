import logging
import PySimpleGUI as sg
from PySimpleGUI import Element, Button

import gc
import asyncio
import time
from threading import Thread
from monstr.client.client import Client
from monstr.client.event_handlers import PrintEventHandler
from monstr.ident.event_handlers import NetworkedProfileEventHandler
from monstr.encrypt import Keys


class NostrBackground(Thread):

    def __init__(self, **kargs):
        self._run = True
        self._loop = asyncio.new_event_loop()

        # self._client = Client('ws://localhost:8081')
        self._client = Client('wss://nos.lol')
        # asyncio.create_task(self._client.run())
        super().__init__(target=self.run, args=(self._loop,))

    def run(self):
        print('loop started')
        self._loop.run_until_complete(self._client.run())
        print('loop ended')

    @property
    def client(self) ->Client:
        return self._client

    def stop(self):
        self._client.end()



async def test_example():

    my_background = NostrBackground()
    my_background.start()

    sg.theme('DarkAmber')   # Add a touch of color
    # All the stuff inside your window.
    layout = [  [sg.Text('npub/nsec'), sg.InputText(key='keyIn')],
                [sg.Button('Ok', key='okBut')] ]

    # Create the Window
    window = sg.Window('Window Title', layout)
    # Event Loop to process "events" and get the "values" of the inputs

    # my_background.client.subscribe(filters=[{'limit': 2}], handlers=[PrintEventHandler()])
    peh = NetworkedProfileEventHandler(client=my_background.client)
    ph = PrintEventHandler(max_length=80,
                           profile_handler=peh)

    while True:
        event, values = window.read(10)

        if event == sg.WIN_CLOSED:
            break
        elif event == 'okBut':
            n_key = Keys.get_key(values['keyIn'])
            if n_key is not None:
                asyncio.create_task(my_background.client.query(filters={
                        'authors': [n_key.public_key_hex()],
                        'limit': 10
                    },
                    do_event=ph.do_event))

        await asyncio.sleep(0.1)

    my_background.stop()
    window.close()
    layout = None
    window = None
    gc.collect()

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    asyncio.run(test_example())


