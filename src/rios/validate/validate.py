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
from ..common import csv_data_dictionary


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
        data_dict = csv_data_dictionary(attachment)
        header = data_dict.keys()

        # Check that all column headers are valid
        bad_headers = []
        if not all(value in self.COLUMNS for value in header):
            for h in header:
                if h not in self.COLUMNS:
                    bad_headers.append(h)
            bad_headers = set(bad_headers)

        # Check for required headers
        missing_headers = []
        if not all(value in header for value in self.REQUIRED_COLUMNS):
            for v in self.REQUIRED_COLUMNS:
                if v not in header:
                    missing_headers.append(v)
            missing_headers = set(missing_headers)

        # Check Field Type row for unexpected values
        bad_field_types = []
        if not all(d in self.FIELD_TYPES for d in data_dict['Field Type']):
            for d in data_dict['Field Type']:
                k = d.keys()
                for v in k:
                    if v not in self.FIELD_TYPES:
                        bad_field_types.append(v)
            bad_field_types = set(bad_field_types)

        if bad_headers or missing_headers or bad_field_types:
            error = Error('Validation error')
            if bad_headers:
                error.wrap('Unexpected column header(s). Got:',
                    ", ".join(bad_headers))
                error.wrap('Allowable column headers:',
                    ", ".join(self.COLUMNS))
            if missing_headers:
                error.wrap('Missing required column header(s). Got:',
                    ", ".join(missing_headers))
                error.wrap('Required column headers:',
                    ", ".join(self.REQUIRED_COLUMNS))
            if bad_field_types:
                error.wrap('Unexpected Field Type value(s). Got:',
                    ", ".join(bad_field_types))
                error.wrap('Allowable Field Type values:',
                    ", ".join(self.FIELD_TYPES))
            raise error


class QualtricsFileAttachmentVal(FileAttachmentVal):
    """ Validation mechanism for Qualtrics files. """

    loader = json.load
    system = 'qualtrics'
    content_type = 'ASCII text'

    def validate(self, attachment):
        pass
