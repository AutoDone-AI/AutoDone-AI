'''
This is a common module for aicompleter
including some template classes
'''

from abc import ABC, abstractmethod
from asyncio import iscoroutine
import asyncio
import threading
from typing import Any, Generic, Optional, Self, TypeVar
import pickle

class BaseTemplate(ABC):
    '''
    A template class for all the template classes in aicompleter
    '''

_T = TypeVar('_T')
class AsyncTemplate(BaseTemplate, Generic[_T]):
    '''
    A template class for all the asynchronous template classes in aicompleter
    :param _T: The type of the synchronous object(if exists)
    '''
    
    # Hook the subclass and add attr __sync_class__
    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        args = [i for i in cls.__orig_bases__ if i.__origin__ == AsyncTemplate][0].__args__
        if len(args) > 0:
            cls.__sync_class__ = args[0]
        else:
            cls.__sync_class__ = None

del _T

class Serializable(BaseTemplate):
    '''
    This class is used to serialize object to string

    Warning: Unsecure and unstable for different python version and program version
    '''
    def serialize(self) -> bytes:
        '''
        Convert to string format
        '''
        return pickle.dumps(self)
    
    @staticmethod
    def deserialize(src: bytes) -> Self:
        '''
        Get a object from a string

        This method will not verify the type of the object, you may not get a object of the same type
        '''
        return pickle.loads(src)

class JSONSerializable(Serializable):
    '''
    This class is used to serialize object to json
    '''
    def serialize(self) -> dict:
        '''
        Convert to json format
        '''
        # Load from __dict__
        return {
            'type': 'class',
            'data': [
                {
                    'key': serialize(key),
                    'value': serialize(value),
                } for key, value in self.__dict__.items()
            ]
        }

    @staticmethod
    @abstractmethod
    def deserialize(src: dict) -> Self:
        '''
        Get a object from a dict

        *Note*: Beacuse it's imposible for static method to get the current type, this method is not implemented
        Implement this below:
        ```py
        @staticmethod
        def deserialize(src: dict) -> Self:
            ret = <class>()
            return ret._deserialize_class(src)
        '''
        raise NotImplementedError('deserialize is not implemented')
    
    @staticmethod
    def _deserialize_class(cls:type, src: dict) -> Self:
        '''
        Get a object from a dict
        '''
        ret = cls.__new__(cls)
        if '__dict__' not in src:
            raise TypeError(f'Cannot deserialize {src}({type(src)}), use method "deserialize" instead')
        ret.__dict__.update({
            deserialize(item['key']): deserialize(item['value']) for item in src['data']
        })
        return ret
    

class Saveable(BaseTemplate):
    '''
    This class is can save object to file
    '''
    @abstractmethod
    def save(self, path: str) -> None:
        '''
        Save to file
        '''
        raise NotImplementedError('save is not implemented')

    @staticmethod
    @abstractmethod
    def load(path: str) -> Self:
        '''
        Load from file
        '''
        raise NotImplementedError('load is not implemented')

class AsyncSaveable(AsyncTemplate[Saveable]):
    '''
    This class is can save object to file asynchronously
    '''
    @abstractmethod
    async def save(self, path: str) -> None:
        '''
        Save to file
        '''
        raise NotImplementedError('save is not implemented')

    @staticmethod
    @abstractmethod
    async def load(path: str) -> Self:
        '''
        Load from file
        '''
        raise NotImplementedError('load is not implemented')

class ContentManager(BaseTemplate):
    '''
    This class is a template for content manager
    '''
    def __enter__(self) -> Any:
        '''
        Enter the context
        '''
        if hasattr(self, 'acquire') and callable(self.acquire):
            self.acquire()
        raise NotImplementedError('enter is not implemented')
    
    def __exit__(self, exc_type, exc_value, traceback) -> None:
        '''
        Exit the context
        '''
        if hasattr(self, 'release') and callable(self.release):
            self.release()
        raise NotImplementedError('exit is not implemented')
    
class AsyncContentManager(AsyncTemplate[ContentManager]):
    '''
    This class is a template for asynchronous content manager
    '''
    async def __aenter__(self) -> Any:
        '''
        Enter the context
        '''
        if hasattr(self, 'acquire') and callable(self.acquire):
            await self.acquire()
        raise NotImplementedError('enter is not implemented')
    
    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        '''
        Exit the context
        '''
        if hasattr(self, 'release') and callable(self.release):
            ret = self.release()
            if iscoroutine(ret):
                return await ret
        raise NotImplementedError('exit is not implemented')

