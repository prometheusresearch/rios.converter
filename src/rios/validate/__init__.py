#
# Copyright (c) 2016, Prometheus Research, LLC
#


__import__('pkg_resources').declare_namespace(__name__)


import contextlib
import six


from validate import RedcapFileAttachmentVal, QualtricsFileAttachmentVal


#SYSTEM_TYPES = {
#    'redcap': RedcapFileValidate,
#    'qualtrics': QualtricsFileValidate,
#}
#
#
#@contextlib.contextmanager
#def validate(file_obj, system):
#    """
#    Context manager for validating REDCap and Qualtrics files.
#
#    :param file_obj: An instrument file to validate
#    :type file_obj: File-like object with ``read`` and ``seek`` attributes
#    :param system: Type of instrument file to validate
#    :type system: String
#    :raises TypeError: If either input fails to meet specifications
#    :returns: Validated instrument file
#    :rtype: string
#    """
#    if not hasattr(file_obj, 'read') and not hasattr(file_obj, 'seek'):
#        raise TypeError('Expected a valid file-like object')
#
#    if isinstance(system, six.string_types) and system in SYSTEM_TYPES:
#        yield SYSTEM_TYPES[system](file_obj)
#        file_obj.seek(0)
#    else:
#        raise TypeError("Expected system types of %s" % 'stuff')
