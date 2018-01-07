#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###############################################################################
# Copyright 2018 The AnPyLar Team. All Rights Reserved.
# Use of this source code is governed by an MIT-style license that
# can be found in the LICENSE file at http://anpylar.com/mit-license
###############################################################################
import ast
import collections
import json
import os
import os.path
import re
import textwrap


from .minify import minify_py
from .utils import print_error, makefile_error, readfile_error


ANPYLAR_JS = 'anpylar.js'


# Define packaging extension globally
VFS_JS_EXT = '.vfs.js'
VFS_JSON_EXT = '.vfs.json'
AUTO_VFS_JS_EXT = '.auto_vfs.js'


# Tempalte for regenerating Brython Lib
Template_StdLib_Begin = '''
__BRYTHON__.use_VFS = true;
__BRYTHON__.VFS =
'''.strip()


######################################################################
# Bundler
######################################################################
class Bundler:
    datadir = os.path.join(os.path.dirname(__file__), 'data')

    # May be added later
    PATH_ANPYLAR_VFS_JS = os.path.join(datadir, 'anpylar.vfs.js')
    PATH_ANPYLAR_AUTO_VFS_JS = os.path.join(datadir, 'anpylar.auto_vfs.js')
    PATH_ANPYLAR_D_AUTO_VFS_JS = os.path.join(datadir, 'anpylar_d.auto_vfs.js')

    # Keys for the PATHs dictionary
    BR_JS = 'br_js'
    BRSTD_JS = 'brstd_js'
    PACKAGES = 'packages'
    ANPYLAR_VFS_JS = 'anpylar_vfs_js'
    ANPYLARJS_JS = 'anpylarjs_js'

    # Default paths
    PATHS = collections.OrderedDict()
    PATHS[BR_JS] = os.path.join(datadir, 'brython.js')
    PATHS[BRSTD_JS] = os.path.join(datadir, 'brython_stdlib.js')
    PATHS[ANPYLAR_VFS_JS] = False
    PATHS[PACKAGES] = None
    PATHS[ANPYLARJS_JS] = os.path.join(datadir, 'anpylar_js.js')

    def __init__(self, anpylarize=False):
        self.prepared = False
        self.br_debug = True
        self.minify = not self.br_debug  # do not minify if debugging
        self.auto_anpylar = True
        self.anpylarize = anpylarize

        # hold basic comps of 'anpylar.js'
        self.comps = comps = collections.OrderedDict()
        self.paths = self.PATHS.copy()
        for k, v in self.paths.items():
            if v is None:
                comps[k] = self.pkgs = []
            elif v:
                comps[k] = None

        self.pakets = []  # corresponding paket for import analysis

    def set_br_debug(self, onoff=True):
        self.br_debug = onoff
        self.minify = not onoff  # do not minify if debugging

    def do_anpylar_vfs(self):
        path = self.paths[self.ANPYLAR_VFS_JS]
        if not self.auto_anpylar:
            self.add_vfs_js(path)  # path has for sure been set by user
        else:
            if not path:  # was not set by user, use internal defs
                if self.br_debug:
                    path = self.PATH_ANPYLAR_D_AUTO_VFS_JS
                else:
                    path = self.PATH_ANPYLAR_AUTO_VFS_JS

            self.add_auto_vfs(path)

        # Place anpylar before any other package
        self.pkgs.insert(0, self.pkgs.pop())
        self.pakets.insert(0, self.pakets.pop())

    def set_anpylar_vfs(self, path, auto=False):
        self.paths[self.ANPYLAR_VFS_JS] = path
        self.auto_anpylar = auto

    def set_anpylar_auto_vfs(self, path):
        self.set_anpylar_vfs(path, auto=True)

    def set_brython(self, path):
        self.paths[self.BR_JS] = path

    def set_brython_stdlib(self, path):
        self.paths[self.BRSTD_JS] = path

    def set_anpylar_js(self, path):
        self.paths[self.ANPYLARJS_JS] = path

    def add_json(self, path):
        vfs = readfile_error(path)
        paket = Paketizer_Json(vfs)
        self.pakets.append(paket)
        self.pkgs.append(paket.get_autoload())

    def add_vfs_js(self, path):
        vfs = readfile_error(path)
        paket = Paketizer_Json(vfs, braces=1)
        self.pakets.append(paket)
        self.pkgs.append(paket.get_autoload())

    def add_auto_vfs(self, path):
        vfs = readfile_error(path)
        paket = Paketizer_Json(vfs, braces=2)
        self.pakets.append(paket)
        # self.pkgs.append(paket.get_autoload())
        self.pkgs.append(vfs)  # already in proper format

    def add_pkg_dir(self, path, **kwargs):
        paket = Paketizer(path, minify=self.minify, **kwargs)
        self.pkgs.append(paket.get_autoload())

    def prepare_bundle(self):
        if self.anpylarize:
            self.do_anpylar_vfs()

        for name, path in self.paths.items():
            if not path:
                continue
            elif name == self.ANPYLAR_VFS_JS:
                continue  # skip in case it's added (it's in packages)

            self.comps[name] = comp = readfile_error(path)

            if name == self.ANPYLARJS_JS:
                bpattern = r'brython\(.*\)'
                brepl = 'brython({})'.format('1' * self.br_debug)
                self.comps[name] = re.sub(bpattern, brepl, comp, count=1)

        self.prepared = True

    def write_bundle(self, path, prepare=True):
        if prepare and not self.prepared:
            self.prepare_bundle()

        out = []
        for val in self.comps.values():
            out += val if isinstance(val, (list,)) else [val]

        makefile_error(path, out, itercontent=True)

    def get_imports(self, tolist=True):
        pkgbases = [paket.base for paket in self.pakets]

        imps = set()
        for paket in self.pakets:
            imps = imps | set(paket.scan_imports(ignores=pkgbases))

        if tolist:
            return list(imps)

        return imps

    def optimize_stdlib(self):
        if not self.prepared:
            self.prepare_bundle()

        pkg = self.comps[self.BRSTD_JS]
        paket = Paketizer_Json(pkg)
        stdlib = paket.modules

        imps = self.get_imports()
        stdlib_entries = set()
        for imp in imps:
            self.find_stdlib_imports(stdlib, imp, stdlib_entries)

        # With the given imports ... re-generate stdlib
        stdlib = {k: v for k, v in stdlib.items() if k in stdlib_entries}
        paket.modules = stdlib

        # replace only json content
        self.comps[self.BRSTD_JS] = pkg[:pkg.find('{')] + paket.get_raw()

    def find_stdlib_imports(self, bstdlib, name, storage_set):
        try:
            entry = bstdlib[name]
        except KeyError:
            return

        storage_set.add(name)  # present in stdlib, add it

        ext, src = entry[0:2]
        if ext != '.py':
            return  # cannot parse, end of chain

        is_package = len(entry) > 2

        fname = name.replace('.', os.sep)
        if is_package:
            fname += os.sep + '__init__'
        fname += ext

        pkgsplit = name.split('.')
        pkg = name if len(pkgsplit) == 1 else '.'.join(pkgsplit[:-1])
        impfinder = ImportFinder()
        impfinder.set_package(pkg)

        tree = ast.parse(src, filename=fname)
        impfinder.visit(tree)

        for imp in impfinder.iter_imports():
            if imp not in storage_set:  # avoid inf recursio by not re-visiting
                self.find_stdlib_imports(bstdlib, imp, storage_set)

