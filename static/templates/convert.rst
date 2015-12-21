Welcome to the RIOS Instrument Converter API
--------------------------------------------
  
Convert to RIOS
---------------

To convert an instrument from another system to RIOS,
POST an **enctype="multipart/form-data"** request 
to:

  **{{PATH_URL}}convert/to/rios?**\ *parameters*

parameters:

  **system=**\ (**qualtrics**)|(**readcap**)
    Required.
    The system to convert from.

  **infile=**
    Required.
    The input file to convert.
    
  **localization=**
    Default is **en**.
    RIOS is multi-lingual.
    You must provide the language code the input file is written in.
    
  **outname=**
    Required.
    Use this parameter to name the output files.

  **format=**\ (**json**)|(**yaml**)
    Default is **yaml**.
    Select the format for the output files.
    
  **instrument_title=**
    Required.
    You must provide the instrument title.
    
  **instrument_id=**
    Required.
    You must provide the instrument ID.  
    This must consist only of lowercase letters, digits, or underscore, 
    and must begin with a letter.
    
  **instrument_version=**
    Required.
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
    Required.
    The system to convert to.

  **instrument_file=**
    Required.
    The input instrument to convert.

  **form_file=**
    Required.
    The input form to convert.

  **calculationset_file=**
    Optional.
    The input calculation set to convert.

  **outname=**
    Required.
    Use this parameter to name the output files.

  **localization=**
    Default is **en**.
    RIOS is multi-lingual.  
    You must select which language to extract.

Response
--------

The response will be a zip file to download, 
or in the case of an error,
a JSON object which includes the attributes **status** (the html status code), 
and **errors** (a list of error message strings).
The zip file will contain the converted instrument file(s) 
and may contain a file whose name ends in **.warnings.txt**, 
which contains any warning messages emitted by the converter.

When converting to RIOS, the converter appends the suffixes
**_i**, **_f**, and **_c** to the filenames of the 
instrument, form, and calculation set respectively.
