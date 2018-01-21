#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###############################################################################
# Copyright 2018 The AnPyLar Team. All Rights Reserved.
# Use of this source code is governed by an MIT-style license that
# can be found in the LICENSE file at http://anpylar.com/mit-license
###############################################################################
import argparse
import datetime
import email.utils
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, HTTPServer
import io
import json
import logging
import mimetypes
import operator
import os
import os.path
import posixpath
import socketserver
import sys
import time
from urllib.parse import urlencode, urlparse, parse_qs
import webbrowser

from .logconfig import logconfig

from .packaging import Bundler
from .utils import readfile_error, win_wait_for_parent


Template_Auto_Index = '''
<!DOCTYPE html>
<html>
<head>
  <title>Auto Serving</title>

  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <script src="anpylar.js" async></script>

  <script type="text/python" src="index.py"></script>
</head>
<body></body>
</html>
'''


def loadmodule(modpath, modname=''):
    if not modpath.endswith('.py'):
        modpath += '.py'

    # generate a random name for the module
    if not modname:
        modpathbase = os.path.basename(modpath)
        modname, _ = os.path.splitext(modpathbase)

    try:
        import importlib.machinery
        loader = importlib.machinery.SourceFileLoader(modname, modpath)
        mod = loader.load_module()
    except Exception as e:
        return (None, e)

    return (mod, None)


