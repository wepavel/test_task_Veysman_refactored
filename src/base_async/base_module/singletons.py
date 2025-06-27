import abc
import threading


class Singleton(abc.ABCMeta):
    """."""
    _instances = {}

    def __call__(cls, *args, **kwargs):
        """."""
        if cls not in cls._instances:
            base = super(Singleton, cls)
            cls._instances[cls] = base.__call__(*args, **kwargs)
        return cls._instances[cls]


class ThreadIsolatedSingleton(abc.ABCMeta):
    """."""
    _instances = threading.local()

    def __call__(cls, *args, **kwargs):
        """."""
        if not hasattr(cls._instances, 'heap'):
            cls._instances.heap = {}
        if cls not in cls._instances.heap:
            cls._instances.heap[cls] = super(
                ThreadIsolatedSingleton, cls
            ).__call__(*args, **kwargs)
        return cls._instances.heap[cls]
