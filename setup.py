#
# Copyright (c) 2012-2014, Prometheus Research, LLC
#


from setuptools import setup, find_packages


setup(
    name='rios.converter',
    version='0.4.0',
    description="RIOS converter website",
    long_description=open('README.rst', 'r').read(),
    maintainer="Prometheus Research, LLC",
    maintainer_email="contact@prometheusresearch.com",
    license="Apache Software License 2.0",
    url="https://bitbucket.org/prometheus/rios.converter",
    package_dir={'': 'src'},
    packages=find_packages('src'),
    namespace_packages=['rios'],
    install_requires=[
        'rex.web >=3.5, <4',
        'rios.conversion == 0.4.0',
        'python-magic == 0.4.12',
    ],
    extras_require={
        'dev': [
            'pbbt>=0.1.4,<1',
            'coverage>=3.7,<4',
            'nose>=1.3,<2',
            'nosy>=1.1,<2',
            'prospector[with_pyroma]>=0.10,<0.11',
            'twine>=1.5,<2',
            'wheel>=0.24,<0.25',
            'Sphinx>=1.3,<2',
            'sphinx-autobuild>=0.5,<0.6',
            'tox>=2,<3',
            'flake8>=2.5.0,<3',
        ],
    },
    test_suite='nose.collector',
    rex_init='rios.converter',
    rex_static='static',
)