######################################################################
# Paketizter
######################################################################
Template_Wrapper_Header = '''
;(function() {
'''

Template_Wrapper_Footer = '''
    if(window.__ANPYLAR__ === undefined)
        window.__ANPYLAR__ = {autoload: []}  // ensure global scope

    window.__ANPYLAR__.autoload.push(function($B) {
        // brython removes 1st 2 entries later if stdlib import is true
        // our entry would be removed if placed 1st
        $B.path.splice(2, 0, vfspath)
        $B.imported['_importlib'].VFSAutoPathFinder(vfspath, $vfs)  // autoload
    })
})()
'''


class Paketizer:
    def __init__(self, d, extensions=['.py'], minify=True, skipcomments=True,
                 parser=None):
        self.modules = modules = {}  # keep track of the loaded modules

        # The root package name is the last directory in the path provided
        self.base = base = os.path.basename(d.rstrip(os.sep))

        for root, dnames, fnames in os.walk(d):
            # must have __init__
            drel = os.path.relpath(root, d)
            if drel == '.':  # start dir
                # Use the package name
                packagename = drel.replace('.', base, 1)
            else:
                # replace OS (back)slashes with python dots
                drel = drel.replace(os.sep, '.')
                # add it to the base package
                packagename = '{}.{}'.format(base, drel)

            for fname in fnames:
                name, ext = os.path.splitext(fname)
                ext = ext.lower()

                if ext not in extensions:
                    continue

                if fname == '__init__.py':  # special case, needs extra marker
                    modname = packagename
                    modext = [1]  # marker in vfs.js for package entry point

                elif ext in ['.js', '.py']:  # regular case, add as module
                    # import path as in anpylar.promise
                    modname = '.'.join((packagename, name))
                    modext = []

                else:  # special case, assets
                    # These are assets and not python packages/subpackages
                    # Replace the . with / to make them searchable using
                    # regular path syntax later
                    modname = '/'.join((packagename.replace('.', '/'), fname))
                    modext = []

                # Reunite the path and normalize it for sanity
                fpath = os.path.join(root, fname)
                # read and add to modules
                content = readfile_error(fpath, parser=parser)

                if minify and ext == '.py':
                    content = minify_py(content, skipcomments=skipcomments)

                modules[modname] = [ext, content] + modext

    @staticmethod
    def gen_autoload(vfs, vfspath, indent=None, is_json=False):
        prefix = '    '

        vfs_json = json.dumps(vfs, indent=indent) if not is_json else vfs
        vfs_js = 'var ' + ' = '.join(('$vfs', vfs_json))
        return ''.join((
            Template_Wrapper_Header,
            '{}var vfspath = "{}"\n'.format(prefix, vfspath),
            textwrap.indent(vfs_js, prefix=prefix),
            '\n',
            Template_Wrapper_Footer,
            ))

    def write_autoload(self, path, **kwargs):
        makefile_error(path, self.get_autoload(**kwargs))

    def get_autoload(self, vfspath=None, indent=None):
        if vfspath is None:
            vfspath = self.base + '.vfs.js'
        return self.gen_autoload(self.modules, vfspath, indent=indent)

    @staticmethod
    def gen_variable(vfs, vfsname, indent=None, is_json=False):
        vfs_json = json.dumps(vfs, indent=indent) if not is_json else vfs
        return 'var ' + ' = '.join((vfsname, vfs_json))

    def write_vfs_js(self, path, vfsname='$vfs', **kwargs):
        makefile_error(path, self.get_variable(vfsname=vfsname, **kwargs))

    def get_variable(self, vfsname, indent=None):
        return self.gen_variable(self.modules, vfsname, indent=indent)

    @staticmethod
    def gen_raw(vfs, indent=None, is_json=False):
        return json.dumps(vfs, indent=indent) if not is_json else vfs

    def get_raw(self, indent=None):
        return self.gen_raw(self.modules, indent=indent)

    @staticmethod
    def scan_imports_vfs(vfs, relative=False, ignores=[]):
        impfinder = ImportFinder()
        for modname, modentry in vfs.items():
            ext, src = modentry[0:2]  # ignore potential "is_package" market
            if ext != '.py':
                continue

            tree = ast.parse(src)
            if relative:
                impfinder.set_package(modname)

            impfinder.visit(tree)

        # filter own imports
        imps = impfinder.get_set_imports()  # get set for quicker processing
        for ignore in ignores:
            imps = {x for x in imps if not x.startswith(ignore)}

        return list(imps)  # list is usually expected result rather than set

    def scan_imports(self, relative=False, ignoreself=True, ignores=[]):
        newignores = ignores + [self.base] * ignoreself

        return self.scan_imports_vfs(self.modules, relative=relative,
                                     ignores=newignores)


