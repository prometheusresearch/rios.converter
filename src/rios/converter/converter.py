#
# Copyright (c) 2016, Prometheus Research, LLC
#


import tempfile
import traceback
import datetime
import docutils.core
import glob
import os
import io
import cStringIO
import shutil
import sys
import zipfile as ZIPFILE
import simplejson
import collections
import csv
import yaml
import cgi
import mimetypes


from cached_property import cached_property
from webob import Response
from webob.static import FileIter, BLOCK_SIZE
from webob.exc import HTTPMethodNotAllowed
from rex.core import (
    AnyVal,
    StrVal,
    Setting,
    Error,
    Validate,
    get_packages,
    get_settings,
)
from rex.web import (
    Command,
    HandleError,
    HandleFile,
    HandleLocation,
    Parameter,
    render_to_response,
)
from rios.conversion import (
    redcap_to_rios,
    qualtrics_to_rios,
    rios_to_redcap,
    rios_to_qualtrics,
)
from rios.conversion.base import(
    DEFAULT_LOCALIZATION,
    DEFAULT_VERSION,
)
from rios.conversion.utils import CsvReader
from .csv_validation import (
    RedcapLegacyCsvValidator,
    RedcapModernCsvValidator,
    StringLoader,
)


def log(session, filename, content):
    """ Log conversion information, issues, and failures """

    log_dir = os.path.join(get_settings().log_dir, session)
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)
    with open(os.path.join(log_dir, filename), 'wb') as fp:
        if hasattr(content, 'read'):
            fp.write(content.read())
        else:
            fp.write(content)
    if hasattr(content, 'seek'):
        # Rewind file object
        content.seek(0)


def log_file(session, filepath):
    """ Copy uploaded instrument files to the log_dir directory """

    log_dir = os.path.join(get_settings().log_dir, session)
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)
    shutil.copy(filepath, log_dir)


def write_to_buffer(file_object, payload, data_type=None, *args, **kwargs):
    """
    Writes stuctured data to a file object of the corresponding data type. The
    ``args`` and ``kwargs`` are passed to the underlying loader_type instance.
    If ``data_type`` is not specified or the function can't handle writing the
    data type of payload, the payload is written as a text file.

    If payload is a dict to be written to a CSV, a dict with a key of name
    ``fieldnames`` and value of type list containing separate field names must
    be passed via ``kwargs`` to enable writing the payload to a CSV with
    :class:csv.DictWriter. The payload will be written to a text file if the
    field names list is not passed in.

    All file objects will be rewound with ``file_object.seek(0)`` after a
    checked for a ``seek`` attribute is successful.

    :param data_type:
        The type of structured data payload will be written too. If None, the
        payload will be written to a text file.
    :type data_type: str of value 'json', 'yaml', or 'csv' or None
    :param file_object: File object to write too.
    :type file_object: file or buffer/stream
    :param payload: Structured dataset.
    :type payload: dict, list, or str
    """

    if data_type == 'json':
        simplejson.dump(
            payload,
            file_object,
            sort_keys=True,
            indent='    ',
            *args,
            **kwargs
        )
    elif data_type == 'yaml':
        yaml.dump(
            payload,
            file_object,
            default_flow_style=False,
            *args,
            **kwargs
        )
    elif data_type == 'csv':
        if isinstance(payload, list):
            # Payload must contain one CSV line per list item
            csv_writer = csv.writer(
                file_object,
                delimeter=',',
                quotechar='\"',
                quoting=csv.QUOTE_MINIMAL,
                *args,
                **kwargs
            )
            for row in payload:
                csv_writer.writerow(row)
        elif isinstance(payload, dict) and 'fieldnames' in kwargs:
            fieldnames = kwargs['fieldnames']
            csv_writer = csv.DictWriter(
                file_object,
                fieldnames=fieldnames,
                delimeter=',',
                quotechar='\"',
                quoting=csv.QUOTE_MINIMAL,
                *args,
                **kwargs
            )
    else:  # Load data to text file
        if isinstance(payload, list):
            for record in payload:
                file_object.write(
                    record if isinstance(record, str) else repr(record)
                )
        else:
            file_object.write(
                str(payload) if isinstance(payload, str) else repr(payload)
            )

    # Rewind ALL THE THINGS! (files)
    if hasattr(file_object, 'seek'):
        file_object.seek(0)

