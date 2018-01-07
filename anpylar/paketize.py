#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###############################################################################
# Copyright 2018 The AnPyLar Team. All Rights Reserved.
# Use of this source code is governed by an MIT-style license that
# can be found in the LICENSE file at http://anpylar.com/mit-license
###############################################################################
import argparse
import logging
import os.path
import sys

from .logconfig import logconfig
from .packaging import Paketizer, VFS_JSON_EXT, VFS_JS_EXT, AUTO_VFS_JS_EXT
from .utils import makefile_error


def run(pargs=None, name=None):
    args, parser = parse_args(pargs=pargs, name=name)

    logconfig(args.quiet, args.verbose)  # configure logging

    dnorm = os.path.normpath(args.dir)
    if not os.path.isdir(dnorm):
        logging.error('%s is not a valid directory', dnorm)
        sys.exit(1)

    extensions = [x.strip().lower() for x in args.extensions.split(',')]

    if args.add_extension:
        for ext in args.add_extensions:
            extensions.append(ext.strip().lower())

    logging.debug('Paketizing extensions %s', str(extensions))

    logging.info('Paketizing %s', dnorm)
    paket = Paketizer(dnorm, extensions=extensions,
                      minify=not args.no_minify,
                      skipcomments=not args.no_headers,
                      parser=parser)

    logging.debug('Paket processed')

    if args.outfile:
        fout = args.outfile
        logging.debug('Outfile provided: %s', args.outfile)
    else:
        logging.debug('No Outfile, using paket.base %s', paket.base)
        fout = paket.base
        if args.json_raw:
            fout += VFS_JSON_EXT
        elif args.vfs_js:
            fout += VFS_JS_EXT
        else:
            fout += AUTO_VFS_JS_EXT

        logging.debug('No Outfile, calculated name %s', fout)

    if args.json_raw:
        logging.debug('Writing paket in raw JSON output')
        content = paket.get_raw(indent=args.indent)
        makefile_error(fout, content, parser=parser)
    elif args.vfs_js:
        logging.debug('Writing paket in vfs.js format with var_name: %s',
                      args.var_name)
        content = paket.get_variable(args.var_name, indent=args.indent)
        makefile_error(fout, content, parser=parser)
    else:  # auto-vfs option (default)
        logging.debug('Writing paket in auto_vfs.js format')
        vfspath = os.path.basename(fout)
        if not vfspath.endswith(VFS_JS_EXT):
            # The existing convention 'vfs.js' can be reused as extension
            if vfspath.endswith(AUTO_VFS_JS_EXT):
                vfspath = '.'.join(vfspath.split('.')[:-2])

            vfspath = vfspath + VFS_JS_EXT

        content = paket.get_autoload(vfspath, indent=args.indent)
        makefile_error(fout, content, parser=parser)

    logging.info('Wrote paket to %s', fout)
    logging.info('Done')


def parse_args(pargs=None, name=None):
    if not name:
        name = os.path.splitext(os.path.basename(sys.argv[0]))[0]

    parser = argparse.ArgumentParser(
        prog=name,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=('AnPyLar Paketizer')
    )

    parser.add_argument('dir', help='Directory to paketize')
    parser.add_argument('outfile', nargs='?', default='',
                        help=('Default filename for the output. If not '
                              'specified, the name of the base directory '
                              'will be used and the extension will be '
                              'automatically chosen'))

    pgroup = parser.add_argument_group(title='Javascript/JSON Options')
    pgroup.add_argument('--var-name', required=False, action='store',
                        default='$vfs',
                        help=('If not autoloading, name for the vfs object '
                              'containing the app'))

    pgroup.add_argument('--indent', required=False, default=None, type=int,
                        help='Beautify output by indenting x spaces(int)')

    pgroup = parser.add_argument_group(title='Extensions to consider')
    pgroup.add_argument('--extensions', required=False, action='store',
                        default='.py,.js,.html,.css',
                        help=('Comma separated list of extensions to consider '
                              'for paketization'))

    pgroup.add_argument('--add-extension', required=False, action='append',
                        help=('Add a extension to be considered to those from '
                              '--extensions. This command can be repeated '
                              'multiple times'))

    pgroup = parser.add_mutually_exclusive_group()
    pgroup.add_argument('--auto-vfs', required=False, action='store_true',
                        help='Wrap vfs_js in auto-loading code (default)')

    pgroup.add_argument('--vfs-js', required=False, action='store_true',
                        help='Regular vfs.js format')

    pgroup.add_argument('--json-raw', required=False, action='store_true',
                        help='Output only json content')

    pgroup = parser.add_argument_group(title='Python minification options')
    pgroup.add_argument('--no-minify', required=False, action='store_true',
                        help='Do not minify the source code')

    pgroup.add_argument('--no-headers', required=False, action='store_true',
                        help=('do not remove first 2 lines of comments in'
                              'python files'))

    pgroup = parser.add_mutually_exclusive_group()
    pgroup.add_argument('--quiet', '-q', action='store_true',
                        help='Remove output (errors will be reported)')
    pgroup.add_argument('--verbose', '-v', action='store_true',
                        help='Increase verbosity level')

    args = parser.parse_args(pargs)
    return args, parser


if __name__ == '__main__':
    run()