class LifeTimeManager(BaseTemplate):
    '''
    This class is a template for lifetime manager
    '''
    def __init__(self) -> None:
        super().__init__()
        self._close_event:threading.Event = threading.Event()

    @property
    def closed(self) -> bool:
        '''
        Whether the object is closed
        '''
        return self._close_event.is_set()
    
    def close(self) -> None:
        '''
        Close the object
        '''
        self._close_event.set()

    def wait_close(self) -> None:
        '''
        Wait until the object is closed
        '''
        self._close_event.wait()

class AsyncLifeTimeManager(AsyncTemplate[LifeTimeManager]):
    '''
    This class is a template for asynchronous lifetime manager
    '''
    def __init__(self) -> None:
        super().__init__()
        self._close_event:asyncio.Event = asyncio.Event()
        '''
        The close event
        '''
        self._close_tasks:set[asyncio.Future] = set()
        '''
        The tasks that will be waited when the object is closed
        '''

    @property
    def closed(self) -> bool:
        '''
        Whether the object is closed
        '''
        return self._close_event.is_set()
    
    def close(self) -> None:
        '''
        Close the object
        '''
        for task in self._close_tasks:
            if not task.done():
                task.cancel()
        self._close_event.set()

    async def wait_close(self) -> None:
        '''
        Wait until the object is closed
        '''
        await self._close_event.wait()
        for task in self._close_tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*self._close_tasks)

def serialize(data:Any, pickle_all:bool = False) -> Any:
    '''
    Convert to serial format (in json)

    :param data: The data to be serialized
    :param pickle_all: Whether to pickle all the data, this is dangerous because it will execute the code in the data
    '''
    if isinstance(data, Serializable):
        return {
            'type': 'serial',
            'subtype': 'class',
            'module': data.__module__,
            'class': data.__class__.__qualname__,
            'data': data.serialize(),
        }
    elif isinstance(data, (list, set, tuple)):
        subtype = 'list' if isinstance(data, list) else 'set' if isinstance(data, set) else 'tuple'
        return {
            'type': 'serial',
            'subtype': subtype,
            'data': [serialize(item) for item in data],
        }
    elif isinstance(data, dict):
        return {
            'type': 'serial',
            'subtype': 'dict',
            'data': [{
                'key': serialize(key),
                'value': serialize(value),
            } for key, value in data.items()],
        }
    elif isinstance(data, (int, float, str, bool, type(None), bytes)):
        subtype = data.__class__.__qualname__
        if subtype not in ('int', 'float', 'str', 'bool', 'NoneType', 'bytes'):
            if pickle_all:
                return {
                    'type': 'serial',
                    'subtype': 'pickle',
                    'data': pickle.dumps(data),
                }
            raise TypeError(f'Cannot serialize {data}({type(data)}), this class is inherited from {subtype}')
        return {
            'type': 'serial',
            'subtype': subtype,
            'data': data,
        }
    else:
        if pickle_all:
            return {
                'type': 'serial',
                'subtype': 'pickle',
                'data': pickle.dumps(data),
            }
        raise TypeError(f'Cannot serialize {data}({type(data)})')

def deserialize(data:dict, global_:Optional[dict[str, Any]] = None, unpickle_all:bool = False) -> Any:
    '''
    Get a object from serial format (in json)

    :param data: The data to be deserialized
    :param global_: The global variables, if none, will try import the module(warning: this is dangerous)
    :param unpickle_all: Whether to unpickle all the data, this is dangerous because it will execute the code in the data
    '''
    if data['type'] != 'serial':
        raise TypeError(f'Cannot deserialize {data}({type(data)})')
    subtype = data['subtype']
    if subtype == 'class':
        if global_ is None:
            import importlib
            module_ = importlib.import_module(data['module'])
            # Split the submodule
            for i in data['class'].split('.'):
                module_ = getattr(module_, i)
            cls = module_
        else:
            cls = global_
            for i in data['class'].split('.'):
                cls = cls[i]
        return cls.deserialize(data['data'])
    elif subtype in ('list', 'set', 'tuple'):
        return globals()[subtype]([deserialize(item) for item in data['data']])
    elif subtype == 'dict':
        return {deserialize(item['key']): deserialize(item['value']) for item in data['data']}
    elif subtype in ('int', 'float', 'str', 'bool', 'NoneType', 'bytes'):
        return data['data']
    elif subtype == 'pickle':
        if unpickle_all:
            return pickle.loads(data['data'])
        raise TypeError(f'Cannot deserialize {data}({type(data)}), this class is inherited from {subtype}')
    else:
        raise TypeError(f'Cannot deserialize {data}({type(data)})')

__all__ = (
    'BaseTemplate',
    *(
        i.__name__ for i in globals().values() if isinstance(i, type) and issubclass(i, BaseTemplate)
    ),

    'serialize',
    'deserialize',
)