def write_to_zip(zipfile, name, payload, format, *args, **kwargs):
    """
    Writes the specified container to a zipfile.

    The ``args`` and ``kwargs`` are passed to the underlying function call. See
    :function:write_to_buffer for more details.
    """

    container = cStringIO.StringIO()
    write_to_buffer(
        data_type=str(format),
        file_object=container,
        payload=payload,
        *args,
        **kwargs
    )
    zipfile.writestr(name, container.read())


class AttachmentVal(Validate):
    """
    Accepts an HTML form field containing an uploaded file.

    Produces a pair: the file name and an open file object. Taken from
    rex.attach 2.0.4.
    """

    Attachment = collections.namedtuple('Attachment', 'name content')

    def __call__(self, data):
        if (isinstance(data, cgi.FieldStorage) and
                data.filename is not None and data.file is not None):
            bffr = (
                data.file
                if isinstance(data.file,
                              (cStringIO.OutputType, cStringIO.InputType,))
                else cStringIO.StringIO(data.file.read())
            )
            return self.Attachment(data.filename, bffr)
        if (isinstance(data, tuple) and len(data) == 2 and
                isinstance(data[0], (str, unicode)) and
                hasattr(data[1], 'read')):
            filename = data[0]
            bffr = cStringIO.StringIO(data[1].read())
            return self.Attachment(filename, bffr)
        error = Error("Expected an uploaded file")
        error.wrap("Got:", repr(data))
        raise error


class BufferedFileApp(object):
    """
    Like `webob.static.FileApp`, but takes an open file object instead.

    Forked from rex.attach 2.0.4 and modified.
    """

    def __init__(self, bffr, filename):
        self.file = bffr
        self.filename = filename

    def __call__(self, req):
        # Adapted from `FileApp.__call__()`.
        if 'wsgi.file_wrapper' in req.environ:
            app_iter = req.environ['wsgi.file_wrapper'](self.file, BLOCK_SIZE)
        else:
            app_iter = FileIter(self.file)
        last_modified = datetime.datetime.now()
        # Need to seek to end of cStringIO.StringIO buffer to get size.
        self.file.seek(0, os.SEEK_END)
        content_length = self.file.tell()
        # Remember to seek back to the beginning before the buffer is sent!
        self.file.seek(0)
        content_type, content_encoding = mimetypes.guess_type(self.filename)
        content_disposition = "attachment; filename=%s" % self.filename
        accept_ranges = 'bytes'
        return Response(
                app_iter=app_iter,
                last_modified=last_modified,
                content_length=content_length,
                content_type=content_type,
                content_encoding=content_encoding,
                content_disposition=content_disposition,
                accept_ranges=accept_ranges,
                conditional_response=True)


class Home(Command):

    path = '/'
    access = 'anybody'
    template = 'rios.converter:/templates/home.html'

    def render(self, req):
        return render_to_response(self.template, req, status=200)


class ConvertDocumentationServe(Command):

    path = '/convertdoc'
    access = 'anybody'
    template = 'rios.converter:/templates/convert.html'

    def render(self, req):
        return render_to_response(self.template, req, status=200)


class ConvertDocumentationSource(Command):

    path = '/convert'
    access = 'anybody'
    template = 'rios.converter:/templates/convert.rst'

    def render(self, req):
        response = render_to_response(self.template, req, status=200)
        html_output = docutils.core.publish_string(
            response.body,
            writer_name='html'
        )
        return Response(html_output)


class ConvertFromRiosWebForm(Command):

    path = '/convert/from'
    access = 'anybody'
    template = 'rios.converter:/templates/from_rios.html'

    def render(self, req):
        return render_to_response(self.template, req, status=200)