class RequestHandler(SimpleHTTPRequestHandler):
    # protocol_version = 'HTTP/1.0'

    def _write(self, text, convert=True, encoding='utf-8'):
        self.wfile.write(text if not convert else bytes(text, encoding))

    def _redir(self, location, query=None):
        loc = '{}{}'.format(self._netloc, location)
        if query:
            loc = '?'.join((loc, query))

        logging.debug('Redirecting to: %s', loc)
        self.send_response(HTTPStatus.TEMPORARY_REDIRECT)
        self.send_header('Location', loc)
        self.end_headers()
        return None

    def _notfound(self):
        # All failed, return 404
        logging.debug('returning 404')
        self.send_response(HTTPStatus.NOT_FOUND)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self._write('<html><head><title>Not Found</title></head>')
        self._write('<body>')
        self._write('<p>You accessed path: {}</p>'.format(self.path))
        self._write('</body></html>')
        return None

    def _fullsendfile(self, fname):
        logging.debug('Sending file: %s', fname)
        with open(fname, 'rb') as f:  # bytes needed for wfile.write
            fcontent = f.read()

        bname = posixpath.basename(fname)
        _, ext = posixpath.splitext(bname)
        ctype, encoding = mimetypes.guess_type(fname)
        self.send_response(HTTPStatus.OK)
        self.send_header('Content-type', ctype or 'text/plain')
        self.end_headers()
        self._write(fcontent, convert=False)  # read as bytes already

    def _endfile(self, f):
        if f is not None:
            f.close()

    def _sendfile(self, f):
        if f is not None:
            logging.debug('Sending file object')
            try:
                if hasattr(f, 'read'):
                    fcontent = f.read()
                else:
                    fcontent = f
            except:
                pass
            else:
                self._write(fcontent, convert=False)  # read as bytes already
            finally:
                if hasattr(f, 'close'):
                    f.close()

    def _sendcontent(self, content, ctype, encoding='utf-8'):
        bcontent = content.encode(encoding)
        logging.debug('sending content (in bytes)')
        self.send_response(HTTPStatus.OK)
        self.send_header('Content-type', ctype)
        self.send_header('Content-Length', str(len(bcontent)))
        self.end_headers()
        return bcontent

    def _checkfile(self, path):
        logging.debug('entering checkfile')
        try:
            f = open(path, 'rb')
        except OSError:
            logging.debug('failed to open: %s', path)
            logging.debug('returning 404')
            return self._notfound()

        IF_MOD = 'If-Modified-Since'
        IF_NONE = 'If-None-Match'

        try:
            fs = os.fstat(f.fileno())
            # Use browser cache if possible
            if IF_MOD in self.headers and IF_NONE not in self.headers:
                # compare If-Modified-Since and time of last file modification
                if_mod = self.headers[IF_MOD]
                try:
                    ims = email.utils.parsedate_to_datetime(if_mod)
                except (TypeError, IndexError, OverflowError, ValueError):
                    pass  # ignore ill-formed values
                else:
                    if ims.tzinfo is None:
                        # obsolete format with no timezone, cf.
                        # https://tools.ietf.org/html/rfc7231#section-7.1.1.1
                        ims = ims.replace(tzinfo=datetime.timezone.utc)
                    if ims.tzinfo is datetime.timezone.utc:
                        # compare to UTC datetime of last modification
                        last_modif = datetime.datetime.fromtimestamp(
                            fs.st_mtime, datetime.timezone.utc
                        )
                        # remove microseconds, like in If-Modified-Since
                        last_modif = last_modif.replace(microsecond=0)

                        if last_modif <= ims:
                            self.send_response(HTTPStatus.NOT_MODIFIED)
                            self.end_headers()
                            f.close()
                            return None

            self.send_response(HTTPStatus.OK)
            ctype = self.guess_type(path)
            self.send_header('Content-type', ctype)
            self.send_header('Content-Length', str(fs[6]))
            self.send_header('Last-Modified',
                             self.date_time_string(fs.st_mtime))
            self.end_headers()
            return f
        except Exception as e:
            f.close()
            logging.debug('checkfile exception: %s', str(e))
            return self._notfound()  # instead of raising

    def do_common(self):
        self.cliargs = cliargs = self.server.cliargs  # cache lookup

        logging.debug('-' * 50)
        logging.debug('server path is: %s', cliargs._spath)

        host = self.headers['Host']
        if host is None:  # was not present !!!!!!!
            sname = cliargs.sname or self.server_name
            host = '{}:{}'.format(sname, self.server.server_port)

        self._netloc = 'http://{}'.format(host)
        self._url = '{}{}'.format(self._netloc, self.path)

        urlparts = urlparse(self.path)
        rootpath = urlparts.path
        rp = posixpath.normpath(rootpath)
        query = urlparts.query

        relpath = rootpath[1:]  # remove leading slash

        logging.debug('self.path is: %s', self.path)
        logging.debug('rootpath: %s', rootpath)
        logging.debug('relpath: %s', relpath)
        logging.debug('query: %s', query)

        target = posixpath.join(cliargs._spath, relpath)
        targetname = posixpath.basename(target)
        logging.debug('target: %s', target)

        if cliargs.api_url:
            logging.debug('checking api_url: %s', cliargs.api_url)
            if rootpath.startswith(cliargs.api_url):
                logging.debug('api url matched for get. Returning data')

                if query:
                    logging.debug('api: get with query: %s', query)
                    qd = parse_qs(query)
                    res = list(cliargs.api_idata.values())
                    for k, vs in qd.items():  # ret is key / list of values
                        igetter = operator.itemgetter(k)
                        for v in vs:
                            res = [x for x in res if v in igetter(x)]

                    content = json.dumps(res)

                elif len(rp) > len(cliargs.api_url):  # api_url is normalized
                    # return the id (only thing left in url)
                    epath = posixpath.basename(rootpath)
                    logging.debug('api: get with extra path: %s', epath)
                    key = int(epath)
                    content = json.dumps(cliargs.api_idata.get(int(key), {}))
                else:
                    logging.debug('api: get ... mean an lean')
                    content = json.dumps(list(cliargs.api_idata.values()))

                return self._sendcontent(content, 'application/json')

        is_anpylar = targetname == 'anpylar.js'

        if cliargs.auto_serve:
            if targetname == 'index.py':
                logging.debug('serving auto_script')
                return self._checkfile(cliargs.auto_serve)

            if not is_anpylar and rootpath == '/':
                # return the index file in any other case
                logging.debug('Serving auto index.html')
                return self._sendcontent(Template_Auto_Index, 'text/html')

        if rootpath == '/':  # root directory is only valid directory
            logging.debug('Root directory sought: %s', target)
            tfile = posixpath.join(target, cliargs.index)
            logging.debug('looking for: %s', tfile)
            if os.path.isfile(tfile):
                logging.debug('Index in directory')
                return self._checkfile(tfile)

            return self._notfound()

        elif os.path.isfile(target) or is_anpylar:  # is a file, return it
            logging.debug('Found file: %s', target)
            if targetname == cliargs.index:
                # index file directly sought - Send to containing directory
                logging.debug('Index file, redirecting')
                return self._redir(posixpath.dirname(rootpath), query)

            if cliargs.dev:
                logging.debug('Checking serving of anpylar.js')
                if targetname == 'anpylar.js':
                    logging.debug('serving development anpylar.js')
                    anpylar_js = self._make_bundle()
                    return self._sendcontent(anpylar_js, 'text/javascript')

            logging.debug('Other file, returning')
            return self._checkfile(target)  # no index file, return it

        # else
        logging.debug('Neither root nor real file sought, checking imports')
        bname = targetname
        _, ext = posixpath.splitext(bname)
        logging.debug('bname is: %s and ext %s:', bname, ext)
        if ext == '.py' and query:  # import attempt and was no file
            logging.debug('Failed .py import attempt: %s', self.path)
            return self._notfound()
        elif ext == '.js' or bname.endswith('.pyc.js'):
            logging.debug('Failed .js or .pyc.js import: %s', self.path)
            return self._notfound()
        elif bname in ['favicon.ico']:  # avoid redirects
            logging.debug('Skipping file: %s', bname)
            return self._notfound()

        # no file, no root dir and no import ... redirect to root with route
        qs0 = {'route': self.path}
        localquery = urlencode(qs0)
        logging.debug('Redir to root with query: %s - %s', query, localquery)
        return self._redir('/', '&'.join((query or '', localquery)))

    def do_HEAD(self):
        self._endfile(self.do_common())

    def do_GET(self):
        self._sendfile(self.do_common())

    def do_POST(self):
        self.cliargs = cliargs = self.server.cliargs  # cache lookup
        logging.debug('-' * 50)
        logging.debug('POST request')
        if not cliargs.api_url:
            logging.debug('POST and no api_url defined')
            logging.debug('POST headers: %s', str(self.headers))
            clength = int(self.headers['Content-Length'])
            logging.debug('Displaying Posted Body of length: %d', clength)
            data = self.rfile.read(clength)
            logging.debug('body is: %s', data)
            return

        querysplit = self.path.split('?')
        if len(querysplit) > 1:
            rootpath, query = querysplit
        else:
            rootpath, query = querysplit[0], None

        logging.debug('checking api_url: %s', cliargs.api_url)
        if not rootpath.startswith(cliargs.api_url):
            logging.debug('api url not matched for post. 404')
            return self._notfound()

        logging.debug('api url matched for post')

        clength = int(self.headers['Content-Length'])
        data = self.rfile.read(clength)
        d = json.loads(data)
        cliargs.api_hidx = idx = cliargs.api_hidx + 1  # inc id
        d[cliargs.api_index] = idx
        cliargs.api_idata[idx] = d
        content = json.dumps(d)
        return self._sendfile(self._sendcontent(content, 'application/json'))

    def do_DELETE(self):
        self.cliargs = cliargs = self.server.cliargs  # cache lookup
        logging.debug('-' * 50)

        self.cliargs = cliargs = self.server.cliargs  # cache lookup
        if not cliargs.api_url:
            logging.debug('DELETE and no api_url defined')
            return

        querysplit = self.path.split('?')
        if len(querysplit) > 1:
            rootpath, query = querysplit
        else:
            rootpath, query = querysplit[0], None

        logging.debug('checking api_url: %s', cliargs.api_url)
        if not rootpath.startswith(cliargs.api_url):
            logging.debug('api url not matched for delete. 404')
            return self._notfound()

        logging.debug('api url matched for delete')

        key = int(posixpath.basename(posixpath.normpath(rootpath)))
        del cliargs_api_idata[key]
        content = json.dumps({})
        return self._sendfile(self._sendcontent(content, 'application/json'))

    def do_PUT(self):
        self.cliargs = cliargs = self.server.cliargs  # cache lookup
        logging.debug('-' * 50)

        self.cliargs = cliargs = self.server.cliargs  # cache lookup
        if not cliargs.api_url:
            logging.debug('PUT and no api_url defined')
            return

        querysplit = self.path.split('?')
        if len(querysplit) > 1:
            rootpath, query = querysplit
        else:
            rootpath, query = querysplit[0], None

        logging.debug('checking api_url: %s', cliargs.api_url)
        if not rootpath.startswith(cliargs.api_url):
            logging.debug('api url not matched for PUT. 404')
            return self._notfound()

        logging.debug('api url matched for PUT')

        key = int(posixpath.basename(posixpath.normpath(rootpath)))

        clength = int(self.headers['Content-Length'])
        data = self.rfile.read(clength)
        d = json.loads(data)
        cliargs.api_idata[key].update(**d)
        content = json.dumps(d)
        return self._sendfile(self._sendcontent(content, 'application/json'))

    def _make_bundle(self):
        cliargs = self.cliargs
        logging.debug('Creating on-the-fly anpylar.js')
        bundler = Bundler()
        bundler.set_br_debug(True)
        if cliargs.dev_brython:
            logging.debug('- brython.js from: %s', cliargs.dev_brython)
            bundler.set_brython(cliargs.dev_brython)

        if cliargs.dev_stdlib:
            logging.debug('- stdlib from: %s', cliargs.dev_stdlib)
            bundler.set_brython_stdlib(cliargs.dev_stdlib)

        if cliargs.dev_anpylar_js:
            logging.debug('- anpylar_js from: %s', cliargs.dev_anpylar_js)
            bundler.set_anpylar_js(cliargs.dev_anpylar_js)

        if cliargs.dev_pkg_vfs:
            logging.debug('- adding packages from vfs files')
            for v in cliargs.dev_pkg_vfs:
                logging.debug('- adding vfs: %s', v)
                bundler.add_vfs_js(v)

        if cliargs.dev_pkg_auto:
            logging.debug('- adding packages from auto_vfs files')
            for v in cliargs.dev_pkg_auto:
                logging.debug('- adding auto_vfs: %s', v)
                bundler.add_auto_vfs(v)

        if cliargs.dev_pkg_dir:
            logging.debug('- adding packages from dir')
            for v in cliargs.dev_pkg_dir:
                logging.debug('- adding dir: %s', v)
                bundler.add_pkg_dir(v)

        if cliargs.dev_anpylar_auto:
            logging.debug('- anpylar.auto_vfs.js from: %s',
                          cliargs.dev_anpylar_auto)
            bundler.set_anpylar_auto_vfs(cliargs.dev_anpylar_auto)

        elif cliargs.dev_anpylar_vfs:
            logging.debug('- anpylar.vfs.js from: %s', cliargs.dev_anpylar_vfs)
            bundler.set_anpylar_vfs(cliargs.dev_anpylar_vfs)

        elif cliargs.dev_anpylar_dir:
            logging.debug('- anpylar.vfs from dir %s', cliargs.dev_anpylar_dir)
            bundler.add_pkg_dir(cliargs.dev_anpylar_dir)

        if not cliargs.dev_anpylar_dir:  # re-check to do it only once
            # no dir ... either specific vfs or internal, is in the bundle
            bundler.do_anpylar_vfs()

        if cliargs.dev_optimize:
            logging.debug('- Optimizing bundle')
            bundler.optimize_stdlib()

        fout = io.StringIO()
        bundler.write_bundle(fout)
        fout.seek(0)  # reset the stream to read the value from the start
        content = fout.getvalue()
        logging.debug('size of fout is: %d', len(content))
        return content


