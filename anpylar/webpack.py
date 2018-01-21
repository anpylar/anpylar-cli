#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###############################################################################
# Copyright 2018 The AnPyLar Team. All Rights Reserved.
# Use of this source code is governed by an MIT-style license that
# can be found in the LICENSE file at http://anpylar.com/mit-license
###############################################################################
import argparse
import ast
import collections
import json
import logging
import os
import os.path
import shutil
import sys

from .logconfig import logconfig
from .packaging import Bundler
from .utils import readfile_error, makedir_error, makefile_error


_DISTPATH_ = '__webpack__'


# main code
def run(pargs=None, name=None):
    args, parser = parse_args(pargs=pargs, name=name)

    logconfig(args.quiet, args.verbose)  # configure logging

    target = os.path.normpath(args.target)
    if not os.path.exists(target):
        logging.error('Target does not exist: %s', target)
        sys.exit(1)

    bundler = Bundler(anpylarize=True)
    bundler.set_br_debug(True)  # default

    # Prepare anpylar.js output path
    APL_path = os.path.join(target, 'anpylar.js')
    logging.debug('anpylar.js path: %s', APL_path)

    # check if only anpylar has to be recreated
    if args.reset_anpylar:
        logging.info('Resetting anpylar.js to complete package')
        bundler.write_bundle(APL_path)
        sys.exit(0)

    if not args.no_package_json:  # package.json not disabled
        logging.info('Processing package.json')
        pjsonpath = os.path.join(target, 'package.json')
        pjsoncontent = readfile_error(pjsonpath, parser=parser)
        pjson = json.loads(pjsoncontent)
    else:
        logging.info('Ignoring package.json')
        pjson = {}  # have a safe default in place

    pjsonpkgs = pjson.get('packages', [])
    pjsonpkgdir = pjson.get('pkgdir', '')
    logging.debug('package.json packages: %s', str(pjsonpkgs))
    pjsondebug = pjson.get('debug', False)

    # Get other packages
    otherpkgs = args.packages

    # do a sanity check
    if otherpkgs:
        logging.info('Processing other packages: %s', str(otherpkgs))
    for otherpkg in otherpkgs:
        pkgtarget = os.path.join(target, otherpkg)
        if not os.path.exists(pkgtarget):
            logging.error('Specified package not found: %s', pkgtarget)
            sys.exit(1)

    # With the list of packages in the hand, update anpylar.js
    logging.debug('Adding packages from package.json to bundle')
    pkgsets = []
    pkgsets += [(pjsonpkgs, 'package.json')]
    pkgsets += [(otherpkgs, 'command line')]

    if pjsonpkgdir:  # preferred installation directory for packages
        pkgsets += [([pjsonpkgdir], 'package.json installation dir')]

    for pkgset, pkgsetname in pkgsets:
        logging.debug('Processing package set: %s', pkgsetname)
        for pkg in pkgset:
            pkgtarget = os.path.normpath(os.path.join(target, pkg))
            if not os.path.exists(pkgtarget):
                logging.error('Package from %s not found: %s (fullpath %s)',
                              pkgsetname, pkg, pkgtarget)

            if os.path.isdir(pkgtarget):
                pkginit = os.path.join(pkgtarget, '__init__.py')
                logging.debug('checking for __init__.py at: %s', pkginit)
                if os.path.exists(pkginit):
                    logging.debug('Adding package dir to bundle: %s:%s',
                                  pkg, pkgtarget)
                    bundler.add_pkg_dir(pkgtarget, extensions=args.extensions)
                else:
                    # no initfound ... copy all underlying files/directories
                    logging.debug('No __init__.py found for %s', pkgtarget)
                    logging.debug('Adding packages beneath it')
                    root, dnames, fnames = next(os.walk(pkgtarget))
                    logging.debug('Checking subdirectories')
                    for dname in dnames:
                        dtarget = os.path.join(root, dname)
                        logging.debug('Adding package dir to bundle: %s:%s',
                                      dname, dtarget)

                        bundler.add_pkg_dir(dtarget,
                                            extensions=args.extensions)

                    logging.debug('Checking subfiles for auto_vfs/vfs files')
                    for fname in fnames:
                        ftarget = os.path.join(root, fname)
                        if fname.endswith('.vfs.js'):
                            logging.debug('Adding vfs.js to bundle: %s:%s',
                                          fname, ftarget)

                            bundler.add_vfs_js(ftarget)
                        elif fname.endswith('.auto_vfs.js'):
                            logging.debug('Adding auto_vfs to bundle: %s:%s',
                                          fname, ftarget)
                            bundler.add_auto_vfs(pkgtarget)

            elif pkg.endswith('.vfs.js'):
                logging.debug('Adding vfs.js to bundle: %s:%s', pkg, pkgtarget)
                bundler.add_vfs_js(pkgtarget)
            elif pkg.endswith('.auto_vfs.js'):
                logging.debug('Adding auto_vfs.js to bundle: %s:%s',
                              pkg, pkgtarget)
                bundler.add_auto_vfs(pkgtarget)
            else:
                logging.error('Exiting. Unknown file type for bundle: %s', pkg)
                sys.exit(1)

    if args.only_anpylar and args.no_optimize:
        logging.info('Exiting after (only) updating anpylar (unoptimized)')
        bundler.write_bundle(APL_path)
        sys.exit(0)

    logging.debug('anpylar for __webpack__, set debug info')
    bundler.set_br_debug(pjsondebug)  # set to real value

    if not args.no_optimize:
        logging.info('Optimizing stdlib')
        bundler.optimize_stdlib()  # optimize stdlib

    logging.info('Updating anpylar.js')
    bundler.write_bundle(APL_path)  # write it out

    if args.only_anpylar:
        logging.info('Exiting after (only) updating anpylar')
        sys.exit(0)  # nothing else can be done

    logging.info('Preparing to put packages into the distribution')
    # All packages in place
    if args.dist:
        distpath = os.path.normpath(args.dist)
        logging.debug('args.dist provided: normalized to: %s', distpath)
    else:
        distpath = os.path.join(target, _DISTPATH_)
        logging.debug('args.dist not providec. Calculated: %s', distpath)

    if os.path.exists(distpath):
        logging.debug('Distribution path exists: %s', distpath)
        if args.no_overwrite:
            logging.error(('Distribution dir %s exists and no overwrite '
                           'was allowed'), distpath)
            sys.exit(1)

        else:  # overwrite allowed ... remove
            logging.debug('Overwrite of %s allowed', distpath)
            logging.info('Removing previous distribution path: %s', distpath)
            try:
                shutil.rmtree(distpath)
            except OSError as e:
                logging.error('Cannot remove dist dir %s: %s',
                              distpath, str(e))
                sys.exit(1)

    logging.info('Proceeding to copying data dirs')

    # List of packages read and distribution directory in place
    # Get only 1st delivery of os.walk ... list the target directory

    # See if package.json specifies additional things to copy
    # with base the original directory
    datafiles = pjson.get('data', None)

    allpkgs = otherpkgs + pjsonpkgs
    if datafiles is None:
        logging.info('No datafiles defined. Copying standard files/dir')
        # Easy policy: copy files/directories which are not packages

        logging.debug('not to copy: %s', str(allpkgs))
        # add normpath to remove a trailing slash
        root, dnames, fnames = next(os.walk(target))

        # shutil.copytree will fail if the destination directory exists
        # Create it only if no copydirs do exit (copying files needs it)
        copydirs = set(dnames) - set(allpkgs)
        logging.debug('Directory names: %s', str(dnames))
        logging.debug('Directories to copy: %s', ','.join(copydirs))

        # find out which dirs would have to be copied verbatim
        for copydir in copydirs:
            logging.debug('Copying directory: %s', copydir)
            srcdir = os.path.join(root, copydir)
            dstdir = os.path.join(distpath, copydir)
            shutil.copytree(copydir, dstdir)

    elif isinstance(datafiles, list):
        # copy only those specified

        logging.debug('Copying data directories from package.json')
        for datafile in datafiles:
            srcdir = os.path.join(target, datafile)
            logging.debug('checking datafile: %s: %s', datafile, srcdir)
            if os.path.isdir(srcdir):
                logging.debug('Is dir datafile: %s', srcdir)
                dstdir = os.path.join(distpath, datafile)
                shutil.copytree(srcdir, dstdir)
            else:
                logging.debug('No dir datafile: %s', srcdir)

    # shutil.copytree fails to work if distpath exists because it tries to
    # create it. But if no dir was copied, the path won't exist yet
    if not os.path.exists(distpath):
        logging.debug('Distpath not yet created. Creating: %s', distpath)
        makedir_error(distpath, parser=parser)

    if datafiles is None:
        # Copy individual files and other directories
        root, dnames, fnames = next(os.walk(target))
        logging.info('Copying individual files')
        for fname in fnames:
            if fname in allpkgs:
                logging.debug('Skipping. File was in packages: %s', fname)
                continue  # skip what has already been copied
            logging.debug('Copying file: %s', fname)
            srcfile = os.path.join(root, fname)
            shutil.copy(srcfile, distpath)

    elif isinstance(datafiles, list):
        # copy only those specified
        logging.debug('Copying data files from package.json')
        for datafile in datafiles:
            srcfile = os.path.join(target, datafile)
            logging.debug('Copying datafile: %s', srcfile)
            if os.path.isfile(srcfile):
                dstfile = os.path.join(distpath, datafile)
                shutil.copyfile(srcfile, dstfile)
            else:
                logging.debug('No file with that name found: %s', srcfile)

    logging.info('Done')


