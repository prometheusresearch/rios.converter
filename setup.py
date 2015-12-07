#
# Copyright (c) 2012-2014, Prometheus Research, LLC
#


from setuptools import setup, find_packages


setup(
    name='rios.converter',
    version="0.1.0",
    description="RIOS converter website",
    long_description=open('README.rst', 'r').read(),
    maintainer="Prometheus Research, LLC",
    maintainer_email="contact@prometheusresearch.com",
    license="AGPLv3",
    url="https://bitbucket.org/prometheus/rios.converter",
    package_dir={'': 'src'},
    packages=find_packages('src'),
    namespace_packages=['rios'],
    install_requires=[
        'rex.web >=3.5, <4',
        'rios.conversion >=0.2, <1',
    ],
    rex_init='rios.converter',
    rex_static='static',
)


