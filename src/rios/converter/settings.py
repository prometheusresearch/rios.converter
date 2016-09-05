#
# Copyright (c) 2016, Prometheus Research, LLC
#


from rex.core import Setting, StrVal


__all__ = (
    'TempDirSetting',
    'LogDirSetting',
)


class TempDirSetting(Setting):
    """ Directory with temporary data """

    name = 'temp_dir'
    default = None
    validate = StrVal()


class LogDirSetting(Setting):
    """ Dir to log conversion activities for future research/analysis """

    name = 'log_dir'
    validate = StrVal()
