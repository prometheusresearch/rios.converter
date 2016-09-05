#
# Copyright (c) 2016, Prometheus Research, LLC
#


import csv
import six
import collections


from props.csvtoolkit import (
    SimpleCSVFileValidator,
    SimpleLogger,

    EnumVal,
    AnyVal,

    StringLoader,

    ValidationException,
)


__all__ = (
    'RedcapLegacyCsvValidator',
    'RedcapModernCSVValidator',
    'StringLoader',
)


DEFAULT_DISPLAY_LIMIT = 30


class RedcapCsvValidationLogger(SimpleLogger):
    """ REDCap CSV validation logger. """

    pass


class RedcapLegacyCsvValidator(SimpleCSVFileValidator):
    """ Validate legacy REDCap instrument files """

    # TODO: Implement validation
    pass


class RedcapModernCsvValidator(SimpleCSVFileValidator):
    """ Validates modern REDCap instrument files """

    validators = {
        'Branching Logic (Show field only if...)': [AnyVal()],
        'Choices, Calculations, OR Slider Labels': [AnyVal()],
        'Custom Alignment': [AnyVal()],
        'Field Label': [AnyVal()],
        'Field Note': [AnyVal()],
        'Field Type': [
            EnumVal([
                'text',
                'notes',
                'dropdown',
                'radio',
                'checkbox',
                'calc',
                'slider',
                'truefalse',
                'yesno',
            ])
        ],
        'Form Name': [AnyVal()],
        'Identifier?': [AnyVal()],
        'Question Number (surveys only)': [AnyVal()],
        'Required Field?': [AnyVal()],
        'Section Header': [AnyVal()],
        'Text Validation Max': [AnyVal()],
        'Text Validation Min': [AnyVal()],
        'Text Validation Type OR Show Slider Number': [AnyVal()],
        'Variable / Field Name': [AnyVal()],
    }

    REQUIRED_HEADERS = [
        "Variable / Field Name",
        "Form Name",
        "Field Type",
        "Field Label",
        "Choices, Calculations, OR Slider Labels",
    ]

    def validate(self):  # noqa: MC0001
        # Temporary hack for validator instantiations not being restarted
        # between validation passes
        self.validators = {
            'Branching Logic (Show field only if...)': [AnyVal()],
            'Choices, Calculations, OR Slider Labels': [AnyVal()],
            'Custom Alignment': [AnyVal()],
            'Field Label': [AnyVal()],
            'Field Note': [AnyVal()],
            'Field Type': [
                EnumVal([
                    'text',
                    'notes',
                    'dropdown',
                    'radio',
                    'checkbox',
                    'calc',
                    'slider',
                    'truefalse',
                    'yesno',
                ])
            ],
            'Form Name': [AnyVal()],
            'Identifier?': [AnyVal()],
            'Question Number (surveys only)': [AnyVal()],
            'Required Field?': [AnyVal()],
            'Section Header': [AnyVal()],
            'Text Validation Max': [AnyVal()],
            'Text Validation Min': [AnyVal()],
            'Text Validation Type OR Show Slider Number': [AnyVal()],
            'Variable / Field Name': [AnyVal()],
        }

        failure_tracker = False

        reader = csv.DictReader(
            # Get rid of Excel/MS/DOS newlines
            self.source.open().read().replace('\r\n', '\n').splitlines(),
            delimiter=self.delimiter,
            quoting=csv.QUOTE_ALL,
            quotechar='"',
            skipinitialspace=True
        )

        # Check for fieldnames
        if not reader.fieldnames:
            self.logger.log("Source CSV has no field names or is empty")
            failure_tracker = True

        # Check for required headers
        missing_headers = []
        if not all(value in reader.fieldnames
                    for value in self.REQUIRED_HEADERS):
            for v in self.REQUIRED_HEADERS:
                if v not in reader.fieldnames:
                    missing_headers.append(v)
            missing_headers = list(set(missing_headers))  # Get unique values
            self.logger.log('Missing required headers:\n  {}'.format(
                "\"" + "\",\n  \"".join(missing_headers) + "\""))
            failure_tracker = True

        # Check for duplicate column names
        if self.check_duplicate_headers and \
                (len(reader.fieldnames) != len(set(reader.fieldnames))):
            duplicates = find_duplicates_by_idx(reader.fieldnames)
            self.logger.log('Found duplicate column headers:')
            for header, idxs in six.iteritems(duplicates):
                locations = ", ".join([str(idx) for idx in idxs])
                self.logger.log('  Header: ' + header +
                                ', columns: ' + locations)
            failure_tracker = True

        # Check for missing validators
        self.missing_validators = set(reader.fieldnames) - set(self.validators)
        if self.missing_validators:
            self.logger.log("\nMissing validators for:")
            log_missing(self.missing_validators, self.logger)
            failure_tracker = True

        # Log immediate failing validation failures
        if self.logger.check():
            return False

        # Check for missing fields
        self.missing_fields = set(self.validators) - set(reader.fieldnames)
        if self.missing_fields:
            self.logger.log("Missing expected column fields:")
            log_missing(self.missing_fields, self.logger)
            failure_tracker = True

        # Validation algorithm
        cols_trckr = []
        for line, row in enumerate(reader):
            for field_name, field in six.iteritems(row):
                try:
                    # KeyError: Row has too many defined fields
                    for validator in self.validators[field_name]:
                        try:
                            validator.validate(field, row=row)
                        except ValidationException as exc:
                            self.failures[field_name][line].append(exc)
                            validator.failure_count += 1
                except KeyError as exc:
                    print "FAIL"
                    cols_trckr.append(str(line))
        if len(cols_trckr) > 0:
            self.logger.log(
                'Found a column without a header. Check for too many'
                ' fields defined on line(s):  {}'.format(", ".join(cols_trckr))
            )
            failure_tracker = True

        # Check for validation errors
        if failure_tracker and not self.failures:
            return False
        elif self.failures:
            self.logger.log("\nValidation failures:")
            log_validator_failures(self.validators, self.logger)
            self.logger.log("\nDetail error log:")
            log_failures(self.failures, self.logger)
            return False
        else:
            self.logger.log("Successful validation!\n")
            return True


