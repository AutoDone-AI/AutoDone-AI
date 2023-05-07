import asyncio
from typing import Any
from autodone import interface
from autodone.interface.base import Character
from autodone.session import Session, Message
import uuid
import json
import error
from autodone.utils import Struct

class InitInterface(interface.Interface):
    '''
    Initializer Interface
    Only used for initializing the session request
    '''
    def __init__(self, character: Character, id: uuid.UUID = uuid.uuid4()):
        super().__init__(character, id)

    async def cmd_init(self, session:Session, message:Message):
        '''
        Init the session
        '''
        try:
            data = json.loads(message.content.text)
        except json.JSONDecodeError:
            raise error.MessageNotUnderstood(message, self)
        if not Struct({
            "interface-name":str,
            "command":str,
            "data":Any,
        }).check(data):
            raise error.MessageNotUnderstood(message, self)
        for i in session.in_handler:
            if i.character.name == data["interface-name"]:
                break
        if i.character.name != data["interface-name"]:
            raise error.NotFound("Interface Not Found",message=message, interface=self, data=data)
        if not i.commands.has(data["command"]):
            raise error.MessageNotUnderstood(message, self)
        cmd = i.commands.get(data["command"])
        if not cmd.callable_roles.has(self.character.role):
            raise error.PermissionDenied(message, self)
        message.cmd = cmd
        message.content = data["data"]
        message.src_interface = self
        message.dest_interface = i
        session.in_handler.call_soon(session, message)

    async def init(self):
        '''
        Initialize this interface
        Add commands for first call to handler
        '''
        self.commands.add(
            interface.Command(
                cmd="init",
                description="Initialize the session",
                callable_roles=set(),
                # No one can call this command, it's only used for initializing
                # and pass the message to the right interface
                overrideable=True,
                expose=False,
                in_interface=self,
                call=self.cmd_init,
            )
        )
        
