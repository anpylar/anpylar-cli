#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###############################################################################
# Copyright 2018 The AnPyLar Team. All Rights Reserved.
# Use of this source code is governed by an MIT-style license that
# can be found in the LICENSE file at http://anpylar.com/mit-license
###############################################################################
import argparse
import json
import logging
import os.path
import sys

from .app_component import Componenter
from .logconfig import logconfig
from .utils import makefile_error, readfile_error


def run(pargs=None, name=None):
    args, parser = parse_args(pargs=pargs, name=name)

    logconfig(args.quiet, args.verbose)  # configure logging

    ckwargs = {}
    ckwargs['preamble'] = args.preamble
    ckwargs['licfile'] = args.license
    ckwargs['name'] = args.name
    ckwargs['selector'] = args.selector
    ckwargs['htmlsheet'] = args.htmlsheet
    ckwargs['stylesheet'] = args.stylesheet
    ckwargs['title'] = args.title
    ckwargs['bindings'] = not args.no_bindings
    ckwargs['render'] = not args.no_render
    ckwargs['htmlista'] = args.htmlista
    ckwargs['selectista'] = args.selectista
    ckwargs['pythonista'] = args.pythonista
    ckwargs['comppath'] = args.comppath
    ckwargs['do_import'] = not args.no_import

    # Special handling for htmlpath
    htmlpath = args.htmlpath
    if htmlpath in ['False', 'None', 'True']:
        htmlpath = eval(htmlpath)

    stylepath = args.stylepath
    if stylepath in ['False', 'None', 'True']:
        stylepath = eval(stylepath)

    ckwargs['htmlpath'] = htmlpath
    ckwargs['stylepath'] = stylepath

    logging.info('Generating component')
    comp = Componenter(**ckwargs)
    outdir = os.path.normpath(args.outdir) if args.outdir else None
    outdir = comp.write_out(outdir=outdir, makedir=True)
    logging.info('Generated component content and files to: %s', outdir)

    # PACKAGE.JSON section
    if args.no_package_json:
        sys.exit(0)

    # Try to add to package json
    package_json_dir = os.path.normpath(os.path.join(outdir, '..'))
    pjsonpath = os.path.join(package_json_dir, 'package.json')
    if not os.path.exists(pjsonpath):
        logging.info(('Warning: No package.json found. '
                      'Cannot add package dir to dirs to package'))
        sys.exit(0)

    pjsoncontent = readfile_error(pjsonpath, parser=parser)
    try:
        pjson = json.loads(pjsoncontent)
    except json.JSONDecodeError as e:
        logging.error('package.json seems corrupted: %s', str(e))
        sys.exit(1)

    pjsonpkgs = pjson.get('packages', [])
    if outdir not in pjsonpkgs:
        pjsonpkgs.append(outdir)

    logging.info('Updating packages in package.json with: %s', outdir)
    pjson['packages'] = pjsonpkgs
    pjsontxt = json.dumps(pjson, indent=4)  # indent for beauty
    makefile_error(pjsonpath, pjsontxt, parser=parser)
    logging.info('Done')


def parse_args(pargs=None, name=None):
    if not name:
        name = os.path.splitext(os.path.basename(sys.argv[0]))[0]

    parser = argparse.ArgumentParser(
        prog=name,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=('AnPyLar Component Generator')
    )

    parser.add_argument('name', help=('Name of the component. The string: '
                                      '"Component" will be appended to the '
                                      'name. For example:\n'
                                      '    PyroDetail -> PyroDetailComponent'))

    parser.add_argument('outdir', nargs='?', default=None,
                        help=('Name for the output directory. If not provided '
                              'the name will be generated automatically, by '
                              'lowercasing the name and inserting "_" between '
                              'lowercase-uppercase letters. For example:\n'
                              '    PyroDetail -> pyro_detail. If the '
                              'directory exists (or is a file), nothing will '
                              'be generated'))

    parser.add_argument('--preamble', action='store_true',
                        help='Add python interpreter line and coding info')

    parser.add_argument('--selector', action='store',
                        nargs='?', default=None, const='True',
                        help=('Add a specific selector to the component. '
                              'If the option is given but no value, it will '
                              'be auto-calculate as in: PyroComponent -> '
                              '<pyro-component>'))

    parser.add_argument('--htmlsheet', action='store_true',
                        help='Prepare the component for embedded HTML code')

    parser.add_argument('--stylesheet', action='store_true',
                        help='Prepare the component for embedded styles')

    parser.add_argument('--comppath', action='store',
                        help=('Specify a name for the component code '
                              'If not provided, the default, the name is '
                              'is calculated automatically as in: '
                              'PyroDetail -> pyro_detail.py'))

    parser.add_argument('--htmlpath', action='store', default='True',
                        help=('Specify a value for stylepath. The default is'
                              'True, which means the name for the html file '
                              'to load is calculated automatically as in: '
                              'PyroDetail -> pyro_detail.html. If set to None '
                              ' or False, no html file will be loaded'))

    parser.add_argument('--stylepath', action='store', default='True',
                        help=('Specify a value for stylepath. The default is'
                              'True, which means the name for the stylesheet '
                              'to load is calculated automatically as in: '
                              'PyroDetail -> pyro_detail.css. If set to None '
                              ' or False, no stylesheet will be loaded'))

    pgroup = parser.add_mutually_exclusive_group()
    pgroup.add_argument('--htmlista', action='store_true',
                        help='Component will only render (Default option)')

    pgroup.add_argument('--selectista', action='store_true',
                        help='Component will select nodes for rendering')

    parser.add_argument('--pythonista', action='store_true',
                        help=('Do not add an HTML file. Only Python rendering'
                              'This sets "htmlpat=None"'))

    parser.add_argument('--no-bindings', action='store_true',
                        help='Do not add the bindings directive')

    parser.add_argument('--no-render', action='store_true',
                        help='Do not add a render method')

    parser.add_argument('--license', action='store',
                        help='Name of file containing license text to add')

    # Don't generate a __init__.py file with the imported component
    parser.add_argument('--no-import', action='store_true',
                        help=argparse.SUPPRESS)

    parser.add_argument('--title', action='store',
                        help=('Add a title template to html and attribute to '
                              'the component code'))

    parser.add_argument('--no-package-json', action='store_true',
                        help='Do not update package.json')

    pgroup = parser.add_mutually_exclusive_group()
    pgroup.add_argument('--quiet', '-q', action='store_true',
                        help='Remove output (errors will be reported)')
    pgroup.add_argument('--verbose', '-v', action='store_true',
                        help='Increase verbosity level')

    args = parser.parse_args(pargs)
    return args, parser


if __name__ == '__main__':
    run()
