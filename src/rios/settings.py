from rex.core import Setting
from rex.core import StrVal


class TempDirSetting(Setting):
    """Directory with temporary data."""
    name = 'temp_dir'
    default = None
    validate = StrVal()
