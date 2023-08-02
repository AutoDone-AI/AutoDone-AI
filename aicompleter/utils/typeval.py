'''
For Annotation Type Checking
'''
import functools
import inspect
import typing
from typing import Type

__all__ = (
    'is_generic',
    'is_base_generic',
    'is_qualified_generic',
    'get_base_generic',
    'get_subtypes',
    'is_instance',
    'is_subtype',
    'python_type',
    'verify'
)

def _is_generic(cls):
    if isinstance(cls, typing._GenericAlias):
        return True

    if isinstance(cls, typing._SpecialForm):
        return cls not in (
            typing.Never,
            typing.NoReturn,
            typing.Self,
        )

    return False


def _is_base_generic(cls):
    if isinstance(cls, typing._GenericAlias):
        if cls.__origin__ in {typing.Generic, typing.Protocol}:
            return False

        # if isinstance(cls, typing._VariadicGenericAlias):
        #     return True

        return len(cls.__parameters__) > 0

    if isinstance(cls, typing._SpecialForm):
        return cls._name in {'ClassVar', 'Union', 'Optional'}

    return False


def _get_base_generic(cls):
    # subclasses of Generic will have their _name set to None, but
    # their __origin__ will point to the base generic
    if cls._name is None:
        return cls.__origin__
    else:
        return getattr(typing, cls._name)


def _get_python_type(cls):
    """
    Like `python_type`, but only works with `typing` classes.
    """
    return cls.__origin__


def _get_name(cls):
    return cls._name

def _get_subtypes(cls):
    subtypes = cls.__args__

    if get_base_generic(cls) is typing.Callable:
        if len(subtypes) != 2 or subtypes[0] is not ...:
            subtypes = (subtypes[:-1], subtypes[-1])

    return subtypes

def is_generic(cls):
    """
    Detects any kind of generic, for example `List` or `List[int]`. This includes "special" types like
    Union and Tuple - anything that's subscriptable, basically.
    """
    return _is_generic(cls)

def is_base_generic(cls):
    """
    Detects generic base classes, for example `List` (but not `List[int]`)
    """
    return _is_base_generic(cls)

def is_qualified_generic(cls):
    """
    Detects generics with arguments, for example `List[int]` (but not `List`)
    """
    return is_generic(cls) and not is_base_generic(cls)

def get_base_generic(cls):
    if not is_qualified_generic(cls):
        raise TypeError('{} is not a qualified Generic and thus has no base'.format(cls))

    return _get_base_generic(cls)

def get_subtypes(cls):
    return _get_subtypes(cls)

def _instancecheck_iterable(iterable, type_args):
    if len(type_args) != 1:
        raise TypeError("Generic iterables must have exactly 1 type argument; found {}".format(type_args))

    type_ = type_args[0]
    return all(is_instance(val, type_) for val in iterable)

def _instancecheck_mapping(mapping, type_args):
    return _instancecheck_itemsview(mapping.items(), type_args)

def _instancecheck_itemsview(itemsview, type_args):
    if len(type_args) != 2:
        raise TypeError("Generic mappings must have exactly 2 type arguments; found {}".format(type_args))

    key_type, value_type = type_args
    return all(is_instance(key, key_type) and is_instance(val, value_type) for key, val in itemsview)

def _instancecheck_tuple(tup, type_args):
    if len(tup) != len(type_args):
        return False

    return all(is_instance(val, type_) for val, type_ in zip(tup, type_args))

