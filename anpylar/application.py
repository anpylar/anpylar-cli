#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###############################################################################
# Copyright 2018 The AnPyLar Team. All Rights Reserved.
# Use of this source code is governed by an MIT-style license that
# can be found in the LICENSE file at http://anpylar.com/mit-license
###############################################################################
import argparse
import base64
import json
import os
import os.path
import sys

from .app_component import Componenter
from .app_module import Moduler
from .packaging import Bundler

from . import application_styles

from .utils import makedir_error, makefile_error


# The templates below are used to generate the module depending of the
# options given to the argument parser

Template_Index = '''
<!DOCTYPE html>
<html>
<head>
  <title>{title}</title>

  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">

  <link rel="stylesheet" href="styles.css">
  <script src="anpylar.js" {do_async}></script>

</head>
<body></body>
</html>
'''.strip()


# main code
def run(pargs=None, name=None):
    args, parser = parse_args(pargs=pargs, name=name)

    # Try to generate the application directory
    makedir_error(args.name, parser)

    # Dir is created - switch into
    os.chdir(args.name)

    appname = args.package.capitalize()

    # Component Generation
    ckwargs = {}
    ckwargs['name'] = appname
    if args.license:
        ckwargs['licfile'] = args.license

    if args.title:
        ckwargs['title'] = args.title
    elif args.tutorial:
        ckwargs['title'] = 'Tour of Pyroes'

    ckwargs['htmlista'] = args.htmlista
    ckwargs['selectista'] = args.selectista
    ckwargs['pythonista'] = args.pythonista
    ckwargs['do_import'] = False

    comp = Componenter(**ckwargs)
    outdir = comp.write_out()  # will create 'appname.lower()' dir

    # Create the module inside the directory created by the component
    os.chdir(appname.lower())

    # Module Generation
    mkwargs = {}
    mkwargs['name'] = appname
    mkwargs['submodule'] = False
    if args.license:
        mkwargs['licfile'] = args.license

    mkwargs['bootstrap'] = appname + 'Component'
    mkwargs['do_import'] = True
    mod = Moduler(**mkwargs)
    mod.write_out()

    # go back to the main directory of the application
    os.chdir('..')

    # Add the distribution files: styles.css (empty unless sample), anyplar.js,
    # index.html Index.html
    title = '{}'.format(args.title)
    do_async = 'async' if not args.no_async else ''
    index_html = Template_Index.format(title=title, do_async=do_async)
    makefile_error('index.html', index_html, parser=parser)

    # styles.css
    styles = ''
    if args.tutorial:
        styles = application_styles.styles_css.strip()
    makefile_error('styles.css', styles, parser=parser)

    # anpylar.js
    bundler = Bundler(anpylarize=True)
    bundler.set_br_debug(True)
    # Prepare anpylar.js output path
    APL_path = os.path.join('.', 'anpylar.js')
    bundler.write_bundle(APL_path)

    # Add package information
    if not args.no_package_json:
        package_json = {
            'packages': [args.package],  # only package during creation

            # general info (same fields as brython)
            'app_name': args.app_name,
            'version': args.app_version,
            'author': args.app_author,
            'author_email': args.app_e_mail,
            'license': args.app_license,
            'url': args.app_url,
        }

        jsontxt = json.dumps(package_json, indent=4)  # indent for beauty
        makefile_error('package.json', jsontxt, parser=parser)


def parse_args(pargs=None, name=None):
    if not name:
        name = os.path.splitext(os.path.basename(sys.argv[0]))[0]

    parser = argparse.ArgumentParser(
        prog=name,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=('AnPyLar Application Generator')
    )

    parser.add_argument('name', help=('Name of the application'))

    parser.add_argument('--package', action='store', default='app',
                        help='Name of the application package inside our app')

    parser.add_argument('--no-async', action='store_true',
                        help='Do not load anyplar.js asynchronously')

    parser.add_argument('--title', action='store', default='',
                        help='Title for index.html')

    # Some common options
    parser.add_argument('--no-preamble', action='store_true',
                        help='Skip python interpreter line and coding info')

    parser.add_argument('--license', action='store',
                        help='Name of file containing license text to add')

    pgroup = parser.add_mutually_exclusive_group()
    pgroup.add_argument('--htmlista', action='store_true',
                        help='Component will only render (Default option)')

    pgroup.add_argument('--selectista', action='store_true',
                        help='Component will select nodes for rendering')

    pgroup.add_argument('--pythonista', action='store_true',
                        help=('Component will only render. '
                              'No html file generation'))

    parser.add_argument('--tutorial', action='store_true',
                        help='Add title and styles from Tour of Pyroes')

    pgroup = parser.add_argument_group(title='package.json')
    pgroup.add_argument('--no-package-json', action='store_true',
                        help='Skip generation of package.json')

    pgroup.add_argument('--app-name', action='store', default='',
                        help='Application name for package json')

    pgroup.add_argument('--app-version', action='store', default='',
                        help='Application version name for package json')

    pgroup.add_argument('--app-author', action='store', default='',
                        help='Author name for package json')

    pgroup.add_argument('--app-e-mail', action='store', default='',
                        help='E-Mail for package json')

    pgroup.add_argument('--app-license', action='store', default='',
                        help='License for package.json')

    pgroup.add_argument('--app-url', action='store', default='',
                        help='Application URL for package.json')

    args = parser.parse_args(pargs)
    return args, parser


if __name__ == '__main__':
    run()