class ConvertToRiosWebForm(Command):

    path = '/convert/to'
    access = 'anybody'
    template = 'rios.converter:/templates/to_rios.html'

    def render(self, req):
        return render_to_response(self.template, req, status=200)


class ConvertToRiosProcessorApi(Command):

    path = '/convert/to/rios'
    access = 'anybody'
    parameters = [
        Parameter('system', StrVal(r'(qualtrics)|(redcap)'), ),
        Parameter('format', StrVal(r'(yaml)|(json)')),
        Parameter('instrument_title', StrVal(r'^[a-zA-Z0-9_\s]*$')),
        Parameter('instrument_id', StrVal(r'([a-z0-9]{3}[a-z0-9]*)?')),
        Parameter('outname', StrVal(r'^[a-zA-Z0-9_]+$')),
        Parameter('infile', AttachmentVal()),
        ]

    converters = {
        'qualtrics': qualtrics_to_rios,
        'redcap': redcap_to_rios,
        }

    convert_fail_template = \
        'rios.converter:/templates/convert_fail.html'
    form_params_fail_template = \
        'rios.converter:/templates/form_params_fail.html'
    validation_fail_template = \
        'rios.converter:/templates/validation_fail.html'

    validator = None

    @cached_property
    def settings(self):
        return get_settings()

    def render(self, req, system, format, instrument_title,
                                        instrument_id, outname, infile):

        # Allow only GET and HEAD requests.
        if req.method not in ('POST',):
            raise HTTPMethodNotAllowed()

        # Construct proper instrument ID
        if 'urn:' not in instrument_id:
            instrument_id = 'urn:%s' % (instrument_id,)
        # Check for required redcap paramters
        if system == 'redcap':
            initialization_errors = []
            if not instrument_id:
                initialization_errors.append('Instrument ID is required')
            if not instrument_title:
                initialization_errors.append('Instrument Title is required')
            if len(initialization_errors) > 0:
                return render_to_response(
                    self.form_params_fail_template,
                    req,
                    errors=initialization_errors,
                )

        # Validate file with props.csvtoolkit validator API
        upload_file = infile.content
        upload_file.seek(0)

        # VALIDATE UPLOADED FILE
        if system == 'redcap':
            try:
                # Pre-validation processing
                self.reader = CsvReader(upload_file)  # noqa: F821
                self.reader.load_attributes()
                upload_file.seek(0)

                # Determine and initialize validator
                first_field = self.reader.attributes[0]
                if first_field == 'Variable / Field Name':
                    # Process new CSV format
                    self.validator = RedcapModernCsvValidator
                elif first_field == 'fieldID':
                    # Process legacy CSV format
                    self.validator = RedcapLegacyCsvValidator
                else:
                    error = Error(
                        "Unknown input CSV header format. Got values:",
                        ", ".join(self.reader.attributes)
                    )
                    error.wrap(
                        "Expected first header/field name value to be:",
                        "\"Variable / Field Name\" or \"fieldID\""
                    )
                    raise error
            except Exception as exc:
                error = Error(
                    "Unable to parse REDCap data dictionary. Got error:",
                    (str(exc) if isinstance(exc, Error) else repr(exc))
                )
                print "TRACEBACK:"
                one, two, tb = sys.exc_info()
                traceback.print_tb(tb)
                return render_to_response(
                    self.validation_fail_template,
                    req,
                    errors=str(error),
                    system=system,
                )
            else:
                # Perform validation
                result = self.validator(StringLoader(upload_file))()
                if not result.validation:
                    return render_to_response(
                        self.validation_fail_template,
                        req,
                        errors=result.log,
                        system=system,
                    )
        else:  # system == 'qualtrics', pre-validated in self.parameters
            try:
                simplejson.load(infile)
            except Exception:
                error = Error(
                    "Qualtrics file validation failed:",
                    "The file content is not valid JSON text"
                )
                error.wrap("Error:", str(exc))
                error.wrap("Please try again with a valid QSF file")
                return render_to_response(
                    self.validation_fail_template,
                    req,
                    errors=str(error),
                    system=system,
                )

        # Rewind file
        upload_file.seek(0)

        # API INITIALIATION
        session = datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')

        if system == 'redcap':
            converter_kwargs = {
                'instrument_version': DEFAULT_VERSION,
                'localization': DEFAULT_LOCALIZATION,
                'description': '',
                'title': instrument_title,
                'id': instrument_id,
                'stream': upload_file,
                'suppress': True,  # Need logged messages
            }
        else:  # system == 'qualtrics'
            converter_kwargs = {
                'stream': upload_file,
                'suppress': True,  # Need logged messages
                'filemetadata': True, # Pull metadata from file
            }

        # LOG INITIALIZATION
        log(session, '%s_to_rios' % (system,), '')
        log(session, 'uploaded_file_contents.log', upload_file.read())
        log(session, 'conversion_params.log', repr(converter_kwargs))

        # PROCESS FILE
        result = self.converters[system](**converter_kwargs)

        # PROCESS RESULT AND RETURN RELEVANT FILES
        if all(key in result for key in ('form', 'instrument',)):
            # Initialize zip file
            zip_container = cStringIO.StringIO()
            zip_filename = outname + '.zip'

            # Process data structures and insert into zip
            zip_file_buffer = None
            with ZIPFILE.ZipFile(zip_container, 'a', ZIPFILE.ZIP_DEFLATED) \
                        as zipfile:
                # Write instrument file to zip
                instrument_name = str(outname) + '_i.' + str(format)
                write_to_zip(
                    zipfile=zipfile,
                    name=instrument_name,
                    payload=result['instrument'],
                    format=format,
                )

                # Write form file to zip
                form_name = str(outname) + '_f.' + str(format)
                write_to_zip(
                    zipfile=zipfile,
                    name=form_name,
                    payload=result['form'],
                    format=format,
                )

                # Write calculationset to zipfile
                if 'calculationset' in result:
                    calc_name = str(outname) + '_c.' + str(format)
                    write_to_zip(
                        zipfile=zipfile,
                        name=calc_name,
                        payload=result['calculationset'],
                        format=format,
                    )
                
                # Write log file to zip
                if 'logs' in result:
                    log_name = 'conversion_log.txt'
                    write_to_zip(
                        zipfile=zipfile,
                        name=log_name,
                        payload=result['logs'],
                        format=None
                    )

            # Rewrind zipfile object
            zip_container.seek(0)

            log(session, 'output.zip', zip_container)
            response = BufferedFileApp(zip_container, zip_filename)
            return response(req)
        elif 'failure' in result:
            fail_log = str(result['failure'])
            log(session, 'failure.log', fail_log)
            return render_to_response(
                self.convert_fail_template,
                req,
                errors=[fail_log,],
                system=system
            )
        else:
            # Conversion result does not contain the proper structure
            error = Error(
                'Unexpected serve side error occured',
                'Unable to convert data dictionary at this time'
            )
            log(session, 'error.log', str(error))
            return render_to_response(
                self.convert_fail_template,
                req,
                errors=[str(error),],
                system=system
            )


