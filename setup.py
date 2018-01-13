#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###############################################################################
# Copyright 2018 The AnPyLar Team. All Rights Reserved.
# Use of this source code is governed by an MIT-style license that
# can be found in the LICENSE file at http://anpylar.com/mit-license
###############################################################################
import os.path
import codecs  # To use a consistent encoding
import setuptools

here = os.path.abspath(os.path.dirname(__file__))

# Get the long description from the relevant file
with codecs.open(os.path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

# Package name
pname = 'anpylar'
gitname = 'anpylar-cli'

# Get the version ... execfile is only on Py2 ... use exec + compile + open
vname = '__version__.py'
with open(os.path.join(pname, vname)) as f:
    exec(compile(f.read(), vname, 'exec'))

# Generate links
gurl = 'https://github.com/anpylar/' + gitname
gdurl = gurl + '/tarball/' + __version__

if True:
    from anpylar.anpylar import AnPyLar

    COMMANDS = []
    for cmd, description in AnPyLar.commands:
        if isinstance(cmd, (list, tuple)):
            cmd, mod = cmd  # unpack potential different module
        else:
            mod = cmd

        cmdstring = ('{pname}-{cmd}={pname}.{mod}:run'
                     .format(pname=pname, cmd=cmd, mod=mod))

        COMMANDS.append(cmdstring)


setuptools.setup(
    name=pname,

    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version=__version__,

    description='Command Line Interface for AnPyLar',
    long_description=long_description,

    # The project's main homepage.
    url=gurl,
    download_url=gdurl,

    # Author details
    author='The AnPyLar Team',
    author_email='anpylar@anpylar.com',

    # Choose your license
    license='MIT',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 5 - Production/Stable',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',

        # Indicate which Topics are covered by the package
        'Topic :: Software Development',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: MIT License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 3',

        # Operating Systems on which it runs
        'Operating System :: OS Independent',
    ],

    # What does your project relate to?
    keywords=['web', 'development'],

    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    # packages=[pname],
    packages=setuptools.find_packages(),

    # List run-time dependencies here.
    # These will be installed by pip when your
    # project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    # install_requires=['six'],

    # List additional groups of dependencies here
    # (e.g. development dependencies).
    # You can install these using the following syntax, for example:
    # $ pip install -e .[dev,test]
    # extras_require={},

    # If there are data files included in your packages that need to be
    # installed, specify them here.  If using Python 2.6 or less, then these
    # have to be included in MANIFEST.in as well.
    # package_data={'sample': ['package_data.dat'],},
    package_data={
        'anpylar.data': [
            'LICENSE.brython',
            'anpylar.auto_vfs.js',
            'anpylar_d.auto_vfs.js',
            'anpylar_js.js',
            'brython.js',
            'brython_stdlib.js',
        ],
    },
    # Although 'package_data' is the preferred approach, in some case you may
    # need to place data files outside of your packages. See:
    # http://docs.python.org/3.4/distutils/setupscript.html#installing-additional-files
    # In this case, 'data_file' will be installed into '<sys.prefix>/my_data'
    # data_files=[('my_data', ['data/data_file'])],

    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
    # entry_points={'console_scripts': ['sample=sample:main',],},
    entry_points={
        'console_scripts': [
            'anpylar=anpylar:anpylar',
        ] + COMMANDS,
    },

    # scripts=[],
)
