import asyncio
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import aicompleter as ac
from aicompleter import Config, utils
import uuid
from aicompleter.test import quick as q
import pytest

@pytest.mark.run(order=0x50)
@pytest.mark.dependency(depends=["test/test_command.py::test_BaseCommand"], scope='session')
def test_BaseInterface():
    # If import successfully, the creation of interface is passed
    from aicompleter.test import quick as q
    nul = q.null_interface
    assert isinstance(nul, ac.Interface)
    @nul.register('test', 'test')
    async def test():
        return 'test'
    assert nul.run('test') == 'test'

    @nul.register('test2', 'test2', format=ac.CommandParamStruct({
        'key': ac.CommandParam('key', type=int),
        'key2': ac.CommandParam('key2', type=str, default='default', optional=True),
    }))
    def test2(key, key2):
        return key, key2
    assert nul.run('test2', key = 1, key2 = '2') == (1, '2')
    # For now, the run method do not support structal call

@pytest.mark.run(order=0x51)
@pytest.mark.dependency(depends=['test_BaseInterface'])
def test_InterfaceInherit():
    class ConfigModel(ac.ConfigModel):
        a: str
        b: int
        c: list
        d: dict
    class DataModel(ac.DataModel):
        a: str
    class TestInterface(ac.Interface):
        cmdreg:ac.Commands = ac.Commands()
        configFactory = ConfigModel
        dataFactory = DataModel

        def __init__(self, config:Config() = Config()):
            super().__init__(
                namespace='test',
                user = ac.User(
                    name = 'test',
                    description='test',
                    id = uuid.uuid4(),
                    in_group='test',
                    support={'test'},
                ),
                id = uuid.uuid4(),
                config = config,
            )

        @cmdreg.register('test', 'test')
        async def test(self):
            return 'test'
        
        @cmdreg.register('test2', 'test2', format=ac.CommandParamStruct({
            'key': ac.CommandParam('key', type=int),
            'key2': ac.CommandParam('key2', type=str, default='default', optional=True),
        }))
        def test2(self, key, key2):
            return key, key2
        
    test = TestInterface()
    assert test.namespace.name == 'test'

    assert test.commands['test'].name == 'test'
    assert test.commands['test2'].name == 'test2'

    assert len(test.commands) == 2

@pytest.mark.run(order=0x52)
@pytest.mark.dependency(depends=["test/test_config.py::test_Config", "test/test_handler.py::test_BaseInterface"], scope='session')
def test_BaseHandler():
    handler = ac.Handler()
    handler = ac.Handler(config=ac.Config({
        'global': {},
        'namespace1': {
            'a': 'b',
        },
    }))
    async def _intest():
        await handler.add_interface(q.null_interface)
        handler.reload()
        assert handler.interfaces[0] == q.null_interface
        # Do more thing on hard test
    asyncio.run(_intest())

@pytest.mark.run(order=0x53)
@pytest.mark.dependency(depends=['test_BaseHandler'])
def test_InterfaceCommand():
    class TestInterface(ac.Interface):
        cmdreg:ac.Commands = ac.Commands()
        def __init__(self):
            super().__init__(
                namespace='test',
                user = ac.User(
                    name = 'test',
                    description='test',
                    id = uuid.uuid4(),
                    in_group='test',
                    support={'test'},
                ),
                id = uuid.uuid4(),
                config = Config(),
            )

        @cmdreg.register('test', 'test')
        def test(self):
            return 'test'
        
        @cmdreg.register('test2', 'test2', format=ac.CommandParamStruct({
            'key': ac.CommandParam('key', type=int),
            'key2': ac.CommandParam('key2', type=str, default='default', optional=True),
        }))
        async def test2(self, key, key2, session:ac.Session):
            return key, key2
        
    @TestInterface.cmdreg.register('test3', format=ac.CommandParamStruct({
        'key': ac.CommandParam('key', type=int),
    }))
    async def test3(key, session, interface, message, config, data):
        assert isinstance(key, int)
        assert isinstance(session, ac.Session)
        assert isinstance(interface, TestInterface)
        assert isinstance(message, ac.Message)
        assert isinstance(config, Config)
        assert isinstance(data, utils.EnhancedDict)
        return True

    test = TestInterface()
    handler = ac.Handler()
    async def _intest():
        await handler.add_interface(test)

        session = await handler.new_session()
        assert await session.asend('test') == 'test'
        assert await session.asend('test2', {'key': 1, 'key2': '2'}) == (1, '2')
        assert await session.asend('test3', {'key': 1}) == True

    asyncio.run(_intest())