#
# Copyright (c) 2016, Prometheus Research, LLC
#


import contextlib


__all__ = (
    'Logger',
    'logger_context',
    'logger_main',
)


class Logger(object):
    """
    Logging container for logging messages.

    This class allows logging of messages in an internal list. The messages
    are available for output, and all messages may be cleared. Make sure that
    messages are cleared in each logging instance when the logging instance is
    no longer needed or needs to be reset.
    """

    __slots__ = ('_slots',)

    def __init__(self):
        self._slots = []

    def clear(self):
        self._slots = []

    def log(self, log):
        if isinstance(log, basestring):
            self._slots.append(log)
        else:
            raise TypeError('Logger objects must be of type string or unicode')

    def check(self):
        """ Checks if any logs have been registered. """
        if len(self._slots) == 0:
            return False
        else:
            return True

    def get(self):
        return "\n".join(self._slots)


@contextlib.contextmanager
def logger_context():
    logging_instance = Logger()
    yield logging_instance
    logging_instance.clear()


logger_main = Logger()
