****************
 RIOS Converter 
****************

.. contents:: Table of Contents


Overview
========

This package implements the RIOS conversion server which provides an API
to the conversions implemented in `rios.conversion`_

See the `convert page source`_ for more details.

Installation
============

rios.converter is a rex.web application which needs no database.
Access to all pages is granted to **anybody**, 
so no authentication is required.  
This converter should be available to the general public.

::

    $ virtualenv --system-site-packages rios.converter
    $ cd rios.converter
    $ . bin/activate
    $ pip install rios.converter

Create a simple **rex.yaml**.  For example::

    $ cat >rex.yaml <<!
    project: rios.converter
    uwsgi:
        uwsgi-socket: localhost:5839
    !

Start the server::

    $ rex start

.. _rios.conversion: https://bitbucket.org/prometheus/rios.conversion/overview 
.. _convert page source: https://bitbucket.org/prometheus/rios.converter/src/tip/static/templates/convert.rst

