import uuid
from typing import Any, Coroutine, Optional
from aicompleter.interface.base import User
import aicompleter.session as session
from .. import *

class PythonCodeInterface(Interface):
    '''
    This interface is designed to execute python code
    '''
    def __init__(self, user: Optional[User] = None, namespace: str = 'pythoncode', id: uuid.UUID = ...):
        user = user or User(
            name='pythoncode',
            in_group='system',
            description='Execute python code',
        )
        super().__init__(user, namespace, id)
        self.commands.add(Command(
            cmd='exec',
            description='Execute python code, the environments and varibles will be persevered in this conversation.You can use set_result(result) method to set the result of the code.',
            format=CommandParamStruct({
                'code': CommandParamElement(name='code', type=str, description='Python code to execute.', tooltip='code'),
                'type': CommandParamElement(name='type', type=str, description='Type of the code, can be "exec" or "eval".', tooltip='exec/eval (default to exec)', default='exec', optional=True)
            }),
            callable_groups={'user','agent'},
            force_await=True,
            to_return=True,
            callback=self.cmd_exec,
        ))

    async def session_init(self, session: Session) -> Coroutine[Any, Any, None]:
        ret = await super().session_init(session)
        # Create a new globals
        session.data[self.namespace.name]['globals'] = {
            '__name__': '__main__',
            '__doc__': None,
            '__package__': None,
            '__loader__': globals()['__loader__'],
            '__spec__': None,
            '__annotations__': {},
            '__builtins__': __import__('builtins'),
        }

    async def cmd_exec(self, session: Session, message: Message):
        '''
        Execute python code
        '''
        func = eval if message.content.json['type'] == 'eval' else exec
        old_dict = dict(session.data[self.namespace.name]['globals'])
        result = ...
        def set_result(res):
            nonlocal result
            result = res
        old_dict['set_result'] = set_result
        ret = func(message.content.json['code'], old_dict)
        session.data[self.namespace.name]['globals'] = old_dict
        if ret != None:
            return ret
        last_sentence = message.content.json['code'].splitlines()[-1].strip()
        if message.content.json['type'] == 'eval':
            return ret
        # Check if it's a variable of the function result
        if result != ...:
            return result
        if set(last_sentence) <= set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_0123456789[].:'):
            try:
                return old_dict[last_sentence]
            except KeyError:
                return None
        return None
    