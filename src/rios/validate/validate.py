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

    Implementations must override `loader`, `system`, and `validate`.

    `loader`
        A function that loads a file into a buffer for processing. Depends on
        the file type to validate. For example, CSV files will typically use
        ``csv.reader`` as the loader function.
    `system`
        A string that defines the corresponding system belonging to the file.
        Used for building SYSTEM_TYPES dictionary for validation context
        manager (see :function:`rios.validate.validate`).
    `validate`
        A function that performs the validation on the file buffer. This
        function must throw an :class:`rex.core.Error` instance if validation
        fails. This function should not return anything.

    Based on :class:`rex.attach.AttachmentVal`.
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
        """
        Runs `loader` on file attachment object.

        :raises Error: If `loader` throws and exception
        """
        try:
            return self.loader(attachment)
        except Exception as exc:
            error = Error('Error opening file for validation')
            error.wrap('Got:', repr(exc))
            raise error

    def validate(self, attachment):
        """
        Handles specific system-type validation.

        Implementations must override this method.
        """
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
