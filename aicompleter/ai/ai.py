import time
import uuid
from abc import abstractmethod
from typing import Any, Coroutine, Optional

import attr

from aicompleter.config import Config


@attr.s(auto_attribs=True)
class AI:
    '''
    Abstract class for AI
    '''
    name: str
    'AI name'
    islocal: bool = False
    'Is AI local or remote'
    isenabled: bool = True
    'Is AI enabled'
    support:set[str] = {}
    'Supported types of AI'
    location: str = None
    'Location of AI'

    config:Config = attr.ib(factory=Config, on_setattr=attr.setters.convert)
    'Config of AI'

    @property
    def support_text(self):
        return 'text' in self.support
    
    @property
    def support_image(self):
        return 'image' in self.support
    
    @abstractmethod
    async def generate(self, *args, **kwargs):
        '''
        Generate content
        '''
        raise NotImplementedError(f"generate() is not implemented in {self.__class__.__name__}")
    
class Transformer(AI):
    '''
    Abstract class for transformer
    '''
    support = {'text'}
    'Supported types of transformer'
    encoding: str
    'Encoding of transformer'
    max_tokens: int = 2048
    'Max tokens of transformer'

    @abstractmethod
    async def generate_many(self, *args, num:int,  **kwargs) -> Coroutine[list[str], Any, None]:
        '''
        Generate many possible content (if supported)
        '''
        raise NotImplementedError(f"generate_many() is not implemented in {self.__class__.__name__}")

    async def generate_text(self, *args, **kwargs) -> str:
        '''
        Generate text
        '''
        rvalue = ''
        async for value in self.generate(*args, **kwargs):
            rvalue = value
        return rvalue
    
    async def generate_many_texts(self, *args, num:int, **kwargs) -> list[str]:
        '''
        Generate many texts
        '''
        rvalue = []
        async for value in self.generate_many(*args, num=num, **kwargs):
            rvalue = value
        return rvalue
    
@attr.s(auto_attribs=True)
class Message:
    '''
    Message of conversation
    '''
    content:str
    'Content of message'
    role:str
    'Role of message'
    id:Optional[uuid.UUID] = None
    'ID of message'
    user:Optional[str] = None
    'User of message'
    time: float = time.time()
    'Time of message'

    def __str__(self):
        return self.content
    
    def __repr__(self):
        return f"{{content: {self.content}, role: {self.role}, id: {self.id}, user: {self.user}}}"

@attr.s(auto_attribs=True)
class Conversation:
    '''
    Conversation
    '''
    messages:list[Message] = []
    'Messages of conversation'
    id:Optional[uuid.UUID] = None
    'ID of conversation'
    user:Optional[str] = None
    'User of conversation'
    time: float = time.time()
    'Creation time of conversation'

class ChatTransformer(Transformer):
    '''
    Abstract class for Chatable transformer
    '''
    @abstractmethod
    async def generate(self, *args, conversation:Conversation, **kwargs) -> Coroutine[str, Any, None]:
        return super().generate(*args, conversation = conversation, **kwargs)
    
    @abstractmethod
    async def generate_many(self, *args, conversation:Conversation, num:int,  **kwargs) -> Coroutine[list[str], Any, None]:
        '''
        Generate many possible content (if supported)
        '''
        raise NotImplementedError(f"generate_many() is not implemented in {self.__class__.__name__}")
    
    @abstractmethod
    async def ask(self, *args, history:Conversation, message:Message, **kwargs) -> Conversation:
        '''
        Ask a question
        '''
        raise NotImplementedError(f"ask() is not implemented in {self.__class__.__name__}")

class TextTransformer(Transformer):
    '''
    Abstract class for Text transformer
    '''
    @abstractmethod
    async def generate(self, *args, prompt: str, **kwargs) -> Coroutine[str, Any, None]:
        return super().generate(*args, prompt=prompt, **kwargs)

    @abstractmethod
    async def generate_many(self, *args, prompt:str, num:int,  **kwargs) -> Coroutine[list[str], Any, None]:
        '''
        Generate many possible content (if supported)
        '''
        raise NotImplementedError(f"generate_many() is not implemented in {self.__class__.__name__}")