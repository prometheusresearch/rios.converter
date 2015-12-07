Welcome to the RIOS Instrument Converter API
============================================

Links to conversion forms
-------------------------

`Convert to RIOS`_

`Convert from RIOS`_

.. _Convert to RIOS: {{PATH_URL}}convert/to
.. _Convert from RIOS: {{PATH_URL}}convert/from
  
Convert to RIOS
---------------

To convert an instrument from another system to RIOS,
POST an **enctype="multipart/form-data"** request 
to:

  **{{PATH_URL}}convert/to/rios?**\ *parameters*

parameters:

  **system=**\ (**qualtrics**)|(**readcap**)
    required

    The system to convert from.

  **infile=**
    required
    
    The input file to convert.
    
  **localization=**
    default is **en**

    RIOS is multi-lingual.  
    You must provide the language code the input file is written in.
    
  **outname=**
    required

    Use this parameter to name the output files.

  **format=**\ (**json**)|(**yaml**)     
    default is **yaml**

    Select the format for the output files.
    
  **instrument_title=**
    required

    You must provide the instrument title.
    
  **instrument_id=**
    required

    You must provide the instrument ID.  
    This must consist only of lowercase letters, digits, or underscore, 
    and must begin with a letter.
    
  **instrument_version=**
    default is **1.0**

    The instrument version.
    This must consist of two numbers separated by a period.
      
    A RIOS instrument is uniquely identified 
    by (instrument_id, instrument_version)


Convert from RIOS
-----------------

To convert an instrument from RIOS to another system,
POST an **enctype="multipart/form-data"** request 
to:

  **{{PATH_URL}}convert/from/rios?**\ *parameters*

parameters:

  **system=**\ (**qualtrics**)|(**readcap**)
    required

    The system to convert to.

  **instrument_file=**
    required

    The input instrument to convert.

  **form_file=**
    required

    The input form to convert.

  **calculationset_file=**
    optional

    The input calculation set to convert.

  **outname=**
    required

    Use this parameter to name the output files.

  **localization=**
    default is **en**

    RIOS is multi-lingual.  
    You must select which language to extract.

Response
--------

The response will be a zip file to download, 
or in the case of an error,
a JSON object with attributes **status** (the html status code), 
and **errors** (a list of error message strings).

The zip file will contain the converted instrument file(s) 
and may contain a file whose name ends in **.warnings.txt**, 
which contains any warning messages emitted by the converter.

When converting to RIOS, the converter appends the suffixes
**_i**, **_f**, and **_c** to the filenames of the 
instrument, form, and calculation set respectively.
