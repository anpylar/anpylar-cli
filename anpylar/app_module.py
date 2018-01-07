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

# The templates below are used to generate the module depending of the
# options given to the argument parser

Template_Preamble = '''
#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###############################################################################
'''

Template_Main_Import = '''from anpylar import Module
'''

Template_Module = '''

class {}(Module):
'''

Template_Bindings = '''
    bindings = {}
'''

Template_Services = '''
    services = {}
'''

Template_Routes = '''
    routes = []
'''

Template_One_Component = '''
    components = {}
'''

Template_Components = '''
    components = [{}]
'''

Template_Init = '''
    def __init__(self):
        pass
'''

Template_Pass = '''
    pass
'''


class Moduler:
    name = ''
    preamble = False
    licfile = ''
    bootstrap = False
    components = True
    bindings = True
    services = True
    routes = True
    init = True
    modpath = None
    do_import = False
    submodule = False  # if not None ... (make dir and) write to that dir

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
        if not outdir:
            if self.submodule:  # specific check
                outdir = self.dir_name
            else:
                outdir = '.'

        if makedir:
            makedir_error(outdir, parser=parser)
        for path, content in self.contents.values():
            filename = os.path.join(outdir, path)
            makefile_error(filename, content, parser=parser)

        return outdir

    def generate(self):
        self.generated = True

        init = ''  # for __init__.py
        mod = ''  # for the component

        if self.preamble:  # whether to skip the shebang and coding info
            mod += Template_Preamble.lstrip()  # 1st line, ensure is 1st
            init += Template_Preamble.lstrip()  # 1st line, ensure is 1st

        lictxt = read_license(self.licfile)
        mod += lictxt
        init += lictxt

        mod += Template_Main_Import

        # if the class has no content (all options drive to it) add a pass to
        # avoid a syntax error
        needpass = True

        if self.bootstrap:
            for comp in self.bootstrap.split(','):
                comp = comp.strip()
                compmod = path_name_calc(comp)
                mod += '\nfrom .{} import {}'.format(compmod, comp)

            mod += '\n'  # separate from rest of code

        # The definition of the module is a must
        self.modname = modname = self.name + 'Module'
        mod += Template_Module.format(modname)

        if self.bootstrap:
            needpass = False
            comps = self.bootstrap.split(',')
            if len(comps) == 1:
                mod += Template_One_Component.format(self.bootstrap)
            else:
                mod += Template_Components.format(self.bootstrap)

        elif self.components:
            needpass = False
            mod += Template_Components.format('')

        if self.bindings:
            needpass = False
            mod += Template_Bindings

        if self.services:
            needpass = False
            mod += Template_Services

        if self.routes:
            needpass = False
            mod += Template_Routes

        if self.init:
            needpass = False
            mod += Template_Init

        if needpass:
            mod += Template_Pass

        self.path_name = path_name = path_name_calc(self.modname)
        self.dir_name = path_name_calc(self.name)
        # Module path: given name or (calculated_name + ext)

        path = self.modpath or (path_name + '.py')
        # keep reference to mod name for import
        pypath, _ = os.path.splitext(path)

        self.contents['mod'] = (path, mod)

        if self.do_import or self.submodule:
            # complete __init__, calc path and output
            init += 'from .{} import {}'.format(pypath, modname)
            self.contents['init'] = ('__init__.py', init)
