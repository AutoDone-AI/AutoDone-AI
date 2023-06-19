import os
import asyncio
from aicompleter import *
from aicompleter.config import Config
from aicompleter.utils import ainput,aprint
from aicompleter.implements import ConsoleInterface
from . import log

__DEBUG__:bool = False
'''
For debug
'''
os.environ.setdefault('DEBUG', "False")
if os.environ['DEBUG'] == "True":
    __DEBUG__ = True

logger = log.Logger("Main")
formatter = log.Formatter()
handler = log.ConsoleHandler()
handler.formatter = formatter
logger.addHandler(handler)
if __DEBUG__:
    logger.setLevel(log.DEBUG)
else:
    logger.setLevel(log.INFO)

_handler:Handler = None
async def main():
    # Read Config
    logger.info("Start Executing")
    if not os.path.exists("config.json"):
        logger.debug("config.json Not Found. Use default config.")
        config = Config()
    else:
        logger.debug("config.json Found. Reading config.json")
        config = Config.loadFromFile("config.json")
    config.setdefault("global.debug", False)
    if config["global.debug"]:
        __DEBUG__ = True
        os.environ['DEBUG'] = "True"

    config['openaichat'].update(config['global'])
    
    consoleinterface:ConsoleInterface = ConsoleInterface()
    chater = ai.openai.Chater('gpt-3.5-turbo-0301', config['openaichat'])
    chatinterface:ai.ChatInterface = ai.ChatInterface(ai=chater, namespace='openaichat')
    hand:Handler = Handler(config)

    await hand.add_interface(consoleinterface, chatinterface)
    session:Session = await hand.new_session()
    ret = None
    while True:
        text = await session.asend(Message(
            cmd='ask',
            session=session,
            dest_interface=consoleinterface,
            content=ret if ret else "Start Your Conversation",
        ))
        ret = await session.asend(Message(
            cmd='ask',
            session=session,
            src_interface=chatinterface,
            dest_interface=chatinterface,
            content=text,
        ))


loop = asyncio.new_event_loop()
if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
try:
    loop.create_task(main())
    loop.run_forever()
except KeyboardInterrupt:
    logger.info("KeyboardInterrupt")
    # loop.stop()
    # loop.run_until_complete(_handler.close())
    loop.stop()
    for task in asyncio.all_tasks(loop):
        task.cancel()
    loop.run_forever()
    loop.stop()
    loop.close()
