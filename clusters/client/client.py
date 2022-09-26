import aiohttp
from aiohttp import WSMsgType

from yarl import URL

class Websocket:
    def __init__(self, client, host: str, port: int = None, key: str = "", secure: bool = False, client_session = None):
        self.client = client
        self._uri = URL.build(scheme="ws" + ("s" * secure), host = host, port = port)
        self.key = key
        if client_session:
            self.session = client_session
        else:
            self.session = aiohttp.ClientSession()

        self._ws = None
        self._listener = None

    @property
    def closed(self):
        return self._ws is not None and not self._ws.closed

    @property
    def websocket(self):
        return self._ws

    async def connect(self):
        self._ws = await self.session.ws_connect(self._uri)

    async def _listen(self):
        while True:
            msg = await self._ws.receive()
            if msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.CLOSED):
                pass
            else:
                pass



# class SharderClient:
#     def __init__(self, url, processor):
#         self.url = url
#         self.processor = processor
#         self.loop = asyncio.get_event_loop()

#     async def connect(self):
#         async with self.session.ws_connect(self.url) as ws: