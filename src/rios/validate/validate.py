#
# Copyright (c) 2016, Prometheus Research, LLC
#


import cgi
import csv
import json
import re
import six
import magic


from rex.core import Validate, Error, guard


__all__ = (
    'RedcapFileValidate',
    'QualtricsFileValidate',
)


class FileAttachmentVal(Validate):
    """
    Abstract base class for an HTML form field containing an uploaded file.

    Implementations must override `loader`, `system`, `content_type` and
    `validate`.

    `loader`
        A function that loads a file into a buffer for processing. Depends on
        the file type to validate. For example, CSV files will typically use
        ``csv.reader`` as the loader function.
    `loader_args`
        List of arguments to pass to loader function.
    `system`
        A string that defines the corresponding system belonging to the file.
        Used for building SYSTEM_TYPES dictionary for validation context
        manager (see :function:`rios.validate.validate`).
    `content_type`
        A string containing the type of content expected in the file. Compared
        to content type string produced by `python-magic` library for proper
        validation.
    `validate`
        A function that performs the validation on the file buffer. This
        function must throw an :class:`rex.core.Error` instance if validation
        fails. This function should not return anything.

    Based on :class:`rex.attach.AttachmentVal`.
    """

    loader = NotImplemented
    loader_args = None
    open_args = None
    system = NotImplemented
    content_type = NotImplemented

    def __call__(self, data):
        if (isinstance(data, cgi.FieldStorage) and
                data.filename is not None and data.file is not None):
            with guard('While processing file', str(data.filename)):
                self.validate(self._load(self._content_type(data.file)))
            return data
        error = Error("Expected an uploaded file")
        error.wrap("Got:", repr(data))
        raise error

    def _content_type(self, attachment):
        """
        Checks if attachment is of the appropriate content type

        :raises Error: If content type doesn't match
        """
        file_type = magic.from_buffer(
            attachment.read(1024) if hasattr(attachment, 'read')
                else attachment
        )
        attachment.seek(0)
        if self.content_type not in file_type:
            error = Error('Incorrect file type')
            error.wrap('Got:', str(file_type))
            raise Error
        return attachment
            

    def _load(self, attachment):
        """
        Runs `loader` on file attachment object.

        :raises Error: If `loader` throws and exception
        """
        try:
            opened_file = (
                open(attachment, *self.open_args)
                    if isinstance(attachment, six.string_types)
                    else attachment
            )
            return self.loader(opened_file)
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
    open_args = ['rU',]
    system = 'redcap'
    content_type = 'ASCII text'

    # Static references for validation
    FIELD_TYPES = [
        'text',
        'notes',
        'dropdown',
        'radio',
        'checkbox',
        'calc',
        'slider',
        'truefalse',
        'yesno',
    ]
    REQUIRED = True
    OPTIONAL = False
    class Column(object):
        """ Column class for validation. """
        def __init__(self, required, types=None)
            self.required = required
            self.types = types
        def __call__(self, value=None):
            
    COLUMNS = {
        "Variable / Field Name":
            [REQUIRED,],
        "Form Name":
            [REQUIRED,],
        "Section Header":
            [OPTIONAL,],
        "Field Type":
            [REQUIRED, FIELD_TYPES,],
        "Field Label":
            [REQUIRED,],
        "Choices, Calculations, OR Slider Labels":
            [REQUIRED,],
        "Field Note":
            [OPTIONAL,],
        "Text Validation Type OR Show Slider Number":
            [OPTIONAL,],
        "Text Validation Min":
            [OPTIONAL,],
        "Text Validation Max":
            [OPTIONAL,],
        "Identifier?":
            [OPTIONAL,],
        "Branching Logic (Show field only if...)":
            [OPTIONAL,],
        "Required Field?":
            [OPTIONAL,],
        "Custom Alignment":
            [OPTIONAL,],
        "Question Number (surveys only)":
            [OPTIONAL,],
        "Matrix Group Name":
            [OPTIONAL,],
        "Matrix Ranking?":
            [OPTIONAL,],
        "Field Annotation":
            [OPTIONAL,],
    }

    def validate(self, attachment):
        try:
            header = attachment.next()
        except Exception as exc:
            print "HELLO!!!", repr(exc)
        return None


class QualtricsFileAttachmentVal(FileAttachmentVal):
    """ Validation mechanism for Qualtrics files. """

    loader = json.load
    system = 'qualtrics'
    content_type = 'ASCII text'

    def validate(self, attachment):
        pass
