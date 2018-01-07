#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###############################################################################
# Copyright 2018 The AnPyLar Team. All Rights Reserved.
# Use of this source code is governed by an MIT-style license that
# can be found in the LICENSE file at http://anpylar.com/mit-license
###############################################################################
import logging
import os.path
import sys

from .utils import path_name_calc, makedir_error, makefile_error, read_license


# The templates below are used to generate the component depending of the
# options given to the argument parser

Template_Preamble = '''
#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###############################################################################
'''

Template_Component = '''from anpylar import Component, html


class {}(Component):
'''

Template_Selector = '''    selector = {}
'''

Template_Htmlpath = '''    htmlpath = {}
'''

Template_Stylepath = '''    stylepath = {}
'''

Template_Htmlsheet = """
    htmlsheet = '''
    '''
"""

Template_Stylesheet = """
    stylesheet = '''
    '''
"""

Template_Bindings = '''
    bindings = {
    }
'''

Template_Render = '''
    def render(self, node):
        {}
'''

Template_Pass = '''
    pass
'''

Template_Title = '''
    title = '{}'
'''

Template_Title_Html = '''<h1 {title}=title>{title}</h1>'''
Template_Title_Html_Selectista = '''<h1>{title}</h1>'''


class Componenter:
    preamble = False  # add she-bang and coding info
    licfile = ''
    name = ''
    title = False
    htmlsheet = False
    stylesheet = False
    selector = None
    htmlpath = True
    stylepath = True
    bindings = True
    render = True
    pythonista = False
    htmlista = False
    selectista = False
    comppath = None
    do_import = True

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)
            else:
                logging.error('Attribute %s unknown for componenter', k)
                sys.exit(1)

        self.contents = {}
        self.generated = False

    def write_out(self, outdir=None, makedir=True, parser=None):
        if not self.generated:
            self.generated = True
            self.generate()
        outdir = outdir or path_name_calc(self.name)
        if makedir:
            makedir_error(outdir, parser=parser)
        for path, content in self.contents.values():
            filename = os.path.join(outdir, path)
            makefile_error(filename, content, parser=parser)

        return outdir

    def generate(self):
        self.generated = True

        init = ''  # for __init__.py
        comp = ''  # for the component

        if self.preamble:  # whether to skip the shebang and coding info
            comp += Template_Preamble.lstrip()  # 1st line, ensure is 1st
            init += Template_Preamble.lstrip()  # 1st line, ensure is 1st

        # license text if given
        if self.licfile:
            lictxt = read_license(self.licfile)
            comp += lictxt
            init += lictxt

        # The definition of the component is a must
        compsuffix = 'Component' * (not self.name.endswith('Component'))
        self.compname = compname = self.name + compsuffix
        comp += Template_Component.format(compname)

        path_comps = path_name_calc(self.compname)

        # if the class has no content (all options drive to it) add a pass to
        # avoid a syntax error
        needpass = True

        if self.selector is not None:
            selector = self.selector or path_name_calc(compname, separator='-')
            comp += Template_Selector.format(selector)

        if self.pythonista:  # sets htmlpath to none, forcing no html file
            self.htmlpath = None

        # process htmlpath
        if self.htmlpath is not True and not self.htmlsheet:
            needpass = False
            hpath = self.htmlpath
            if isinstance(hpath, str):  # if string
                hpath = "'{}'".format(hpath)  # embed in quotes

            comp += Template_Htmlpath.format(hpath)

        # process stylepath
        if self.stylepath is not True and not self.stylesheet:
            needpass = False
            spath = self.stylepath
            # no clear value -> string
            if spath not in ['None', 'False', 'True']:
                spath = "'{}'".format(spath)

            comp += Template_Stylepath.format(spath)

        # Add/No-add template options
        if self.htmlsheet:
            needpass = False
            comp += Template_Htmlsheet

        if self.stylesheet:
            needpass = False
            comp += Template_Stylesheet

        if self.title:
            needpass = False
            comp += Template_Title.format(self.title)

        if self.bindings:
            needpass = False
            comp += Template_Bindings

        if self.render:
            needpass = False
            if not self.title:
                comp += Template_Render.format('pass')

            elif self.pythonista:
                comp += Template_Render.format(
                    'html.h1(\'{title}\')._fmt(title=self.title)')
            elif self.selectista:
                comp += Template_Render.format(
                    'node.select(\'h1\')._fmt(title=self.title)')
            else:  # self.htmlista or nothing specified
                comp += Template_Render.format('pass')

        if needpass:
            comp += Template_Pass

        # Component path: given name or (calculated_name + ext)
        path = self.comppath or (path_comps + '.py')
        # keep reference to mod name for import
        pypath, _ = os.path.splitext(path)

        self.contents['comp'] = (path, comp)

        init += 'from .{} import {}'.format(pypath, compname)
        if self.do_import:
            self.contents['init'] = ('__init__.py', init)

        # add htmlpath and stylepath files if needed
        to_generate = [(self.stylepath, '.css')]
        if not self.htmlsheet:
            to_generate += [(self.htmlpath, '.html')]

        for p, ext in to_generate:
            if p and p not in ['None', 'False']:
                if p in ['True'] or p is True:
                    # auto_name (add ext)
                    if self.comppath:
                        path = os.path.splitext(self.comppath)[0] + ext
                    else:
                        path = path_comps + ext
                else:
                    path = p  # explicit name given

                # path = os.path.join(outdir, path)
                content = ''
                if ext == '.html' and self.title:
                    if self.pythonista:
                        pass
                    elif self.selectista:
                        content = Template_Title_Html_Selectista
                    else:  # htmlista or nothing
                        content = Template_Title_Html

                self.contents[ext] = (path, content)
