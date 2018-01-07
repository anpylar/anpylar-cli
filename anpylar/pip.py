#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###############################################################################
# Copyright 2018 The AnPyLar Team. All Rights Reserved.
# Use of this source code is governed by an MIT-style license that
# can be found in the LICENSE file at http://anpylar.com/mit-license
###############################################################################
import argparse
import json
import logging
import os.path
import posixpath
import shutil
import subprocess
import sys
import tempfile

from .logconfig import logconfig
from .utils import makefile_error, readfile_error


def run(pargs=None, name=None):
    args, parser = parse_args(pargs=pargs, name=name)

    logconfig(args.quiet, args.verbose)  # configure logging

    target = os.path.normpath(args.target)
    logging.info('Target for pip installation is: %s', target)

    if args.no_package_json:
        pjson = {}
    else:
        pjsonpath = os.path.join(target, 'package.json')
        if not os.path.exists(pjsonpath):
            logging.info('No package.json found. Creating a basic one')

            pjson = {
                'packages': [],  # only package during creation
            }

            jsontxt = json.dumps(pjson, indent=4)  # indent for beauty
            makefile_error(pjsonpath, jsontxt, parser=parser)

        else:
            logging.info('Processing package.json')
            pjsontxt = readfile_error(pjsonpath, parser=parser)
            logging.debug('Loading json content')
            try:
                pjson = json.loads(pjsontxt)
            except json.JSONDecodeError as e:
                errmsg = 'Exiting Failed to load json from: %s\n%s'
                logging.error(errmsg, pjsonpath, e)
                sys.exit(1)

    if not os.path.exists(target):
        logging.debug('%s does not exist', target)
        if not args.make_target:
            e = '%s does not exist and --marke-target is not provided'
            logging.error(e, target)
            sys.exit(1)

        logging.debug('Attempt to create: %s', target)
        # can make target
        try:
            os.makedirs(target)
        except OSError as e:
            errormsg = 'Failed to create target: %s - %s'
            logging.error(errormsg, target, str(e))
            sys.exit(1)

    # target was in place or has been created
    INSTPREFIX = '_anpylar'  # avoid pip auto-generation under root
    logging.debug('Creating temporary directory')
    with tempfile.TemporaryDirectory() as td:
        logging.debug('Created temporary directory: %s', td)
        pip_cmd = ['pip']
        pip_cmd += ['install']
        pip_cmd += ['--isolated']  # ignore user and environment variables
        pip_cmd += ['--ignore-installed']  # ignore if installed elsewhere
        pip_cmd += ['--no-compile']  # skip compilation
        pip_cmd += ['--prefix', INSTPREFIX]  # to fix inst sub-dir
        pip_cmd += ['--root', td]  # the root is the temporary directory
        pip_cmd += args.packages  # packages to install

        logging.debug('pip command to execute: %s', str(pip_cmd))
        try:
            subprocess.check_call(pip_cmd)
        except subprocess.CalledProcessError as e:
            logging.error('pip installation failed. Exiting: %s', str(e))
            sys.exit(1)

        # Installation succeeded. Scan site-packages directories
        site_packages = os.path.join(td, INSTPREFIX, 'Lib', 'site-packages')
        logging.debug('Finding pip installation under: %s', site_packages)

        if not os.path.exists(site_packages):
            logging.error('Existing: No dir with installed packages found')
            sys.exit(1)

        # Rather than walking top-down, get only 1st iteration
        root, dnames, fnames = next(os.walk(site_packages))
        # meta-info for packages
        dnames_info = [x for x in dnames if x.endswith('.dist-info')]
        logging.debug('Found info packages: %s', str(dnames_info))
        for dname in dnames_info:
            logging.debug('Processing info dir: %s', dname)
            wheelpath = os.path.join(root, dname, 'WHEEL')
            if not os.path.exists(wheelpath):
                logging.debug('No WHEEL file for: %s', dname)
                continue  # ASSUME PURE-PYTHON, nothing can be inferred

            purepy = True  # Assumption
            with open(wheelpath, encoding='utf-8') as wheel:
                for l in wheel:
                    tag, value = l.rstrip().split(': ')
                    if tag == 'Root-Is-Purelib':
                        purepy = value == 'true'

                    break  # target found go

            logging.debug('Package is purepy: %s', purepy)
            if not purepy:
                pname, ext = os.path.splitext(dname)  # xxxx-0.0.0.dist-info
                e = 'Package %s is not pure python. Bailing out'
                logging.error(e, dname)
                sys.exit(1)

        # Still alive ... all packages are pure-python (or assumed to be)
        # actual packages. Need list for package.json updates
        dnames_pkgs = [x for x in dnames if not x.endswith('.dist-info')]
        logging.debug('Found real packages: %s', str(dnames_pkgs))

        pkgdir = args.pkgdir
        if not pkgdir:  # nothing specified
            if not args.no_package_json:  # can get from package.json
                pkgdir = pjson.get('pkgdir', pkgdir)

        # Update destination to target + potential prefix
        dst = target
        dst = os.path.normpath(os.path.join(target, pkgdir))
        logging.debug('Adding prefix %s to target - dst: %s', pkgdir, dst)
        if not os.path.exists(dst):
            logging.debug('%s does not exist creating ...', dst)
            try:
                os.makedirs(dst)
            except OSError as e:
                errmsg = ('Error creating directory for installation: '
                          '%s - %s')
                logging.error(errmsg, dst, str(e))
                sys.exit(1)

        logging.info('Moving pip packages to final destination')
        # dst is in place, go for installation
        for dname in dnames_pkgs:
            logging.debug('Moving: %s', dname)
            dpath = os.path.join(root, dname)  # where package is

            dstpath = os.path.join(dst, dname)  # where package goes
            if os.path.exists(dstpath):
                logging.debug('Package already exists')
                if not args.no_replace:
                    logging.debug('Not replacing existing package')
                    continue  # existing package left in place

                logging.debug('Removing directory of existing package')
                try:
                    os.remove(dstpath)
                except OSError as e:
                    errmsg = ('Error creating directory for package: '
                              '%s - %s')
                    logging.error(errmsg, dstpath, str(e))
                    sys.exit(1)

            # Safe to move over if possible
            logging.debug('Finally moving package')
            try:
                # movt to "dst" and not "dstpath", because the dir is moved
                shutil.move(dpath, dst)  # move dpath under target
            except OSError as e:
                errmsg = 'Failed moving package: %s -> %s\n%s'
                logging.error(errmsg, dpath, dstpath, str(e))
                sys.exit(1)

    if args.no_package_json:
        logging.info('Requested no update of package.json. Exiting')
        sys.exit(0)

    # let's assume is a dict (it should be)
    logging.debug('Getting packages entry')
    json_pkgs = pjson.get('packages', [])
    logging.debug('Loaded packages are: %s', str(json_pkgs))

    # unixify and normalize paths
    npackages = [x.replace('\\', posixpath.sep) for x in json_pkgs]
    npackages = [posixpath.normpath(x) for x in npackages]

    npkgdir = os.path.normpath(pkgdir)
    npkgdir = npkgdir.replace(os.sep, posixpath.sep)

    if args.single_pkgdir and pkgdir:
        # single entry req: and (either args.pkgdir or from json)
        if npkgdir not in npackages:
            npackages.append(npkgdir)
    else:  # no single entry
        for dname in dnames_pkgs:
            logging.debug('Checking entry for %s:', dname)
            final_name = os.path.normpath(os.path.join(pkgdir, dname))
            # sanitize output for json
            final_name = final_name.replace(os.sep, posixpath.sep)
            if final_name not in npackages:
                logging.debug('Not present, adding it: %s (%s)',
                              dname, final_name)
                npackages.append(final_name)

    # update packages entry with normalized packages
    pjson['packages'] = npackages

    if args.pkgdir:  # update pkgdir if given, if needed or forced
        pjpkgdir = pjson.get('pkgdir', None)
        if pjpkgdir is None or args.force_pkgdir:
            pjson['pkgdir'] = npkgdir  # add the normalized/unixified

    # Update the file with the new json
    pjsontxt = json.dumps(pjson, indent=4)
    makefile_error(pjsonpath, pjsontxt, parser=parser)


