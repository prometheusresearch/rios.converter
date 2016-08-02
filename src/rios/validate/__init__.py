#
# Copyright (c) 2016, Prometheus Research, LLC
#


__import__('pkg_resources').declare_namespace(__name__)


import contextlib
import six


from validate import FileAttachmentVal


SYSTEM_TYPES = {
    cls.system: cls() for cls in FileAttachmentVal.__subclasses__()
}


@contextlib.contextmanager
def validate(file_obj, system):
    """
    Context manager for validating REDCap and Qualtrics files.

    :param file_obj: An instrument file to validate
    :type file_obj: File-like object with ``read`` and ``seek`` attributes
    :param system: Type of instrument file to validate
    :type system: String
    :raises TypeError: If either input fails to meet specifications
    :returns: Validated instrument file
    :rtype: string
    """
    if isinstance(system, six.string_types) and system in SYSTEM_TYPES:
        yield SYSTEM_TYPES[system](file_obj)
        #file_obj.seek(0)
    else:
        error = Error('Expected valid system types')
        error.wrap('Got:', repr(system))
        raise error
