from rex.core import get_settings
from rex.core import Rex
from webob import Request

def test_pages():
    app = Rex(
        'rios.converter',
        temp_dir='tests/sandbox',
        log_dir='tests/sandbox/log_dir'
    )
    app.on()
    print Request.blank('/').get_response(app)
    print Request.blank('/convert/to').get_response(app)
    print Request.blank('/convert/from').get_response(app)

    with open('tests/redcap/format_1.csv') as input_file:
        print Request.blank('/convert/to/rios', POST={
                'system': 'redcap', 
                'format': 'yaml', 
                'instrument_title':'Test title', 
                'instrument_id': 'id0',
                'instrument_version':'1.6',
                'localization':'en', 
                'outname':'red2rio-out', 
                'infile': ('format_1.csv', input_file),
                }).get_response(app)

    with open('tests/qualtrics/test_1.qsf') as input_file:
        print Request.blank('/convert/to/rios', POST={
                'system': 'qualtrics', 
                'format': 'yaml', 
                'instrument_title':'Test title', 
                'instrument_id': 'id0',
                'instrument_version':'1.6',
                'localization':'en', 
                'outname':'q2rio-out', 
                'infile': ('test_1.qsf', input_file),
                }).get_response(app)
    app.off()

def test_rios_to_redcap():
    app = Rex(
        'rios.converter',
        temp_dir='tests/sandbox',
        log_dir='tests/sandbox/log_dir'
    )
    app.on()

    i_file = open('tests/redcap/format_1_i.yaml')
    f_file = open('tests/redcap/format_1_f.yaml')
    c_file = open('tests/redcap/format_1_c.yaml')
    print Request.blank('/convert/from/rios', POST={
                'system': 'redcap', 
                'format': 'yaml', 
                'instrument_file': ('format_1_i.yaml', i_file),
                'form_file': ('format_1_f.yaml', f_file),
                'calculationset_file': ('format_1_c.yaml', c_file),
                'outname':'rio2red-out.csv', 
                }).get_response(app)
    i_file.close()
    f_file.close()
    c_file.close()
    app.off()

def test_rios_to_qualtrics():
    app = Rex(
        'rios.converter',
        temp_dir='tests/sandbox',
        log_dir='tests/sandbox/log_dir'
    )
    app.on()

    i_file = open('tests/redcap/format_1_i.yaml')
    f_file = open('tests/redcap/format_1_f.yaml')
    c_file = open('tests/redcap/format_1_c.yaml')
    print Request.blank('/convert/from/rios', POST={
                'system': 'qualtrics', 
                'format': 'yaml', 
                'instrument_file': ('format_1_i.yaml', i_file),
                'form_file': ('format_1_f.yaml', f_file),
                'calculationset_file': ('format_1_c.yaml', c_file),
                'outname':'rio2q-out.txt', 
                }).get_response(app)
    i_file.close()
    f_file.close()
    c_file.close()
    app.off()