def run(pargs=None, name=None):
    args, parser = parse_args(pargs=pargs, name=name)
    logconfig(args.quiet, args.verbose)  # configure logging

    # Determine if dev mode is active to build an on-the-fly bundle
    args.dev = any(getattr(args, x) for x in dir(args) if x.startswith('dev_'))

    if args.auto_serve:
        args.dev = True

        args.auto_serve = os.path.normpath(args.auto_serve)
        if os.path.isdir(args.auto_serve):
            # Get first .py file
            root, dnames, fnames = next(os.walk(args.auto_serve))
            found = None
            for fname in fnames:
                _, ext = os.path.splitext(fname)
                if ext == '.py':
                    args.auto_serve = found = os.path.join(root, fname)
                    break

            if found is None:
                logging.error('No .py script in auto_serve dir: %s'
                              % args.auto_serve)
                sys.exit(1)

        elif not os.path.isfile(args.auto_serve):
            logging.error('auto_serve % not found' % args.auto_serve)
            sys.exit(1)

    logging.debug('args.dev is %s', str(args.dev))

    if args.api_url:
        if not args.api_url.startswith('/'):
            args.api_url = '/' + args.api_url

        if not args.api_url.startswith('/'):
            args.api_url += '/'

        args.api_url = posixpath.normpath(args.api_url)

        # Check the mod
        apimod, e = loadmodule(args.api_mod)
        if apimod is None:
            logging.error('API URL specified: %s', args.api_url)
            logging.error('But cannot load API Module: %s', args.api_mod)
            sys.exit(1)

        # Check the data
        apidata = getattr(apimod, args.api_data, None)
        if apidata is None:
            logging.error('API URL specified: %s', args.api_url)
            logging.error('API Module Loaded: %s', args.api_mod)
            logging.error('But cannot find API Data: %s', args.api_data)
            sys.exit(1)

        try:
            args.api_idata = {d[args.api_index]: d for d in apidata}
        except KeyError:
            logging.error('API URL specified: %s', args.api_url)
            logging.error('API Module Loaded: %s', args.api_mod)
            logging.error('API Data found')
            logging.error('Failed to find index in  data: %s', args.api_index)
            sys.exit(1)

        args.api_hidx = max(args.api_idata.keys())

    srvaddr = ('', args.port)
    handlercls = SimpleHTTPRequestHandler if args.simple else RequestHandler

    logging.info('%s: Server Starts - %s', time.asctime(), str(srvaddr))

    # rework the application path for sanity
    args._spath = args.application.replace('\\', '/')
    if args._spath[-1] != '/':
        args._spath += '/'  # make sure it has a trailing slath

    # to allow restarting the server in short succession
    socketserver.TCPServer.allow_reuse_address = True

    httpd = HTTPServer(srvaddr, handlercls)
    httpd.cliargs = args

    if args.browser:  # try to open a browser if needed
        url = 'http://{}:{}'.format(httpd.server_name, httpd.server_port)
        webbrowser.open_new_tab(url)

    # needed to avoid potential process deadlocks under windows if run as child
    win_wait_for_parent()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()

    logging.info('%s: Server Stops - %s', time.asctime(), str(srvaddr))


