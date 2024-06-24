import asyncio
import aiohttp
import logging
from cachetools import TTLCache, LRUCache


class ResourceFetcher:
    """
        very basic http resource fetcher, with a LRU cache
    """
    def __init__(self):
        self._cache = LRUCache(10000)

        self._in_progress = {}

    async def get(self, url):
        if url in self._cache:
            ret = self._cache[url]
        else:
            if url not in self._in_progress:
                self._in_progress[url] = True
                self._cache[url] = ret = await self._do_fetch(url)

            else:

                timeout = 10.0
                wait_time = 0
                while url not in self._cache:
                    if wait_time >= timeout:
                        raise Exception(f'timeout loading resource {url}')
                    await asyncio.sleep(0.1)
                    wait_time += 0.1

                # if we didn't throw it should exist by now
                ret = self._cache[url]


        return ret

    async def _do_fetch(self, url):
        ret = None
        async with aiohttp.ClientSession(headers={
            'Accept': 'image/*'
        }) as session:

            retry_count = 5
            attempt = 1
            wait_time = 1

            while ret is None and attempt <= retry_count:
                try:
                    async with session.get(url) as response:
                        if response.status == 200:
                            ret = await response.read()
                            self._cache[url] = ret

                except Exception as e:
                    # note we just continue without relay specific info... maybe do some better fullback
                    logging.debug(f'ResourceFetcher::get failed: {e} for {url}')
                    retry_count += 1
                    await asyncio.sleep(wait_time)
                    wait_time *= 2

            self._in_progress[url] = False

        return ret

    def __contains__(self, url):
        return url in self._cache

    def __getitem__(self, url):
        return self._cache[url]


async def test_resource_fetch():
    my_resources = ResourceFetcher()
    print(await my_resources.get('https://oxtr.dev/assets/profilepic-animated-small.gif'))


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.DEBUG)
    asyncio.run(test_resource_fetch())