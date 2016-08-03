#
# Copyright (c) 2016, Prometheus Research, LLC
#


import cgi
import csv
import json
import re
import six
import cStringIO
import io
import copy
import magic


from rex.core import Validate, Error, guard


__all__ = (
    'RedcapFileValidate',
    'QualtricsFileValidate',
)


class FileAttachmentVal(Validate):
    """
    Abstract base class for an HTML form field containing an uploaded file.

    Implementations must override `loader`, `system`, and `content_type`
    values along with overriding the `validate` function.

    `loader`
        A function that loads a file into a buffer for processing. Depends on
        the file type to validate. For example, CSV files will typically use
        ``csv.reader`` as the loader function.
    `loader_args`
        List of arguments to pass to loader function.
    `loader_kwargs`
        Dict of named arguments to pass to loader function.
    `open_args`
        List of arguments to pass to file open function.
    `system`
        A string that defines the corresponding system belonging to the file.
        Used for automatically building SYSTEM_TYPES dictionary for validation
        function (see :function:`rios.validate.validate`).
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
    loader_args = []
    loader_kwargs = {}
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
            attachment.read(1024)
                if hasattr(attachment, 'read') else attachment
        )
        attachment.seek(0)
        if self.content_type not in file_type:
            error = Error('Incorrect file type')
            error.wrap('Got:', str(file_type))
            raise error
        return attachment
            

    def _load(self, attachment):
        """
        Runs `loader` on file attachment object.

        :raises Error: If `loader` throws and exception
        """
        try:
            return self.loader(
                (open(attachment, *self.open_args)
                        if isinstance(attachment, six.string_types)
                        else attachment
                ),
                *self.loader_args,
                **self.loader_kwargs
            )
        except Exception as exc:
            error = Error('Error opening file for validation')
            error.wrap('Got:', repr(exc))
            raise error

    def validate(self, attachment):
        """
        Handles specific system-type validation.

        Implementations must override this method and raise a
        :class:`rex.core.error.Error` error instance if validation fails.
        """
        raise NotImplementedError("%s.validate()" % self.__class__.__name__)


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
    REQUIRED_COLUMNS = [
        "Variable / Field Name",
        "Form Name",
        "Field Type",
        "Field Label",
        "Choices, Calculations, OR Slider Labels",
    ]
    OPTIONAL_COLUMNS = [
        "Section Header",
        "Field Note",
        "Text Validation Type OR Show Slider Number",
        "Text Validation Min",
        "Text Validation Max",
        "Identifier?",
        "Branching Logic (Show field only if...)",
        "Required Field?",
        "Custom Alignment",
        "Question Number (surveys only)",
        "Matrix Group Name",
        "Matrix Ranking?",
        "Field Annotation",
    ]
    COLUMNS = REQUIRED_COLUMNS + OPTIONAL_COLUMNS

    def validate(self, attachment):
        header = attachment.next()
        # Make sure all column headers are valid
        if not all(value in self.COLUMNS for value in header):
            error = Error('Unexpected column headers(s)')
            error.wrap('Expected column headers:', ", ".join(self.COLUMNS))
            error.wrap('Got:', ", ".join(header))
            raise error
        if not all(value in header for value in self.REQUIRED_COLUMNS):
            error = Error('Missing required column header(s)')
            error.wrap('Expected required column headers:',
                ", ".join(self.REQUIRED_COLUMNS))
            error.wrap('Got', ", ".join(header))
            raise error
        # Check Field Type row for unexpected values
        column_values = {}
        for h_value in header:
            column_values[h_value] = []
        for row in attachment:
            for h_value, value in zip(header, row):
                column_values[h_value].append(value)
        if not all(value in self.FIELD_TYPES
            for value in column_values['Field Type']):
            error = Error('Unexpected Fiel Type value')
            error.wrap('Expected Field Type values:',
                ", ".join(self.FIELD_TYPES))
            error.wrap('Got:', column_values['Field Type'])
            raise error


class QualtricsFileAttachmentVal(FileAttachmentVal):
    """ Validation mechanism for Qualtrics files. """

    loader = json.load
    system = 'qualtrics'
    content_type = 'ASCII text'

    def validate(self, attachment):
        pass