def parse_args(pargs=None, name=None):
    if not name:
        name = os.path.splitext(os.path.basename(sys.argv[0]))[0]

    parser = argparse.ArgumentParser(
        prog=name,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=('AnPyLar pip Installer')
    )

    parser.add_argument('command', help='only *install* supported')

    parser.add_argument('packages', nargs='+',
                        help='pip packages to install')

    parser.add_argument('--target', action='store', default='.',
                        help='Target directory, defaults to current dir')

    parser.add_argument('--make-target', action='store_true',
                        help='Create target directory if does not exist')

    parser.add_argument('--no-replace', required=False, action='store_true',
                        help=('Do not replace existing packages with new '
                              'install'))

    pgroup = parser.add_argument_group(title='package.json')
    pgroup.add_argument('--no-package-json', action='store_true',
                        help=('If the installation directory contains a '
                              'package.json file the installed packages will '
                              'be added to the *packages* entry to be later '
                              'taken into consideration for packing the '
                              'complete application. Using this option '
                              'disables the behavior'))

    pgroup.add_argument('--pkgdir', action='store', default='',
                        help=('Install packages under pkgdir in the '
                              'application directory. This overrides the '
                              'entry pkgdir in package.json'))

    pgroup.add_argument('--single-pkgdir', action='store', default='',
                        help=('Add (if possible) a single directory entry to '
                              'packages rather than each packet individually'))

    pgroup.add_argument('--force-pkgdir', action='store_true',
                        help=('If a pkgdir is supplied and package.json is '
                              'being processed, update the entry for pkgdir '
                              'even if a value already exists'))

    pgroup = parser.add_mutually_exclusive_group()
    pgroup.add_argument('--quiet', '-q', action='store_true',
                        help='Remove output (errors will be reported)')
    pgroup.add_argument('--verbose', '-v', action='store_true',
                        help='Increase verbosity level')

    args = parser.parse_args(pargs)
    return args, parser


if __name__ == '__main__':
    run()
