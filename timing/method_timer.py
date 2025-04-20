import time
from typing import TypeVar, Any, Tuple, Union, Callable
try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_FOUND = True
except ImportError:
    print("Matplotlib not found, plots cannot be made")
    MATPLOTLIB_FOUND = False
import numpy as np
import copy
import weakref
from multiproc.multiproc_class import MultiProcCls # incompatible with MethodTimer

class MethodTimer:
    """Wapper class for arbitrary classes that enables timinng for indivudial methods"""
    def __init__(self, cls:Any , names:Tuple = (), /, *args, **kwargs) -> None:
        """
        Parameters
        ----------
        cls: Any
            Class or object to track whose fucntions. If object is provided, then *args and 
            **kwargs shall be None
            If class is provided, then *args or **kwargs should be present (if they take any for init)
        names: Tuples
            Names of methods to track the times for. If empty, then all method calls will be tracked
        args: tuple
            arguments for class
        kwargs: dict
    
            kwargs for class
        
        NOTE: we use weakref, so you can safely delete the object, if cls is an instance

        Examples:
        ---------
        
            >>> obj = MyClass(...)
            >>> wrapped_obj = MethodTimer(obj, ())
            >>> wrapped_obj.func1(...)
            >>> timing_data = wrapped_obj.data_    
        """
        if isinstance(cls, type):
            if issubclass(cls, MultiProcCls):
                raise RuntimeError("Cannot use MethodTimer with MultiProcCls, use raw class for timing")
            try:
                obj_ = cls(*args, **kwargs)
            except TypeError as t:
                raise RuntimeError(f"Insufficient args to init class {cls}, got following erros {t}") 
        else:
            if isinstance(cls, MultiProcCls):
                raise RuntimeError("Cannot use MethodTimer with MultiProcCls, use raw class for timing")
            obj_ = weakref.proxy(cls)
        time_map_ = dict()
        for name in names:
            time_map_[name] = np.array(())
        if len (names) == 0:
            # time every single callable
            all_attrs = dir(obj_)
            for attr in all_attrs:
                if callable(getattr(obj_, attr)):
                    time_map_[attr] = np.array(())
        
        # check if they are valid callables
        attrs = list(time_map_.keys())
        for attr in attrs:
            if not hasattr(obj_, attr):
                print(f"Following methods were specified to track, but its not a valid method for the class: {attr}")
                continue
            if not callable(getattr(obj_, attr)):
                print(f"Following methods were specified, but its not a callable and will not be tracked: {attr}")
                time_map_.pop(attr)
            if attr.startswith("__"):
                time_map_.pop(attr)
        # print for info
        print("The following methods will be time tracked: ")
        print(list(time_map_.keys()))
        self.obj_ = obj_
        self.time_map_ = time_map_
        
        
    def __getattribute__(self, name:str):
        if name in ("data_", "plot_histograms", "plot"):
            return  super(MethodTimer, self).__getattribute__(name)
        # do method wrapping to track time
        time_map = super(MethodTimer, self).__getattribute__('time_map_')
        obj = super(MethodTimer, self).__getattribute__('obj_')
        # get proper ref, we are using weakref
        obj = obj.__repr__.__self__
        # bootstrap objects getattr
        def wrapped_getattr(obj_inst, name_):
            if name_ in time_map:
                attr = super(type(obj_inst), obj_inst).__getattribute__(name_)
                def wrapped_fnc_(*args, **kwargs):
                    ts_ = time.time()
                    ret = attr(*args, **kwargs)
                    tf_ = time.time()
                    time_map[name_] = np.append(time_map[name_], (tf_-ts_))
                    return ret
                return wrapped_fnc_
            else:
                return super(type(obj_inst), obj_inst).__getattribute__(name_)
        obj_cls = type(obj)
        obj_cls.__getattribute__ = wrapped_getattr
        return obj.__getattribute__(name)

    def plot_histograms(self, names, /, *hist_args, **hist_kwargs):
        """plot time histograms for the methods specified

        Parameters
        ----------
        names: str, list, tuple
            Names of methods whose times to plot in hist
        hist_args: tuple
            arguments for matplotlib hist
        hist_kwargs: dict
            keyword arguments for matplotlib hist
        """
        if not MATPLOTLIB_FOUND:
            print("No matplotlib installation found, cannot create plots")
            return
        time_map = super(MethodTimer, self).__getattribute__('time_map_')
        if isinstance(names, str):
            names = (names, )
        if not isinstance(names, (tuple, list)):
            raise RuntimeError("Expected names to be a str, tuple or list of str with method names")
        valid_names = list()
        for name in names:
            if not name in time_map:
                print(f"Method {name} not found in tracked times")
            valid_names.append(name)
        for i, name in enumerate(valid_names):
            plt.figure(i)
            plt.hist(time_map[name], *hist_args, **hist_kwargs)
            plt.title(f"Times for method {name}")
            plt.xlabel("time (s)")
            plt.ylabel("frequency (N)")
        plt.show()

    def plot(self, names, /, *plot_args, **plot_kwargs):
        """plot time plots for the methods specified

        Parameters
        ----------
        names: str, list, tuple
            Names of methods whose times to plot in hist
        plot_args: tuple
            arguments for matplotlib plot
        plot_kwargs: dict
            keyword arguments for matplotlib plot
        """
        if not MATPLOTLIB_FOUND:
            print("No matplotlib installation found, cannot create plots")
            return
        time_map = super(MethodTimer, self).__getattribute__('time_map_')
        if isinstance(names, str):
            names = (names, )
        if not isinstance(names, (tuple, list)):
            raise RuntimeError("Expected names to be a str, tuple or list of str with method names")
        valid_names = list()
        for name in names:
            if not name in time_map:
                print(f"Method {name} not found in tracked times")
            valid_names.append(name)
        for i, name in enumerate(valid_names):
            plt.figure(i)
            plt.plot(time_map[name], *plot_args, **plot_kwargs)
            plt.title(f"Times for method {name}")
            plt.xlabel("iteration")
            plt.ylabel("time (s)")
        plt.show()
        
    @property
    def data_(self):
        time_map = super(MethodTimer, self).__getattribute__('time_map_')
        return copy.deepcopy(time_map)
    
    def __repr__(self):
        obj = super(MethodTimer, self).__getattribute__('obj_')
        # get proper ref, we are using weakref
        obj = obj.__repr__.__self__
        return getattr(obj, '__repr__')()

    def __call__(self, *args, **kwargs):
        """callable wrapper if wrapped object implements __call__"""
        call = self.__getattribute__("__call__")
        return call(*args, **kwargs)