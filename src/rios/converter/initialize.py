#
# Copyright (c) 2016, Prometheus Research, LLC
#


import os


from rex.core import Initialize, get_settings


__all__ = ('ConverterInitialize',)


class ConverterInitialize(Initialize):
    """ Initialize log_dir directory to make sure it exists and is writable """
    def __call__(self):
        log_dir = get_settings().log_dir
        if not os.path.isdir(log_dir):
            raise Error('Log Directory (%s) doesn\'t exist' % (log_dir,))
        if not os.access(log_dir, os.R_OK | os.W_OK | os.X_OK):
            raise Error('Log Directory (%s) not writable' % (log_dir,))
