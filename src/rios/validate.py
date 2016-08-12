#
# Copyright (c) 2016, Prometheus Research, LLC
#


import cgi
import csv
import json
import six
import io
import magic


from rex.core import Validate, Error, guard
from common import csv_data_dictionary


__all__ = (
    'SystemFileAttachmentVal',
    'validate_system_file',
)


class SystemFileAttachmentVal(Validate):
    """
    Abstract base class for an HTML form field containing an uploaded file.

    Subclass for each third party instrument system requiring validation. Each
    subclass is automatically handled by the :function:validate function.

    Implementations must override `loader`, `system`, and `content_type`
    values along with overriding the `validate` function.

    `loader`
        A dict with key of `loader` and value of a loader function that
        corresponds to the file structure being processed for validation. For
        example, CSV files will typically use :function:`csv.reader` as the
        loader function.
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
    system = NotImplemented
    content_type = NotImplemented
    file_descriptor = NotImplemented
    file_format = NotImplemented

    def __call__(self, data):
        if (isinstance(data, cgi.FieldStorage) and
                data.filename is not None and data.file is not None):
            with guard('Error encountered while processing file',
                        str(data.filename)):
                content_validated_file = self._content_type(data.file)
                load_validated_file = self._load(content_validated_file)
                self.validate(load_validated_file)
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
            error = Error(
                'Incorrect file type uploaded for system of type:',
                str(self.system)
            )
            error.wrap('File type expected:', str(self.file_descriptor))
            error.wrap(
                'Please select a file of the correct type and try again'
            )
            raise error
        return attachment

    def _load(self, attachment):
        """
        Runs `loader` on file attachment object.

        :raises Error: If `loader` throws and exception
        """
        try:
            if isinstance(attachment, file):
                load_this = io.BytesIO(attachment.read())
            else:
                load_this = attachment
            return self.loader['loader'](
                load_this,
                *self.loader_args,
                **self.loader_kwargs
            )
        except Exception:
            error = Error(
                'Invalid file content format encountered for system of type:',
                str(self.system)
            )
            error.wrap('File content format expected', str(self.file_format))
            error.wrap(
                'Please select a file with the correct content formatting'
                '  and try again'
            )
            raise error

    def validate(self, attachment):
        """
        Handles specific system-type validation.

        Implementations must override this method and raise a
        :class:`rex.core.error.Error` error instance if validation fails.
        """
        raise NotImplementedError("%s.validate()" % self.__class__.__name__)


class RedcapFileAttachmentVal(SystemFileAttachmentVal):
    """ Validation mechanism for REDCap files. """

    loader = {'loader': csv.reader}
    # Loader kwargs barely matter since 'csv' module is NOT strict at all
    # ...but might as well try!
    loader_kwargs = {'strict': True, 'delimiter': ',', 'quotechar': '"'}
    system = 'redcap'
    content_type = 'ASCII text'
    file_descriptor = 'CSV file'
    file_format = 'Comma separated values formatted text'

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

        # Check for required headers
        missing_headers = []
        if not all(value in header for value in self.REQUIRED_COLUMNS):
            for v in self.REQUIRED_COLUMNS:
                if v not in header:
                    missing_headers.append(v)
            missing_headers = set(missing_headers)  # Get unique values

        # Check that all column headers are valid
        bad_headers = []
        # Parse rest of headers if have required ones
        if not missing_headers \
                and not all(value in self.COLUMNS for value in header):
            for h in header:
                if h not in self.COLUMNS:
                    bad_headers.append(h)
            bad_headers = set(bad_headers)  # Get unique values

        # Check Field Type row for unexpected values
        bad_field_types = []
        # Only parse 'Field Type' col if exists
        if ('Field Type' in data_dict
            and not all(d in self.FIELD_TYPES
                        for d in data_dict['Field Type'])):
            for d in data_dict['Field Type']:
                for t, ln in six.iteritems(d):
                    if t not in self.FIELD_TYPES:
                        bad_field_types.append(d)

        if bad_headers or missing_headers or bad_field_types:
            error = Error('REDCap file validation error',
                            'Please fix these errors and try again')
            if bad_headers:
                error.wrap('Unexpected column header(s). Got:',
                                ", ".join(bad_headers))
                error.wrap('Allowable column headers:',
                                ", ".join(self.COLUMNS))
            if missing_headers:
                error.wrap('Missing required column header(s):',
                                ", ".join(missing_headers))
                error.wrap('Required column headers:',
                                ", ".join(self.REQUIRED_COLUMNS))
            if bad_field_types:
                errors = []
                for d in bad_field_types:
                    for k, v in six.iteritems(d):
                        errors.append("Bad value: '" + k + "', on line: " + v)
                error.wrap('Unexpected Field Type value(s). Got:',
                                ", ".join(errors))
                error.wrap('Allowable Field Type values:',
                                ", ".join(self.FIELD_TYPES))
            raise error


class QualtricsFileAttachmentVal(SystemFileAttachmentVal):
    """ Validation mechanism for Qualtrics files. """

    loader = {'loader': json.load}
    system = 'qualtrics'
    content_type = 'ASCII text'
    file_descriptor = 'QSF file'
    file_format = 'JSON formatted text'

    def validate(self, attachment):
        pass

# Autogenerate system validators based on SystemFileAttachmentVal subclasses
SYSTEM_TYPES = {
    cls.system: cls() for cls in SystemFileAttachmentVal.__subclasses__()
}


def validate_system_file(infile, system):
    """
    Validation mechanism for incoming, third party instrument definition files.

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
