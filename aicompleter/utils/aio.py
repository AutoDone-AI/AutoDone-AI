
import asyncio
from concurrent.futures import ThreadPoolExecutor

_on_reading:asyncio.Lock = asyncio.Lock()
'''
Global asyncio lock for console input
'''

async def ainput(prompt: str = "") -> str:
    '''
    Async input
    '''
    async with _on_reading:
        with ThreadPoolExecutor(1, "AsyncInput") as executor:
            return (await asyncio.get_event_loop().run_in_executor(executor, input, prompt)).rstrip()

async def aprint(string: str) -> None:
    '''
    Async print
    '''
    await _on_reading.acquire()
    print(string)
    _on_reading.release()