#class ConvertFromRiosProcessorApi(Command):
#
#    path = '/convert/from/rios'
#    access = 'anybody'
#    parameters = [
#        Parameter('system', StrVal('(qualtrics)|(redcap)'), ),
#        Parameter('format', StrVal('(yaml)|(json)')),
#        Parameter('instrument_file', AnyVal()),
#        Parameter('form_file', AnyVal()),
#        Parameter('calculationset_file', AnyVal()),
#        Parameter('outname', StrVal('.*')), ]
#
#    converter_class = {
#        'qualtrics': QualtricsFromRios,
#        'redcap': RedcapFromRios,
#        }
#
#    convert_fail_template = 'rios.converter:/templates/convert_fail.html'
#    form_params_fail_template = \
#        'rios.converter:/templates/form_params_fail.html'
#
#    def load_file(self, session, file_field):
#        filename = os.path.join(self.temp_dir, file_field.filename)
#        with open(filename, 'w') as fo:
#            fo.write(file_field.file.read())
#        log_file(session, filename)
#        return filename
#
#    def render(
#            self,
#            req,
#            system,
#            format,
#            instrument_file,
#            form_file,
#            calculationset_file,
#            outname):
#
#        session = datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')
#        self.settings = get_settings()
#        tempfile.tempdir = self.settings.temp_dir
#        self.temp_dir = tempfile.mkdtemp()
#        outfile = os.path.join(self.temp_dir, outname)
#        initialization_errors = []
#        if not outname:
#            initialization_errors.append('Output filename prefix is required.')
#        if not format:
#            format = 'yaml'
#        args = [
#                '--verbose',
#                '--format', format,
#                '--outfile', outfile,
#                ]
#        if hasattr(instrument_file, 'filename'):
#            args.extend([
#                    '--instrument',
#                    '%s' % self.load_file(session, instrument_file)])
#        else:
#            initialization_errors.append(
#                'An input instrument file is required.'
#            )
#        if hasattr(form_file, 'filename'):
#            args.extend([
#                    '--form',
#                    '%s' % self.load_file(session, form_file)])
#        else:
#            initialization_errors.append('An input form file is required.')
#        if hasattr(calculationset_file, 'filename'):
#            args.extend([
#                    '--calculationset',
#                    '%s' % self.load_file(session, calculationset_file)])
#        args.extend(['--localization', LOCALIZATION])
#        if initialization_errors:
#            shutil.rmtree(self.temp_dir)
#            return render_to_response(
#                self.form_params_fail_template,
#                req,
#                errors=initialization_errors,
#            )
#
#        crash = None
#        error_filename = outfile + '.stderr'
#        with open(error_filename, 'wb') as stderr:
#            # I can't eplain why I am
#            # unable to pass stderr as argument:
#            #    result = self.to_class()(args, None, stderr)
#            # Stuff it into sys.stderr instead.
#            sys.stderr = stderr
#            try:
#                errors = []
#                result = self.converter_class[system]()(args)
#            except Exception, e:
#                result = -1
#                errors.append(str(e))
#                crash = traceback.format_exc()
#            finally:
#                sys.stderr = sys.__stderr__
#        if result > 0:
#            with open(error_filename, 'rb') as err:
#                errors.append(err.read())
#
#        log(session, 'rios_to_%s' % (system,), '')
#        log(session, 'args', repr(args))
#        if crash:
#            log(session, 'crash', crash)
#
#        if result == 0:
#            zip_filename = outfile + '.zip'
#            z = zipfile.ZipFile(zip_filename, 'w')
#            if os.stat(error_filename).st_size:
#                z.write(error_filename, '%s.warnings.txt' % outname)
#            z.write(outfile, outname)
#            z.close()
#            with open(zip_filename, 'rb') as z:
#                body = z.read()
#            name = outname + '.zip'
#            shutil.rmtree(self.temp_dir)
#            log(session, 'output.zip', body)
#            return Response(
#                    content_type='application/zip',
#                    content_disposition='attachment; filename="%s"' % name,
#                    body=body)
#        else:
#            shutil.rmtree(self.temp_dir)
#            log(session, 'errors', repr(errors))
#            return render_to_response(
#                self.convert_fail_template,
#                req,
#                errors=errors,
#                system=system
#            )


class HandleNotFound(HandleError):

    code = 404
    template = 'rios.converter:/templates/404.html'

    def __call__(self, req):
        return render_to_response(
                self.template,
                req,
                status=self.code,
                path=req.path)


class HandleRST(HandleFile):

    ext = '.rst'

    def __call__(self, req):
        # Load the file.
        packages = get_packages()
        with packages.open(self.path) as rst_file:
            rst_input = rst_file.read()

        # Render to HTML.
        html_output = docutils.core.publish_string(
                rst_input,
                writer_name='html')

        # Generate the response.
        return Response(html_output)


class HandlePing(HandleLocation):

    path = '/ping'

    def __call__(self, req):
        return Response(content_type='text/plain', body="pong!")
