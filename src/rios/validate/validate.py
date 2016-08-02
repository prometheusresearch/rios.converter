#
# Copyright (c) 2016, Prometheus Research, LLC
#


import cgi
import csv
import json


from rex.core import Validate, Error, guard


__all__ = (
    'RedcapFileValidate',
    'QualtricsFileValidate',
)


class FileAttachmentVal(Validate):
    """
    Abstract base class for an HTML form field containing an uploaded file.

    Based on ``rex.attach`` package's ``AttachmentVal`` class.
    """

    loader = NotImplemented
    system = NotImplemented

    def __call__(self, data):
        if (isinstance(data, cgi.FieldStorage) and
                data.filename is not None and data.file is not None):
            with guard('While processing file', str(data.filename)):
                self.validate(self._load(data.file))
            return data
        error = Error("Expected an uploaded file")
        error.wrap("Got:", repr(data))
        raise error

    def _load(self, attachment):
        try:
            return self.loader(attachment)
        except Exception as exc:
            error = Error('Error opening file for validation')
            error.wrap('Got:', repr(exc))
            raise error

    def validate(self, attachment):
        raise NotImplementedError("%s.render()" % self.__class__.__name__)


class RedcapFileAttachmentVal(FileAttachmentVal):
    """ Validation mechanism for REDCap files. """

    loader = csv.reader
    system = 'redcap'

    def validate(self, attachment):
        pass


class QualtricsFileAttachmentVal(FileAttachmentVal):
    """ Validation mechanism for Qualtrics files. """

    loader = json.load
    system = 'qualtrics'

    def validate(self, attachment):
        pass
