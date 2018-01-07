#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###############################################################################
# Copyright 2018 The AnPyLar Team. All Rights Reserved.
# Use of this source code is governed by an MIT-style license that
# can be found in the LICENSE file at http://anpylar.com/mit-license
###############################################################################
import argparse
import ast
import io
import logging
import os.path
import sys
import traceback

from .logconfig import logconfig
from .utils import readfile_error


def syntax_check(filename, encoding='utf-8'):
    _, ext = os.path.splitext(filename)
    if ext != '.py':
        return True

    logging.debug('Syntax Checking: %s', filename)

    src = readfile_error(filename, encoding=encoding)
    try:
        ast.parse(src, filename=filename)
    except SyntaxError:
        f = io.StringIO()  # filter part of the output
        traceback.print_exc(file=f)
        f.seek(0)
        # skip 5 lines - our own traceback calling ast
        # critical to make sure it shows up
        logging.error(''.join(f.readlines()[5:]))
        return False

    return True


def check_single_file(filename, encoding='utf-8', stop=False):
    ret = syntax_check(filename, encoding=encoding)
    if not ret and stop:
        sys.exit(0)

    return ret


def run(pargs=None, name=None):
    args, parser = parse_args(pargs=pargs, name=name)

    logconfig(args.quiet, args.verbose)  # configure logging

    for element in args.files_dirs:
        element = os.path.normpath(element)
        logging.debug('Processing: %s', element)
        if not os.path.exists(element):
            logging.debug('%s is neither file nor directory. Skipping',
                          element)

        if os.path.isfile(element):
            logging.debug('%s is a file.', element)
            check_single_file(element, stop=not args.no_stop)

        elif os.path.isdir(element):
            logging.debug('%s is a directory. Walking down!', element)
            for root, dnames, fnames in os.walk(element):
                try:
                    dnames.remove('__pycache__')  # skip well-known target
                except ValueError as e:  # not present
                    pass

                for fname in fnames:
                    logging.debug('Checking file: %s', fname)
                    filename = os.path.join(root, fname)
                    check_single_file(filename, stop=not args.no_stop)


def parse_args(pargs=None, name=None):
    if not name:
        name = os.path.splitext(os.path.basename(sys.argv[0]))[0]

    parser = argparse.ArgumentParser(
        prog=name,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=('AnPyLar Syntax Checker')
    )

    parser.add_argument('files_dirs', nargs='+',
                        help='Files or Directories to check')

    parser.add_argument('--no-stop', action='store_true',
                        help='Process all targets regardless of errors')

    pgroup = parser.add_mutually_exclusive_group()
    pgroup.add_argument('--quiet', '-q', action='store_true',
                        help='Remove output (errors will be reported)')
    pgroup.add_argument('--verbose', '-v', action='store_true',
                        help='Increase verbosity level')

    args = parser.parse_args(pargs)
    return args, parser


if __name__ == '__main__':
    run()
