"""This module contains wrappers for creating and managing objects in a multiprocessing context.
"""
import multiprocessing
from multiprocessing import (Process, Pipe)
from multiprocessing.connection import Connection
import weakref
from dataclasses import dataclass

@dataclass(init=True)
class SIGNALS:
    SHUTDOWN: bool = False
    INIT: bool = False


@dataclass(init=True)
class TASK_STRUCT:
    SIGNAL: SIGNALS = None
    TASK: str = ""
    TASK_ARGS: tuple = None
    TASK_KWARGS: dict = None
    TEST_CALL: bool = False

class MultiProcRunner:
    def __init__(self, conn:Connection, wrapped_cls: type, /, *args: tuple, **kwargs: dict):
        self._conn = conn 
        self._wrapped_cls = wrapped_cls
        self._init_args = args
        self._init_kwargs = kwargs
        self._proc = Process(target=self._main)
        self._proc.start()

    def _main(self):
        """main loop, this will run indefinitely to process calls and return values"""
        obj = self._wrapped_cls(*self._init_args, **self._init_kwargs)
        init_sig = self._conn.recv()
        if not isinstance(init_sig, TASK_STRUCT):
            raise RuntimeError(f"Expected a TASK_STRUCT but got {type(init_sig)}")
        ok = not init_sig.SIGNAL.SHUTDOWN
        if not init_sig.SIGNAL.INIT:
            print("No init in signal, exiting _main")
            return
        while ok:
            sig = self._conn.recv()
            if not isinstance(sig, TASK_STRUCT):
                raise RuntimeError(f"Expected a TASK_STRUCT but got {type(init_sig)}")
            if sig.SIGNAL.SHUTDOWN:
                break
            attr = sig.TASK
            if hasattr(obj, attr):
                attr = getattr(obj, attr)
                if sig.TEST_CALL:
                    self._conn.send(attr)
                else:
                    ret = attr(*sig.TASK_ARGS, **sig.TASK_KWARGS)
                    self._conn.send(ret)
            else:
                print(f"Instance of class {obj.__class__} has no attribute {attr}")
                self._conn.send(None)

    def __del__(self):
        self._proc.terminate()
        self._proc.close()


class MultiProcCls:
    """This wrapper is useful if you want to initialize multiple instances of a class
    that runs in a separate process, but needs to be accessed just like an object in main process
    """
    def __init__(self, wrapped_cls: type, /, *args: tuple, **kwargs: dict):
        if not isinstance(wrapped_cls, type):
            raise RuntimeError(f"Expected wrapped_cls to be a class, but got {type(wrapped_cls)}")
        self._proc = None
        _conn, conn = Pipe()
        self._runner = MultiProcRunner(conn, wrapped_cls, *args, **kwargs)
        self._cache_map = dict()
        self._conn =_conn
        sig = SIGNALS(SHUTDOWN=False, INIT=True)
        init_sig = TASK_STRUCT(SIGNAL=sig)
        _conn.send(init_sig)

    def __getattribute__(self, name):
        if name in ("_proc", "_conn", "_runner", "_cache_map"):
            return super(MultiProcCls, self).__getattribute__(name)
        
        callable_ = self._cache_map.get(name, False)
        in_map = name in self._cache_map
        if not callable_ and in_map:
            sig = TASK_STRUCT(TASK=name, TEST_CALL=True, SIGNAL=SIGNALS(SHUTDOWN=False, INIT=False))
            self._conn.send(sig)
            return self._conn.recv()
        elif not callable_ and not in_map:
            sig = TASK_STRUCT(TASK=name, TEST_CALL=True, SIGNAL=SIGNALS(SHUTDOWN=False, INIT=False))
            self._conn.send(sig)
            ret = self._conn.recv()
            callable_ = callable(ret)
            self._cache_map[name] = callable_
            if not callable_:
                return ret
            else:
                def wrapped_fnc(*args, **kwargs):
                    sig = TASK_STRUCT(TASK=name, TEST_CALL=False, TASK_ARGS=args, TASK_KWARGS=kwargs,
                                      SIGNAL=SIGNALS(SHUTDOWN=False, INIT=False))
                    self._conn.send(sig)
                    return self._conn.recv()
                return wrapped_fnc
            
        elif callable_:
            def wrapped_fnc(*args, **kwargs):
                sig = TASK_STRUCT(TASK=name, TEST_CALL=False, TASK_ARGS=args, TASK_KWARGS=kwargs,
                                  SIGNAL=SIGNALS(SHUTDOWN=False, INIT=False))
                self._conn.send(sig)
                return self._conn.recv()
            return wrapped_fnc
        
    def __del__(self):
        self._conn.send(TASK_STRUCT(SIGNAL=SIGNALS(SHUTDOWN=True, INIT=False)))