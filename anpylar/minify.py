#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###############################################################################
# Copyright 2018 The AnPyLar Team. All Rights Reserved.
# Use of this source code is governed by an MIT-style license that
# can be found in the LICENSE file at http://anpylar.com/mit-license
###############################################################################
import io
import keyword
import re
import token
import tokenize


def minify_py(src, preserve_lines=False, skipcomments=False):
    TKNIZE_NEWLINE_INDENT_None = [tokenize.NEWLINE, tokenize.INDENT, None]
    TKNIZE_INDENT_COMMENT = [tokenize.INDENT, tokenize.COMMENT]
    TKNIZE_NAME_NUMBER_OP = [tokenize.NAME, tokenize.NUMBER, tokenize.OP]
    TKNIZE_NAME_NUMBER = [tokenize.NAME, tokenize.NUMBER]

    # tokenize expects method readline of file in binary mode
    file_obj = io.BytesIO(src.encode('utf-8'))
    token_generator = tokenize.tokenize(file_obj.readline)

    out = ''  # minified source
    line = 0
    last_type = None
    indent = 0  # current indentation level
    brackets = []  # stack for brackets

    # first token is script encoding
    encoding = next(token_generator).string

    file_obj = io.BytesIO(src.encode(encoding))
    token_generator = tokenize.tokenize(file_obj.readline)

    for item in token_generator:

        # update brackets stack if necessary
        if token.tok_name[item.type] == 'OP':
            if item.string in '([{':
                brackets.append(item.string)
            elif item.string in '}])':
                brackets.pop()

        sline = item.start[0]  # start line
        if sline == 0:  # encoding
            continue

        # udpdate indentation level
        if item.type == tokenize.INDENT:
            indent += 1
        elif item.type == tokenize.DEDENT:
            indent -= 1
            continue

        if sline > line:  # first token in a line

            if not brackets and item.type == tokenize.STRING:
                if last_type in TKNIZE_NEWLINE_INDENT_None:
                    # If not inside a bracket, replace a string starting a
                    # line by the empty string.
                    # It will be removed if the next line has the same
                    # indentation.
                    out += ' '*indent+"''"
                    if preserve_lines:
                        out += '\n'*item.string.count('\n')
                    continue
            out += ' ' * indent  # start with current indentation
            if item.type not in TKNIZE_INDENT_COMMENT:
                out += item.string
            elif (item.type == tokenize.COMMENT and not skipcomments and
                  line <= 2 and item.line.startswith('#!')):
                # Ignore comments starting a line, except in one of the first
                # 2 lines, for interpreter path and/or encoding declaration
                out += item.string
        else:
            if item.type == tokenize.COMMENT:  # ignore comments in a line
                continue
            if not brackets and item.type == tokenize.STRING and \
               last_type in [tokenize.NEWLINE, tokenize.INDENT]:
                # If not inside a bracket, ignore string after newline or
                # indent
                out += "''"
                if preserve_lines:
                    out += '\n'*item.string.count('\n')
                continue
            if item.type in TKNIZE_NAME_NUMBER_OP and \
               last_type in TKNIZE_NAME_NUMBER:
                # insert a space when needed
                if item.type != tokenize.OP \
                   or item.string not in ',()[].=:{}+&' \
                   or (last_type == tokenize.NAME and
                       last_item.string in keyword.kwlist):
                    out += ' '
            elif (item.type == tokenize.STRING and
                  item.string[0] in 'rbu' and last_type in TKNIZE_NAME_NUMBER):
                # for cases like "return b'x'"
                out += ' '
            elif (item.type == tokenize.NAME and
                  last_item.type == tokenize.OP and last_item.string == '.'):
                # special case : from . import X
                out += ' '
            out += item.string

        line = item.end[0]
        last_item = item
        if item.type == tokenize.NL and last_type == tokenize.COMMENT:
            # NL after COMMENT is interpreted as NEWLINE
            last_type = tokenize.NEWLINE
        else:
            last_type = item.type

    # replace lines with only whitespace by empty lines
    out = re.sub('^\s+$', '', out, re.M)

    if not preserve_lines:
        # remove empty line at the start of the script (doc string)
        out = re.sub("^''\n", '', out)

        # remove consecutive empty lines
        out = re.sub('\n( *\n)+', '\n', out)

        # remove lines with an empty string followed by a line that starts with
        # the same indent
        def repl(mo):
            if mo.groups()[0] == mo.groups()[1]:
                return '\n'+mo.groups()[1]
            return mo.string[mo.start(): mo.end()]
        out = re.sub("\n( *)''\n( *)", repl, out)

    return out
