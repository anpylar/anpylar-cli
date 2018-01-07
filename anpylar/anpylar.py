#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###############################################################################
# Copyright 2018 The AnPyLar Team. All Rights Reserved.
# Use of this source code is governed by an MIT-style license that
# can be found in the LICENSE file at http://anpylar.com/mit-license
###############################################################################

# Argparse multi-level commands pattern
# chase-seibert.github.io/blog/2014/03/21/python-multilevel-argparse.html

import argparse
import sys

from . import application
from . import bundle
from . import component
from . import module
from . import paketize
from . import pip
from . import serve
from . import syntaxcheck
from . import version
from . import webpack


_debug = False


def debugout(*args, **kwargs):
    if _debug:
        print(*args, **kwargs)


_NAME = 'anpylar'

USAGE = '''anpylar <command> [<args>]

The available commands are:
'''


class AnPyLar(object):

    commands = (
        ('application', 'Generate application skeleton'),
        ('bundle', 'Create an AnPyLar  bundle'),
        ('component', 'Generate component code'),
        ('paketize', 'Paketize an application'),
        ('module', 'Generate module code'),
        ('webpack', 'Pack the application for web deployment'),
        ('pip', 'Install packages with pip into an app'),
        ('serve', 'Serve an application'),
        ('syntaxcheck', 'Check files/directories for syntax errors'),
        ('version', 'Display version information'),
    )

    def __init__(self, pargs=None):
        usage = USAGE[:]  # copy of global value

        self.cmdnames = []
        self.modules = {}
        for cmd, description in self.commands:
            if isinstance(cmd, (list, tuple)):
                cmd, mod = cmd  # unpack potential different module
            else:
                mod = cmd

            self.cmdnames.append(cmd)
            self.modules[cmd] = mod

            usage += '\n    ' + cmd
            usage += ' ' * (16 - len(cmd))
            usage += description

        parser = argparse.ArgumentParser(
            description='AnPyLar command line manager',
            usage=usage,
        )

        parser.add_argument('command', help='Subcommand to run')
        # parse_args defaults to [1:] for args, but you need to
        # exclude the rest of the args too, or validation will fail
        args = parser.parse_args(pargs or sys.argv[1:2])

        cmds = [x for x in self.cmdnames if x.startswith(args.command)]
        if len(cmds) > 1:
            print('Requested action matches multiple targets: ', end='')
            print(' and '.join(cmds))
            print()
            parser.print_help()
            sys.exit(1)

        command = cmds[0]
        try:
            mod = sys.modules[__package__ + '.' + self.modules[command]]
        except KeyError as e:
            debugout(e)
            parser.print_help()
            sys.exit(1)

        mod.run(sys.argv[2:], name=_NAME + '-' + command)


def run():
    AnPyLar()


if __name__ == '__main__':
    run()
