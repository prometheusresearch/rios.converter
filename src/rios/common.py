#
# Copyright (c) 2016, Prometheus Research, LLC
#


__all__ = (
    'csv_data_dictionary',
)


def csv_data_dictionary(csv):
    """
    Generates a dictionary with a key per header value. The values are lists
    containing dicts of value and line number (for each value's location)
    key-value pairs.

    For example:
        {
            'header_1': [
                {'value_1', value_1_row_number},
                {'value_2', value_2_row_number},
                ...]
            'header_2': ...,
            ...
        }

    :param header: CSV file
    :type header: Open file buffer
    :returns: Data dictionary of CSV
    :rtype: dictionary
    """
    assert hasattr(csv, 'next')
    csv_header = csv.next()
    csv_data_dictionary = {}
    for header in csv_header:
        csv_data_dictionary[header] = []
    for row in csv:
        line_num = str(int(csv.line_num)) # Get rid of 'L' char
        for header, value in zip(csv_header, row):
            csv_data_dictionary[header].append({value: line_num})
    return csv_data_dictionary