def parse_args(pargs=None, name=None):
    if not name:
        name = os.path.splitext(os.path.basename(sys.argv[0]))[0]

    parser = argparse.ArgumentParser(
        prog=name,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=('AnPyLar Web Application Packager')
    )

    parser.add_argument('target', nargs='?', default='.',
                        help='Application directory to package')

    parser.add_argument('--package', action='append', default=[],
                        dest='packages',
                        help=('Add package from directory or vfs.js or '
                              'auto_vfs.js from directory to anpylar.js '
                              'even if not present in package.json. '
                              'Can be specified multiple times'))

    parser.add_argument('--no-package-json', action='store_true',
                        help='Ignore packages listed in packages.json')

    parser.add_argument('--dist', action='store', default='',
                        help='Specify destination directory for the webpack')

    parser.add_argument('--no-overwrite', action='store_true',
                        help='Do not overwrite existing dist directory')

    parser.add_argument('--extensions', default='.py,.js,.css,.html',
                        help=('Comma separated list of extensions to pack '
                              'when packaging directories'))

    pgroup = parser.add_mutually_exclusive_group()
    pgroup.add_argument('--reset-anpylar', action='store_true',
                        help=('Reset anpylar.js to default content ignoring '
                              'application packages. No packaging'))

    pgroup.add_argument('--only-anpylar', action='store_true',
                        help=('Update only anpylar.js with packages code. '
                              'No packaging'))

    parser.add_argument('--no-optimize', action='store_true',
                        help=('Do not optimize the size of the anpylar.js '
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
