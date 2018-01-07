#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###############################################################################
# Copyright 2018 The AnPyLar Team. All Rights Reserved.
# Use of this source code is governed by an MIT-style license that
# can be found in the LICENSE file at http://anpylar.com/mit-license
###############################################################################
import errno
import os
import sys


# prints the error and the parser help and bails out
def print_error(error, parser=None):
    print('-' * 50)
    print(error)
    print('-' * 50)
    print()
    if parser:
        try:
            parser.print_help()
        except:
            pass  # avoid new errors

    sys.exit(1)


# calculates the name of the item's names by lowercasing and inserting an _
# as a transition between lowercase -> uppercase in the original
# PyroDetail -> pyro_detail
def path_name_calc(name, separator='_'):
    tokens = []
    lastlower = False
    for x in name:
        if x.isupper():
            if lastlower:
                tokens.append(separator)
            tokens.append(x.lower())
            lastlower = False
        else:
            tokens.append(x)
            lastlower = x.islower()

    return ''.join(tokens)


def makedir_error(dirname, parser=None):
    if dirname in ['.', '..']:
        return

    try:
        os.makedirs(dirname)  # try to make the dir
    except OSError as e:
        if e.errno != errno.EEXIST:  # strange error
            print_error(e, parser)
        else:
            e = 'Directory already exists.'
            print_error(e, parser)


def makefile_error(filename, content, parser=None,
                   encoding='utf-8', newline='\n',
                   end='\n', itercontent=False, mode='w'):

    if 'b' in mode:
        encoding = None
    try:
        if hasattr(filename, 'write'):
            f = filename
        elif filename == '-':
            f = sys.stdout
        else:
            try:
                f = open(filename, mode, newline=newline, encoding=encoding)
            except EnvironmentError as e:  # some file error
                print_error(e, parser)

        if not itercontent:
            f.write(content)
        else:
            for x in content:
                f.write(x)
                if end:
                    f.write(end)

    except EnvironmentError as e:  # some file error
        print_error(e, parser)


def readfile_error(filename, parser=None, encoding='utf-8',
                   newline=None, mode='r'):

    if 'b' in mode:
        encoding = None

    try:
        with open(filename, mode, newline=newline, encoding=encoding) as f:
            return f.read()
    except EnvironmentError as e:  # some file error
        print_error(e, parser)


def read_license(filename, parser=None):
    output = ''
    if filename:
        try:
            with open(filename) as f:
                for l in f:
                    if l[0] != '#':  # comment it out if needed
                        output += '# '

                    output += l

            output += '#' * 79 + '\n'  # PEP-8 compliant, as separator to code

        except EnvironmentError as e:
            # parent of IOError/OSError/WindowsError where
            print_error(e, parser)

    return output


def win_wait_for_parent(raise_exceptions=False):
    if not sys.platform == 'win32':
        return True

    # When started under cygwin, the parent process will die leaving a child
    # hanging around. The process has to be waited upon
    import ctypes
    from ctypes.wintypes import DWORD, BOOL, HANDLE
    import threading

    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

    # Get a handle for the right purpose (wait on it aka "synchronization")
    SYNCHRONIZE = 0x00100000
    phandle = kernel32.OpenProcess(SYNCHRONIZE, 0, os.getppid())

    def check_parent():
        # Wait for parent signal (death) and exit
        kernel32.WaitForSingleObject(phandle, -1)  # -1 -> INFINITE
        os._exit(0)

    if not phandle:  # if not possible
        if raise_exceptions:  # either raise if wished
            raise ctypes.WinError(ctypes.get_last_error())

        return False  # or let the caller know

    # kickstart parent check in the background thread
    threading.Thread(target=check_parent).start()
    return True
