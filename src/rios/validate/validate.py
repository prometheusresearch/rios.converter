#
# Copyright (c) 2016, Prometheus Research, LLC
#


__all__ = (
    'RedcapFileValidate',
    'QualtricsFileValidate',
)


class FileValidate(object):
    """ Abstract base class for file validation. """

    def __init__(self, _file):
        if not hasattr(_file, 'read') and hasattr(_file, 'seek'):
            raise TypeError('Initialization requires a file-like object')

    def validate(self):
        raise NotImplementedError


class RedcapFileValidate(object):
    """ Validation mechanism for REDCap files. """

    def __init__(self, csv_file):
        super(RedcapFileValidate, self).__init__(csv_file)
        self.csv_file = csv_file

    def validate(self):
        return True


class QualtricsFileValidate(object):
    """ Validation mechanism for Qualtrics files. """

    def __init__(self, qsf_file):
        super(QualtricsFileValidate, self).__init__(qsf_file)
        self.qsf_file = qsf_file

    def validate(self):
        return True
