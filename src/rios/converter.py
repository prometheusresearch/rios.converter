import tempfile
import traceback
import datetime

from rex.core import get_packages
from rex.core import get_settings
from rex.core import AnyVal
from rex.core import StrVal
from rex.core import Setting
from rex.core import Initialize, Error
from rex.web import Command
from rex.web import HandleError
from rex.web import HandleFile
from rex.web import HandleLocation
from rex.web import Parameter
from rex.web import render_to_response
from webob import Response
import docutils.core
import glob
import os
import shutil
import sys
import zipfile
from rios.conversion.redcap.to_rios import RedcapToRios
from rios.conversion.redcap.from_rios import RedcapFromRios
from rios.conversion.qualtrics.to_rios import QualtricsToRios
from rios.conversion.qualtrics.from_rios import QualtricsFromRios


class TempDirSetting(Setting):
    """Directory with temporary data."""
    name = 'temp_dir'
    default = None
    validate = StrVal()

class LogDirSetting(Setting):
    """Directory to log conversion activities to for future research/analysis"""
    name = 'log_dir'
    validate = StrVal()


class ConverterInitialize(Initialize):
    def __call__(self):
        log_dir = get_settings().log_dir
        if not os.path.isdir(log_dir):
            raise Error('Log Directory (%s) doesn\'t exist' % (log_dir,))
        if not os.access(log_dir, os.R_OK|os.W_OK|os.X_OK):
            raise Error('Log Directory (%s) not writable' % (log_dir,))


def log(session, filename, content):
    log_dir = os.path.join(get_settings().log_dir, session)
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)
    fp = open(os.path.join(log_dir, filename), 'wb')
    fp.write(content)
    fp.close()

def log_file(session, filepath):
    log_dir = os.path.join(get_settings().log_dir, session)
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)
    shutil.copy(filepath, log_dir)


class HomeCmd(Command):

    path = '/'
    access = 'anybody'
    #template = 'rios.converter:/templates/home.rst'
    template = 'rios.converter:/templates/home.html'

    def render(self, req):
        return render_to_response(self.template, req, status=200)
        #response = render_to_response(self.template, req, status=200)
        #html_output = docutils.core.publish_string(
        #        response.body,
        #        writer_name='html')
        #return Response(html_output)


class ConvertDoc(Command):

    path = '/convertdoc'
    access = 'anybody'
    template = 'rios.converter:/templates/convert.html'

    def render(self, req):
        return render_to_response(self.template, req, status=200)


class Convert(Command):

    path = '/convert'
    access = 'anybody'
    template = 'rios.converter:/templates/convert.rst'

    def render(self, req):
        response = render_to_response(self.template, req, status=200)
        html_output = docutils.core.publish_string(
                response.body,
                writer_name='html')
        return Response(html_output)


class ConvertFrom(Command):

    path = '/convert/from'
    access = 'anybody'
    template = 'rios.converter:/templates/from_rios.html'

    def render(self, req):
        return render_to_response(self.template, req, status=200)


class ConvertTo(Command):

    path = '/convert/to'
    access = 'anybody'
    template = 'rios.converter:/templates/to_rios.html'

    def render(self, req):
        return render_to_response(self.template, req, status=200)


class ConvertToRios(Command):

    path = '/convert/to/rios'
    access = 'anybody'
    parameters = [
        Parameter('system', StrVal('(qualtrics)|(redcap)'), ),
        Parameter('format', StrVal('(yaml)|(json)')),
        Parameter('instrument_title', StrVal('.*')),
        Parameter('instrument_id', StrVal('([a-z][a-z0-9_]*)?')),
        Parameter('instrument_version', StrVal('(\d+\.\d+)?')),
        Parameter('localization', StrVal('.*')),
        Parameter('outname', StrVal('.*')),
        Parameter('infile', AnyVal()),
        ]

    converter_class = {
        'qualtrics': QualtricsToRios,
        'redcap': RedcapToRios,
        }

    def render(
            self,
            req,
            system,
            format,
            instrument_title,
            instrument_id,
            instrument_version,
            localization,
            outname,
            infile):

        session = datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')
        self.settings = get_settings()
        tempfile.tempdir = self.settings.temp_dir
        temp_dir = tempfile.mkdtemp()
        outfile_prefix = os.path.join(temp_dir, outname)
        errors = []
        if not hasattr(infile, 'file'):
            errors.append('Input file is required.')
        if not outname:
            errors.append('Output filename prefix is required.')
        if not instrument_version:
            instrument_version = '1.0'
        args = [
                '--infile', '-',  # stdin
                '--outfile-prefix', outfile_prefix,
                '--instrument-version', instrument_version, ]
        if system == 'redcap':
            if not instrument_id:
                errors.append('Instrument ID is required.')
            if not instrument_title:
                errors.append('Instrument Title is required.')
            args.extend([
                '--id', instrument_id,
                '--title', instrument_title, ])
        if localization:
            args.extend(['--localization', localization])
        if format:
            args.extend(['--format', format])
        else:
            format = 'yaml'
        error_filename = outfile_prefix + '.stderr'

        if errors:
            shutil.rmtree(temp_dir)
            return Response(json={
                    "status": 400,
                    "errors": errors
                    })
        crash = None
        with open(error_filename, 'wb') as stderr:
            sys.stdin = infile.file
            # I can't explain why I am
            # unable to pass stderr as argument:
            #    result = self.to_class()(args, None, stderr)
            # Stuff it into sys.stderr instead.
            sys.stderr = stderr
            try:
                errors = []
                result = self.converter_class[system]()(args)
            except Exception, e:
                result = -1
                errors.append(str(e))
                crash = traceback.format_exc()
            finally:
                sys.stderr = sys.__stderr__
        if result > 0:
            with open(error_filename, 'r') as err:
                errors.append(err.read())

        log(session, '%s_to_rios' % (system,), '')
        infile.file.seek(0)
        log(session, 'infile', infile.file.read())
        log(session, 'args', repr(args))
        if crash:
            log(session, 'crash', crash)

        if result == 0:
            zip_filename = outfile_prefix + '.zip'
            z = zipfile.ZipFile(zip_filename, 'w')
            if os.stat(error_filename).st_size:
                z.write(error_filename, '%s.warnings.txt' % outname)
            for rios_file in glob.glob('%s*.%s' % (outfile_prefix, format)):
                basename = os.path.basename(rios_file)
                z.write(rios_file, basename)
            z.close()
            with open(zip_filename, 'rb') as z:
                body = z.read()
            name = outname + '.zip'
            shutil.rmtree(temp_dir)
            log(session, 'output.zip', body)
            return Response(
                    content_type='application/zip',
                    content_disposition='attachment; filename="%s"' % name,
                    body=body)
        else:
            shutil.rmtree(temp_dir)
            log(session, 'errors', repr(errors))
            return Response(json={
                    "result": str(result),
                    "args": args,
                    "status": 400,
                    "errors": errors
                    })