_ORIGIN_TYPE_CHECKERS = {}
for class_path, check_func in {
                        # iterables
                        'typing.Container': _instancecheck_iterable,
                        'typing.Collection': _instancecheck_iterable,
                        'typing.AbstractSet': _instancecheck_iterable,
                        'typing.MutableSet': _instancecheck_iterable,
                        'typing.Sequence': _instancecheck_iterable,
                        'typing.MutableSequence': _instancecheck_iterable,
                        'typing.ByteString': _instancecheck_iterable,
                        'typing.Deque': _instancecheck_iterable,
                        'typing.List': _instancecheck_iterable,
                        'typing.Set': _instancecheck_iterable,
                        'typing.FrozenSet': _instancecheck_iterable,
                        'typing.KeysView': _instancecheck_iterable,
                        'typing.ValuesView': _instancecheck_iterable,
                        'typing.AsyncIterable': _instancecheck_iterable,

                        # mappings
                        'typing.Mapping': _instancecheck_mapping,
                        'typing.MutableMapping': _instancecheck_mapping,
                        'typing.MappingView': _instancecheck_mapping,
                        'typing.ItemsView': _instancecheck_itemsview,
                        'typing.Dict': _instancecheck_mapping,
                        'typing.DefaultDict': _instancecheck_mapping,
                        'typing.Counter': _instancecheck_mapping,
                        'typing.ChainMap': _instancecheck_mapping,

                        # other
                        'typing.Tuple': _instancecheck_tuple,
                    }.items():
    try:
        cls = eval(class_path)
    except AttributeError:
        continue

    _ORIGIN_TYPE_CHECKERS[cls] = check_func


def _instancecheck_callable(value, type_):
    if not callable(value):
        return False

    if is_base_generic(type_):
        return True

    param_types, ret_type = get_subtypes(type_)
    sig = inspect.signature(value)

    missing_annotations = []

    if param_types is not ...:
        if len(param_types) != len(sig.parameters):
            return False

        # FIXME: add support for TypeVars

        # if any of the existing annotations don't match the type, we'll return False.
        # Then, if any annotations are missing, we'll throw an exception.
        for param, expected_type in zip(sig.parameters.values(), param_types):
            param_type = param.annotation
            if param_type is inspect.Parameter.empty:
                missing_annotations.append(param)
                continue

            if not is_subtype(param_type, expected_type):
                return False

    if sig.return_annotation is inspect.Signature.empty:
        missing_annotations.append('return')
    else:
        if not is_subtype(sig.return_annotation, ret_type):
            return False

    if missing_annotations:
        raise ValueError("Missing annotations: {}".format(missing_annotations))

    return True


def _instancecheck_union(value, type_):
    types = get_subtypes(type_)
    return any(is_instance(value, typ) for typ in types)

def _instancecheck_optional(value, type_):
    if len(type_.__args__) != 2:
        raise TypeError("Optional must have exactly 2 type arguments; found {}".format(type_.__args__))

    type_arg = type_.__args__[0]
    return value is None or is_instance(value, type_arg)

def _instancecheck_type(value, type_):
    # if it's not a class, return False
    if not isinstance(value, type):
        return False

    if is_base_generic(type_):
        return True

    type_args = get_subtypes(type_)
    if len(type_args) != 1:
        raise TypeError("Type must have exactly 1 type argument; found {}".format(type_args))

    return is_subtype(value, type_args[0])


_SPECIAL_INSTANCE_CHECKERS = {
    'Union': _instancecheck_union,
    'Callable': _instancecheck_callable,
    'Type': _instancecheck_type,
    'Any': lambda v, t: True,
    'Optional': _instancecheck_optional,
}

_BUILTINS_CLASS_MAP = {
    list: typing.List,
    set: typing.Set,
    dict: typing.Dict,
    tuple: typing.Tuple,
}

