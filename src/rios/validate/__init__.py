#
# Copyright (c) 2016, Prometheus Research, LLC
#


__import__('pkg_resources').declare_namespace(__name__)


import six


from validate import FileAttachmentVal


SYSTEM_TYPES = {
    cls.system: cls() for cls in FileAttachmentVal.__subclasses__()
}


def validate(infile, system):
    """
    Context manager for validating REDCap and Qualtrics files.

    :param infile: An attachment payload to validate
    :type infile: cgi.Fieldstorage object
    :param system: Type of instrument file to validate
    :type system: string
    :raises Error: If system parameter is malformed
    """
    if not isinstance(system, six.string_types) and system not in SYSTEM_TYPES:
        error = Error('Expected valid system types')
        error.wrap('Got:', repr(system))
        raise error
    return SYSTEM_TYPES[system](infile)
