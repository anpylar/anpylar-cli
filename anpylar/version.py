#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###############################################################################
# Copyright 2018 The AnPyLar Team. All Rights Reserved.
# Use of this source code is governed by an MIT-style license that
# can be found in the LICENSE file at http://anpylar.com/mit-license
###############################################################################
import argparse
import os.path
import sys

from . import __version__


def run(pargs=None, name=None):
    args, parser = parse_args(pargs=pargs, name=name)
    print(__version__.__version__)


def parse_args(pargs=None, name=None):
    name = name or os.path.splitext(os.path.basename(sys.argv[0]))[0]

    parser = argparse.ArgumentParser(
        prog=name,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=('AnPyLar Version Printer')
    )

    args = parser.parse_args(pargs)
    return args, parser


if __name__ == '__main__':
    run()