def log_failures(failures, logger):
    for field_name, field_failure in six.iteritems(failures):
        logger.log("  Failure in column: \"{}\":".format(field_name))
        for i, (row, errors) in enumerate(six.iteritems(field_failure)):
            logger.log("    Line: {}".format(row))
            for error in errors:
                logger.log("      {}".format(error))


def log_validator_failures(validators, logger):
    for field_name, validators_list in six.iteritems(validators):
        for validator in validators_list:
            if validator.fails():
                logger.log(
                    "  {} failed {} time(s) on field: '{}'".format(
                        validator.__class__.__name__, validator.failure_count,
                        field_name))
                invalid = list(validator.fails())
                display = ["'{}'".format(field)
                           for field in invalid[:DEFAULT_DISPLAY_LIMIT]]
                hidden = len(invalid[DEFAULT_DISPLAY_LIMIT:])
                logger.log(
                    "    Invalid fields: [{}]".format(", ".join(display)))
                if hidden:
                    logger.log(
                        "    ({} more suppressed)".format(hidden))


def log_missing(missing_items, logger):
    logger.log(
        "{}".format(",\n".join(["  '{}'".format(field)
                               for field in sorted(missing_items)]) + "\n"))


def find_duplicates_by_idx(inlist):
    """
    Finds duplicate entries in a list and returns their index in the list.

    :param inlist: List with possible duplicates
    :type list: list
    :returns: Dict of value names and idxs
    :rtype: dictionary
    """
    assert isinstance(inlist, list), 'Function parameter must be of type list'
    enumed_list = collections.defaultdict(list)
    for idx, value in enumerate(inlist):
        enumed_list[value].append(idx)
    indexed_duplicates = {
        value: idxs
        for value, idxs in six.iteritems(enumed_list)
        if len(idxs) > 1
    }
    return indexed_duplicates