def parse_args(pargs=None, name=None):
    if not name:
        name = os.path.splitext(os.path.basename(sys.argv[0]))[0]

    parser = argparse.ArgumentParser(
        prog=name,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=(
            'AnPyLar Simple Server'
        )
    )

    parser.add_argument('application', nargs='?', default='.',
                        help='Application directory to serve')

    pgroup = parser.add_argument_group(title='Server Options')
    pgroup.add_argument('--sname', required=False, default='127.0.0.1',
                        help='Server Name')

    pgroup.add_argument('--port', required=False, default=2222, type=int,
                        help='Port to listen to')

    pgroup.add_argument('--index', required=False, default='index.html',
                        help='Index file to look for')

    pgroup.add_argument('--simple', required=False, action='store_true',
                        help='Use built-in SimpleHTTPRequestHandler')

    pgroup = parser.add_argument_group(title='Miscelenaous options')
    pgroup.add_argument('--browser', required=False, action='store_true',
                        help='Try to open a browser to the served app')

    pgroup = parser.add_argument_group(
        title='Development options',
        description=('If any of the options in this group is set, the server '
                     'will construct an on-the-fly anpylar.js bundle with '
                     'each reload either with the default files in the '
                     'package or with the provided files/directories'))

    pgroup.add_argument('--auto-serve', action='store',
                        help=('Serve the path/file given as argument, '
                              'automatically providing a wrapping index.html '
                              'file and anpylar.js. This activates '
                              'development mode'))

    pgroup.add_argument('--dev-on', action='store_true',
                        help='Activate dev serving unconditionally')

    pgroup.add_argument('--dev-brython', help='Serve dev brython')

    pgroup.add_argument('--dev-stdlib', help='Serve dev brython stdlib')

    pgroup.add_argument('--dev-anpylar-js', help='Serve dev anpylar_js.js')

    pgroup.add_argument('--dev-anpylar-vfs',
                        help='Serve dev from anpylar.vfs.js')

    pgroup.add_argument('--dev-anpylar-auto',
                        help='Serve dev from anpylar.auto_vfs.js')

    pgroup.add_argument('--dev-anpylar-dir',
                        help='Serve dev anpylar from directory')

    pgroup.add_argument('--dev-pkg-vfs', action='append', default=[],
                        help='Add a vfs.js package to the dev bundle')

    pgroup.add_argument('--dev-pkg-auto', action='append', default=[],
                        help='Add a auto_vfs.js package to the dev bundle')

    pgroup.add_argument('--dev-pkg-dir', action='append', default=[],
                        help='Add a directory package to the dev bundle')

    pgroup.add_argument('--dev-optimize', action='store_true',
                        help='Optimized the generated bundle')

    pgroup = parser.add_argument_group(title='API options')
    pgroup.add_argument('--api-url', default='',
                        help='URL path when serving an API request')

    pgroup.add_argument('--api-mod', default='',
                        help='Which python source file contains the data')

    pgroup.add_argument('--api-data', default='',
                        help='Name of the variable holding teh data')

    pgroup.add_argument('--api-index', default='',
                        help='Name of the field which will serve as an index')

    pgroup = parser.add_mutually_exclusive_group()
    pgroup.add_argument('--quiet', '-q', action='store_true',
                        help='Remove output (errors will be reported)')
    pgroup.add_argument('--verbose', '-v', action='store_true',
                        help='Increase verbosity level')

    args = parser.parse_args(pargs)
    return args, parser


if __name__ == '__main__':
    run()
