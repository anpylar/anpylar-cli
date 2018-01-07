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
from .packaging import Bundler
from .utils import print_error, makefile_error, readfile_error


def run(pargs=None, name=None):
    args, parser = parse_args(pargs=pargs, name=name)

    logconfig(args.quiet, args.verbose)  # configure logging

    bundler = Bundler()

    if args.debug:
        logging.info('Activating line info in brython')
        bundler.set_br_debug(True)

    if args.brython:
        logging.info('Adding specific brython.js')
        bundler.set_brython(args.brython)

    if args.brython_stdlib:
        logging.info('Adding specific brython_stdlib.js')
        bundler.set_brython_stdlib(args.brython_stdlib)

    if args.anpylar_js:
        logging.info('Adding specific anpylar_js.js')
        bundler.set_anpylar_js(args.anpylar_js)

    if args.anpylar_auto:
        logging.info('Adding specific anpylar.auto_vfs.js')
        bundler.set_anpylar_auto_vfs(args.anpylar_auto)
    elif args.anpylar_vfs:
        logging.info('Adding specific anpylar.vfs.js')
        bundler.set_anpylar_vfs(args.anpylar_vfs)

    if args.json:
        logging.info('Adding pure json pakets')
    for pjson in args.json:
        logging.debug('Adding pure json paket: %s', pjson)
        bundler.add_json(pjson)

    if args.vfs_js:
        logging.info('Adding vfs.js pakets')
    for vfs_js in args.vfs_js:
        logging.debug('Adding vfs.js paket: %s', vfs_js)
        bundler.add_vfs_js(vfs_js)

    if args.auto_vfs:
        logging.info('Adding auto_vfs.js pakets')
    for auto_vfs in args.auto_vfs:
        logging.debug('Adding auto_vfs.js paket: %s', auto_vfs)
        bundler.add_auto_vfs(auto_vfs)

    if args.pkg_dir:
        logging.info('Adding pakets directly from directories')
    for pkg_dir in args.pkg_dir:
        logging.debug('Adding dir paket: %s', pkg_dir)
        pdir = os.path.normpath(pkg_dir)
        bundler.add_pkg_dir(pdir)

    if not args.disable_anpylar_vfs:
        bundler.do_anpylar_vfs()  # make sure it is the bundle

    logging.info('Preparing bundle')
    bundler.prepare_bundle()

    if args.optimize:
        logging.info('Optimizing stdlib for the bundle')
        bundler.optimize_stdlib()

    logging.info('Writing bundle out to: %s', args.output)
    bundler.write_bundle(os.path.normpath(args.output))

    logging.info('Done')


def parse_args(pargs=None, name=None):
    if not name:
        name = os.path.splitext(os.path.basename(sys.argv[0]))[0]

    parser = argparse.ArgumentParser(
        prog=name,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=('AnPyLar Bundle (anpylar.js) Creator')
    )

    parser.add_argument('output', nargs='?', default=ANPYLAR_JS,
                        help='Name for the output bundled file')

    pgroup = parser.add_argument_group(title='Brython files')
    pgroup.add_argument('--brython', action='store', default=None,
                        help='Use specific brython.js for the bundle')

    pgroup.add_argument('--brython_stdlib', action='store', default=None,
                        help='Use specific brython_stdlib.js for the bundle')

    pgroup = parser.add_argument_group(title='Anpylar options')
    pgroup.add_argument('--anpylar-js', action='store', default=None,
                        help='Use specific anpylar_js for the bundle')

    pgroup.add_argument('--anpylar-vfs', action='store', default=None,
                        help='Use specific anpylar_vfs for the bundle')

    pgroup.add_argument('--anpylar-auto', action='store', default=None,
                        help='Use specific anpylar_auto_vfs for the bundle')

    pgroup.add_argument('--disable-anpylar-vfs', action='store_true',
                        help='Do not add anpylar.vfs.js')

    pgroup = parser.add_argument_group(title='Add Packages')
    pgroup.add_argument('--json', action='append', default=[],
                        help='Add a paketized package in pure json format')

    pgroup.add_argument('--vfs-js', action='append', default=[],
                        help='Add a paketized package in vfs.js format')

    pgroup.add_argument('--auto-vfs', action='append', default=[],
                        help='Add a paketized package in auto_vfs.js format')

    pgroup.add_argument('--pkg-dir', action='append', default=[],
                        help='Add a package directly from a directory')

    pgroup = parser.add_argument_group(title='Miscelanea')
    pgroup.add_argument('--debug', action='store_true',
                        help=('Keep line info for debugging purposes'))

    pgroup.add_argument('--optimize', action='store_true',
                        help=('Optimize the size of the anpylar.js '
                              'by packaging only the needed stdlib modules'))

    pgroup = parser.add_mutually_exclusive_group()
    pgroup.add_argument('--quiet', '-q', action='store_true',
                        help='Remove output (errors will be reported)')
    pgroup.add_argument('--verbose', '-v', action='store_true',
                        help='Increase verbosity level')

    args = parser.parse_args(pargs)
    return args, parser


if __name__ == '__main__':
    run()
