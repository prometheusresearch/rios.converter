import tempfile

from rex.core import get_packages
from rex.core import get_settings
from rex.core import AnyVal
from rex.core import StrVal
from rex.core import PIntVal
from rex.core import Setting
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
        Parameter('format', StrVal('(yaml)|(json)'), default='yaml'),
        Parameter('instrument_title', StrVal('.+')),
        Parameter('instrument_id', StrVal('[a-z][a-z0-9_]*')),
        Parameter('instrument_version', StrVal('(\d+\.\d+)?')),
        Parameter('localization', StrVal('.*'), default='en'),
        Parameter('outname', StrVal('.+'), default='rios'),
        Parameter('infile', AnyVal()),
        ]

    converter_class = {
        'qualtrics': QualtricsToRios,
        'redcap': RedcapToRios,
        }

            
    def render(self, req,
            system,
            format,
            instrument_title,
            instrument_id,
            instrument_version,
            localization,
            outname,
            infile):

        self.settings = get_settings()
        tempfile.tempdir = self.settings.temp_dir
        temp_dir = tempfile.mkdtemp()
        outfile_prefix = os.path.join(temp_dir, outname)
        args = [
                '--id', instrument_id,
                '--infile', '-',  # stdin
                '--outfile-prefix', outfile_prefix,
                '--instrument-version', instrument_version,
                '--title', instrument_title, ]
        if localization:
            args.extend(['--localization', localization])
        if format:
            args.extend(['--format', format])
        else:
            format = 'yaml'
        error_filename = outfile_prefix + '.stderr'

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
        if result > 0:
            with open(error_filename, 'r') as err:
                errors.append(err.read())
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
            return Response(
                    content_type='application/zip', 
                    content_disposition='attachment; filename="%s"' % name,
                    body=body)
        else:
            shutil.rmtree(temp_dir)
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
        Parameter('format', StrVal('(yaml)|(json)'), default='yaml'),
        Parameter('localization', StrVal('.*'), default='en'),
        Parameter('instrument_file', AnyVal()),
        Parameter('form_file', AnyVal()),
        Parameter('calculationset_file', AnyVal()),
        Parameter('outname', StrVal('.+')), ]

    converter_class = {
        'qualtrics': QualtricsFromRios,
        'redcap': RedcapFromRios,
        }

    def load_file(self, file_field):
        filename = os.path.join(self.temp_dir, file_field.filename)
        with open(filename, 'w') as fo:
            fo.write(file_field.file.read())
        return filename

    def render(self, req,
            system,
            format,
            localization,
            instrument_file,
            form_file,
            calculationset_file,
            outname):
    
        self.settings = get_settings()
        tempfile.tempdir = self.settings.temp_dir
        self.temp_dir = tempfile.mkdtemp()
        outfile = os.path.join(self.temp_dir, outname)
        errors = []
        args = [
                '--verbose',
                '--format', format,
                '--outfile', outfile, 
                ]
        if hasattr(instrument_file, 'filename'):
            args.extend([
                    '--instrument', 
                    '%s' % self.load_file(instrument_file)])                
        else:
            errors.append('An input instrument file is required.')
        if hasattr(form_file, 'filename'):
            args.extend([
                    '--form', 
                    '%s' % self.load_file(form_file)])
        else:
            errors.append('An input form file is required.')
        if hasattr(calculationset_file, 'filename'):
            args.extend([
                    '--calculationset', 
                    '%s' % self.load_file(calculationset_file)])
        if localization:
            args.extend(['--localization', localization])
        if errors:
            shutil.rmtree(self.temp_dir)
            return Response(json={
                    "status": 400,
                    "errors": errors
                    })        
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
        if result > 0:
            with open(error_filename, 'rb') as err:
                errors.append(err.read())
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
            return Response(
                    content_type='application/zip', 
                    content_disposition='attachment; filename="%s"' % name,
                    body=body)
        else:
            shutil.rmtree(self.temp_dir)
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


class HomeCmd(Command):

    path = '/'
    access = 'anybody'
    template = 'rios.converter:/templates/home.rst'

    def render(self, req):
        response = render_to_response(self.template, req, status=200)
        html_output = docutils.core.publish_string(
                response.body,
                writer_name='html')
        return Response(html_output)


class HelloCmd(Command):

    path = '/hello'
    access = 'anybody'
    parameters = [
        Parameter('name', StrVal('[A-Za-z]+'), default='World'),
    ]

    def render(self, req, name):
        return Response("Hello, %s!" % name, content_type='text/plain')