class Paketizer_Json(Paketizer):
    def __init__(self, content, braces=1):
        idx = -1
        for i in range(braces):
            idx = content.find('{', idx + 1)

        self.modules, _ = json.JSONDecoder().raw_decode(content[idx:])
        self.base = sorted(self.modules.keys())[0]


######################################################################
# ImportFinder
######################################################################
class ImportFinder(ast.NodeVisitor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._imps = set()
        self._relimport = True
        self._package = None

    def visit_Import(self, node):
        # node.names is made up os "alias" instances (name, asname)
        for alias in node.names:  # import foo.bar.foo
            self.add_import(alias.name.split('.'))

        self.generic_visit(node)  # visit children

    def visit_ImportFrom(self, node):
        # node.names is made up os "alias" instances (name, asname)
        # + module(string or None) and level(>= 0)
        for alias in node.names:
            if not self._package and node.level:
                continue  # no package set -> skip any relative import

            psplit = []  # keep the splitted package parts
            if node.level == 1:  # curpkg: from .xx import or from . import
                psplit += self._psplit[:]  # rel import, get cur pkg
            elif node.level:  # > 1  from ..x import or from .. import
                psplit = self._psplit[:-node.level + 1]  # go up the chain

            # level 0 is absolute and has "module". Implicitly managed here
            if node.module is not None:  # from xx / from .xx / from ..xx
                psplit += node.module.split('.')  # from aa.bb import

            if alias.name != '*':
                psplit += alias.name.split('.')

            self.add_import(psplit)

        self.generic_visit(node)

    def set_package(self, package):
        self._package = package  # for relative imports
        self._psplit = package.split('.')

    def add_import(self, isplit):
        for i in range(len(isplit)):
            self._imps.add('.'.join(isplit[0:i + 1]))

    def get_set_imports(self):
        return self._imps

    def get_imports(self):
        return list(self._imps)

    def iter_imports(self):
        return iter(self._imps)