class ConvertFromRios(Command):

    path = '/convert/from/rios'
    access = 'anybody'
    parameters = [
        Parameter('system', StrVal('(qualtrics)|(redcap)'), ),
        Parameter('format', StrVal('(yaml)|(json)')),
        Parameter('localization', StrVal('.*')),
        Parameter('instrument_file', AnyVal()),
        Parameter('form_file', AnyVal()),
        Parameter('calculationset_file', AnyVal()),
        Parameter('outname', StrVal('.*')), ]

    converter_class = {
        'qualtrics': QualtricsFromRios,
        'redcap': RedcapFromRios,
        }

    def load_file(self, session, file_field):
        filename = os.path.join(self.temp_dir, file_field.filename)
        with open(filename, 'w') as fo:
            fo.write(file_field.file.read())
        log_file(session, filename)
        return filename

    def render(
            self,
            req,
            system,
            format,
            localization,
            instrument_file,
            form_file,
            calculationset_file,
            outname):

        session = datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')
        self.settings = get_settings()
        tempfile.tempdir = self.settings.temp_dir
        self.temp_dir = tempfile.mkdtemp()
        outfile = os.path.join(self.temp_dir, outname)
        errors = []
        if not outname:
            errors.append('Output filename prefix is required.')
        if not format:
            format = 'yaml'
        args = [
                '--verbose',
                '--format', format,
                '--outfile', outfile,
                ]
        if hasattr(instrument_file, 'filename'):
            args.extend([
                    '--instrument',
                    '%s' % self.load_file(session, instrument_file)])
        else:
            errors.append('An input instrument file is required.')
        if hasattr(form_file, 'filename'):
            args.extend([
                    '--form',
                    '%s' % self.load_file(session, form_file)])
        else:
            errors.append('An input form file is required.')
        if hasattr(calculationset_file, 'filename'):
            args.extend([
                    '--calculationset',
                    '%s' % self.load_file(session, calculationset_file)])
        if localization:
            args.extend(['--localization', localization])
        if errors:
            shutil.rmtree(self.temp_dir)
            return Response(json={
                    "status": 400,
                    "errors": errors
                    })
        crash = None
        error_filename = outfile + '.stderr'
        with open(error_filename, 'wb') as stderr:
            # I can't eplain why I am
            # unable to pass stderr as argument:
            #    result = self.to_class()(args, None, stderr)
            # Stuff it into sys.stderr instead.
            sys.stderr = stderr
            try:
                result = self.converter_class[system]()(args)
            except Exception, e:
                result = -1
                errors.append(str(e))
                crash = traceback.format_exc()
            finally:
                sys.stderr = sys.__stderr__
        if result > 0:
            with open(error_filename, 'rb') as err:
                errors.append(err.read())

        log(session, 'rios_to_%s' % (system,), '')
        log(session, 'args', repr(args))
        if crash:
            log(session, 'crash', crash)

        if result == 0:
            zip_filename = outfile + '.zip'
            z = zipfile.ZipFile(zip_filename, 'w')
            if os.stat(error_filename).st_size:
                z.write(error_filename, '%s.warnings.txt' % outname)
            z.write(outfile, outname)
            z.close()
            with open(zip_filename, 'rb') as z:
                body = z.read()
            name = outname + '.zip'
            shutil.rmtree(self.temp_dir)
            log(session, 'output.zip', body)
            return Response(
                    content_type='application/zip',
                    content_disposition='attachment; filename="%s"' % name,
                    body=body)
        else:
            shutil.rmtree(self.temp_dir)
            log(session, 'errors', repr(errors))
            return Response(json={
                    "result": str(result),
                    "args": args,
                    "status": 400,
                    "errors": errors
                    })


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
