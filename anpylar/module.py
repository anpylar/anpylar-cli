#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###############################################################################
# Copyright 2018 The AnPyLar Team. All Rights Reserved.
# Use of this source code is governed by an MIT-style license that
# can be found in the LICENSE file at http://anpylar.com/mit-license
###############################################################################
import argparse
import json
import os.path
import sys

from .app_module import Moduler
from .utils import readfile_error, makefile_error


# main code
def run(pargs=None, name=None):
    args, parser = parse_args(pargs=pargs, name=name)

    mkwargs = {}
    mkwargs['preamble'] = args.preamble
    mkwargs['licfile'] = args.license
    mkwargs['bootstrap'] = args.bootstrap
    mkwargs['components'] = not args.no_components
    mkwargs['name'] = args.name
    mkwargs['bindings'] = not args.no_bindings
    mkwargs['services'] = not args.no_services
    mkwargs['routes'] = not args.no_routes
    mkwargs['init'] = not args.no_init
    mkwargs['modpath'] = args.modpath
    mkwargs['do_import'] = args.do_import
    mkwargs['submodule'] = args.submodule

    mod = Moduler(**mkwargs)
    outdir = os.path.normpath(args.outdir) if args.outdir else None
    outdir = mod.write_out(outdir=outdir, makedir=True)

    if not args.submodule:  # no need to update package.json
        sys.exit(0)

    # PACKAGE.JSON section
    if args.no_package_json:
        sys.exit(0)

    # Try to add to package json
    package_json_dir = os.path.normpath(os.path.join(outdir, '..'))
    pjsonpath = os.path.join(package_json_dir, 'package.json')
    if not os.path.exists(pjsonpath):
        print('Warning: No package.json found. Cannot add package dir '
              'to dirs to package')
        sys.exit(0)

    pjsoncontent = readfile_error(pjsonpath, parser=parser)
    try:
        pjson = json.loads(pjsoncontent)
    except json.JSONDecodeError as e:
        print('package.json seems corrupted:', e)
        sys.exit(0)

    pjsonpkgs = pjson.get('packages', [])
    if outdir not in pjsonpkgs:
        pjsonpkgs.append(outdir)

    print('Updating packages in package.json with:', outdir)
    pjson['packages'] = pjsonpkgs
    pjsontxt = json.dumps(pjson, indent=4)  # indent for beauty
    makefile_error(pjsonpath, pjsontxt, parser=parser)


def parse_args(pargs=None, name=None):
    if not name:
        name = os.path.splitext(os.path.basename(sys.argv[0]))[0]

    parser = argparse.ArgumentParser(
        prog=name,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=('AnPyLar Component Generator')
    )

    parser.add_argument('name', help=('Name of the module. The string: '
                                      '"Module" will be appended to the '
                                      'name. For example:\n'
                                      '    Pyro -> PyroModule'))

    parser.add_argument('outdir', nargs='?', default=None,
                        help=('Name for the output directory. If not provided '
                              'the name will be generated automatically, by '
                              'lowercasing the name and inserting "_" between '
                              'lowercase-uppercase letters. For example:\n'
                              '    PyroDetail -> pyro_detail. If the '
                              'directory exists (or is a file), nothing will '
                              'be generated'))

    parser.add_argument('--submodule', action='store_true',
                        help='Create a subdirectory for the module')

    parser.add_argument('--preamble', required=False, action='store_true',
                        help='Add python interpreter line and coding info')

    parser.add_argument('--modpath', required=False, action='store',
                        help=('Specify a name for the module code file '
                              'If not provided, the default, the name is '
                              'is calculated automatically as in: '
                              'PyroDetail -> pyro_detail.py'))

    parser.add_argument('--no-bindings', required=False, action='store_true',
                        help='Do not add the bindings directive')

    parser.add_argument('--no-services', required=False, action='store_true',
                        help='Do not add the services directive')

    parser.add_argument('--no-routes', required=False, action='store_true',
                        help='Do not add the routes directive')

    parser.add_argument('--no-components', required=False, action='store_true',
                        help=('Do not add the components directive. The '
                              'bootstrap option overrides this'))

    parser.add_argument('--bootstrap', required=False, action='store',
                        help=('List of comma separated names of components '
                              'to bootstrap. Import statements will be added '
                              'with the following naming convention: '
                              'CompName -> from .comp_name import Compname'))

    parser.add_argument('--no-init', required=False, action='store_true',
                        help='Do not add an init method')

    parser.add_argument('--license', required=False, action='store',
                        help='Name of file containing license text to add')

    parser.add_argument('--import', required=False, action='store_true',
                        dest='do_import',  # avoid conflicht with kw
                        help='Add __init__.py an import even if no submodule')

    parser.add_argument('--no-package-json', action='store_true',
                        help='Do not update package.json')

    args = parser.parse_args(pargs)
    return args, parser


if __name__ == '__main__':
    run()