def is_instance(obj, type_):
    '''
    Check if an object is an instance of a type annotation
    This function will check the subtypes of a qualified generic type annotation

    Examples:
    ::
        >>> is_instance(1, int)
        True
        >>> is_instance(1, typing.Union[int, str])
        True
        >>> is_instance(1, typing.Union[str, float])
        False
    ::
    '''
    if type_ in _BUILTINS_CLASS_MAP:
        ntype_ = _BUILTINS_CLASS_MAP[type_]

    if hasattr(type_, '__origin__') and type_.__origin__ in _BUILTINS_CLASS_MAP:
        ntype_ = _BUILTINS_CLASS_MAP[type_.__origin__]

    if 'ntype_' in locals():
        if hasattr(type_, '__args__'):
            ntype_.__args__ = type_.__args__
        type_ = ntype_

    if type_.__module__ == 'typing':
        if is_qualified_generic(type_):
            base_generic = get_base_generic(type_)
        else:
            base_generic = type_
        name = _get_name(base_generic)

        try:
            validator = _SPECIAL_INSTANCE_CHECKERS[name]
        except KeyError:
            pass
        else:
            return validator(obj, type_)

    if is_base_generic(type_):
        python_type = _get_python_type(type_)
        return isinstance(obj, python_type)

    if is_qualified_generic(type_):
        python_type = _get_python_type(type_)
        if not isinstance(obj, python_type):
            return False

        base = get_base_generic(type_)
        try:
            validator = _ORIGIN_TYPE_CHECKERS[base]
        except KeyError:
            raise NotImplementedError("Cannot perform isinstance check for type {}".format(type_))

        type_args = get_subtypes(type_)
        return validator(obj, type_args)

    return isinstance(obj, type_)

def is_subtype(sub_type, super_type):
    if not is_generic(sub_type):
        python_super = python_type(super_type)
        return issubclass(sub_type, python_super)

    # at this point we know `sub_type` is a generic
    python_sub = python_type(sub_type)
    python_super = python_type(super_type)
    if not issubclass(python_sub, python_super):
        return False

    # at this point we know that `sub_type`'s base type is a subtype of `super_type`'s base type.
    # If `super_type` isn't qualified, then there's nothing more to do.
    if not is_generic(super_type) or is_base_generic(super_type):
        return True

    # at this point we know that `super_type` is a qualified generic... so if `sub_type` isn't
    # qualified, it can't be a subtype.
    if is_base_generic(sub_type):
        return False

    # at this point we know that both types are qualified generics, so we just have to
    # compare their sub-types.
    sub_args = get_subtypes(sub_type)
    super_args = get_subtypes(super_type)
    return all(is_subtype(sub_arg, super_arg) for sub_arg, super_arg in zip(sub_args, super_args))


def python_type(annotation):
    """
    Given a type annotation or a class as input, returns the corresponding python class.

    Examples:

    ::
        >>> python_type(typing.Dict)
        <class 'dict'>
        >>> python_type(typing.List[int])
        <class 'list'>
        >>> python_type(int)
        <class 'int'>
    """
    try:
        mro = annotation.mro()
    except AttributeError:
        # if it doesn't have an mro method, it must be a weird typing object
        return _get_python_type(annotation)

    if Type in mro:
        return annotation.python_type
    elif annotation.__module__ == 'typing':
        return _get_python_type(annotation)
    else:
        return annotation

def verify(func=None, /, check_parameters:bool = True, check_return:bool = False):
    '''
    Verify the type of parameters and return value when calling a function

    Examples:
    ::
        >>> @verify
        >>> def func(param1, param2: int, param3: str = '', *args: int, param5: Optional[str] = None, param6: list[int|str] = []) -> tuple[int|str]:
        >>>     return (param1, param2, param3, *args, param5, param6)
        
        >>> print(func(1,2,'3', param6=[1,2,3]))
    '''
    if func == None:
        return functools.partial(verify, check_parameters=check_parameters, check_return=check_return)
    if not callable(func):
        raise TypeError('func must be callable')
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        sig = inspect.signature(func)
        if check_parameters:
            bind = sig.bind(*args, **kwargs)
            bind.apply_defaults()
            for name, value in bind.arguments.items():
                if sig.parameters[name].annotation != sig.empty:
                    if not is_instance(value, sig.parameters[name].annotation):
                        raise TypeError(f"Parameter {name} is not {sig.parameters[name].annotation}")
        result = func(*args, **kwargs)
        if check_return:
            if sig.return_annotation != sig.empty:
                if not is_instance(result, sig.return_annotation):
                    raise TypeError(f"Return value is not {sig.return_annotation}")
        return result
    return wrapper