from rex.core import Setting

class TempDirSetting(Setting):
    """Directory with temporary data."""
    name = 'temp_dir'
    default = None
    validate = StrVal()
