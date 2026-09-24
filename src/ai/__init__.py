from __future__ import annotations
import os
import sys
import typing

# Set default fallback OPENAI_API_KEY if not present so CrewAI module imports cleanly
os.environ.setdefault("OPENAI_API_KEY", "mock-key-for-initialization")

# Enable PEP 604 pipe union syntax for Python 3.9 compatibility with CrewAI
if sys.version_info < (3, 10):
    import threading
    if not hasattr(threading.Timer, "__or__"):
        class _TimerMeta(type):
            def __or__(self, other):
                return typing.Union[self, other]
            def __ror__(self, other):
                return typing.Union[other, self]
        class _PatchTimer(threading.Timer, metaclass=_TimerMeta):
            pass
        threading.Timer = _PatchTimer

    try:
        from pydantic._internal._model_construction import ModelMetaclass
        ModelMetaclass.__or__ = lambda self, other: typing.Union[self, other]
        ModelMetaclass.__ror__ = lambda self, other: typing.Union[other, self]
    except Exception:
        pass
    try:
        from pydantic.v1.main import ModelMetaclass as ModelMetaclassV1
        ModelMetaclassV1.__or__ = lambda self, other: typing.Union[self, other]
        ModelMetaclassV1.__ror__ = lambda self, other: typing.Union[other, self]
    except Exception:
        pass

"""AI Mentor Crew, Tools, Memory, and Prompts package."""
