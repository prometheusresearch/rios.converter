****************
 RIOS Converter 
****************

.. contents:: Table of Contents


Overview
========

This package implements the RIOS conversion server which provides an API
to the conversions implemented in `rios.conversion`_

See the `home page source`_ for more details.

Installation
============

rios.converter is a rex.web application which needs no database.

::

    $ virtualenv --system-site-packages rios.converter
    $ cd rios.converter
    $ . bin/activate
    $ hg clone ssh://hg@bitbucket.org/prometheus/rios.converter
    $ pip install -e rios.converter

Create a simple **rex.yaml**.  For example::

    $ cat >rex.yaml <<!
    project: rios.converter
    uwsgi:
        uwsgi-socket: localhost:5839
    !

Start the server::

    $ rex start

.. _rios.conversion: https://bitbucket.org/prometheus/rios.conversion/overview 
.. _home page source: https://bitbucket.org/prometheus/rios.converter/src/tip/static/templates/home.rst

