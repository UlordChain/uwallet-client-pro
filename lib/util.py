#!/usr/bin/env python
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2011 Thomas Voegtlin
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os, sys, re, json
import platform
import shutil
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
import traceback
import urlparse
import urllib
import threading
from i18n import _

base_units = {'BTC':8, 'mBTC':5, 'uBTC':2}
fee_levels = [_('Within 25 blocks'), _('Within 10 blocks'), _('Within 5 blocks'), _('Within 2 blocks'), _('In the next block')]

def normalize_version(v):
    return [int(x) for x in re.sub(r'(\.0+)*$','', v).split(".")]

class NotEnoughFunds(Exception): pass

class InvalidPassword(Exception):
    def __str__(self):
        return _("Incorrect password")

# Throw this exception to unwind the stack like when an error occurs.
# However unlike other exceptions the user won't be informed.
class UserCancelled(Exception):
    '''An exception that is suppressed from the user'''
    pass

class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        from transaction import Transaction
        if isinstance(obj, Transaction):
            return obj.as_dict()
        return super(MyEncoder, self).default(obj)

class PrintError(object):
    '''A handy base class'''
    def diagnostic_name(self):
        return self.__class__.__name__

    def print_error(self, *msg):
        print_error("[%s]" % self.diagnostic_name(), *msg)

    def print_msg(self, *msg):
        print_msg("[%s]" % self.diagnostic_name(), *msg)

class ThreadJob(PrintError):
    """A job that is run periodically from a thread's main loop.  run() is
    called from that thread's context.
    """

    def run(self):
        """Called periodically from the thread"""
        pass

class DebugMem(ThreadJob):
    '''A handy class for debugging GC memory leaks'''
    def __init__(self, classes, interval=30):
        self.next_time = 0
        self.classes = classes
        self.interval = interval

    def mem_stats(self):
        import gc
        self.print_error("Start memscan")
        gc.collect()
        objmap = defaultdict(list)
        for obj in gc.get_objects():
            for class_ in self.classes:
                if isinstance(obj, class_):
                    objmap[class_].append(obj)
        for class_, objs in objmap.items():
            self.print_error("%s: %d" % (class_.__name__, len(objs)))
        self.print_error("Finish memscan")

    def run(self):
        if time.time() > self.next_time:
            self.mem_stats()
            self.next_time = time.time() + self.interval

class DaemonThread(threading.Thread, PrintError):
    """ daemon thread that terminates cleanly """

    def __init__(self):
        threading.Thread.__init__(self)
        self.parent_thread = threading.currentThread()
        self.running = False
        self.running_lock = threading.Lock()
        self.job_lock = threading.Lock()
        self.jobs = []

    def add_jobs(self, jobs):
        with self.job_lock:
            self.jobs.extend(jobs)

    def run_jobs(self):
        # Don't let a throwing job disrupt the thread, future runs of
        # itself, or other jobs.  This is useful protection against
        # malformed or malicious server responses
        with self.job_lock:
            for job in self.jobs:
                try:
                    job.run()
                except:
                    traceback.print_exc(file=sys.stderr)

    def remove_jobs(self, jobs):
        with self.job_lock:
            for job in jobs:
                self.jobs.remove(job)

    def start(self):
        with self.running_lock:
            self.running = True
        return threading.Thread.start(self)

    def is_running(self):
        with self.running_lock:
            return self.running and self.parent_thread.is_alive()

    def stop(self):
        with self.running_lock:
            self.running = False

    def on_stop(self):
        if 'ANDROID_DATA' in os.environ:
            import jnius
            jnius.detach()
            self.print_error("jnius detach")
        self.print_error("stopped")


is_verbose = False
def set_verbosity(b):
    global is_verbose
    is_verbose = b


def print_error(*args):
    if not is_verbose: return
    print_stderr(*args)

def print_stderr(*args):
    args = [str(item) for item in args]
    sys.stderr.write(" ".join(args) + "\n")
    sys.stderr.flush()

def print_msg(*args):
    # Stringify args
    args = [str(item) for item in args]
    sys.stdout.write(" ".join(args) + "\n")
    sys.stdout.flush()

def json_encode(obj):
    try:
        s = json.dumps(obj, sort_keys = True, indent = 4, cls=MyEncoder)
    except TypeError:
        s = repr(obj)
    return s

def json_decode(x):
    try:
        return json.loads(x, parse_float=decimal.Decimal)
    except:
        return x

# decorator that prints execution time
def profiler(func):
    def do_profile(func, args, kw_args):
        n = func.func_name
        t0 = time.time()
        o = func(*args, **kw_args)
        t = time.time() - t0
        print_error("[profiler]", n, "%.4f"%t)
        return o
    return lambda *args, **kw_args: do_profile(func, args, kw_args)


def android_ext_dir():
    import jnius
    env = jnius.autoclass('android.os.Environment')
    return env.getExternalStorageDirectory().getPath()

def android_data_dir():
    import jnius
    PythonActivity = jnius.autoclass('org.kivy.android.PythonActivity')
    return PythonActivity.mActivity.getFilesDir().getPath() + '/data'

def android_headers_path():
    path = android_ext_dir() + '/org.uwallet.uwallet/blockchain_headers'
    d = os.path.dirname(path)
    if not os.path.exists(d):
        os.mkdir(d)
    return path

def android_check_data_dir():
    """ if needed, move old directory to sandbox """
    ext_dir = android_ext_dir()
    data_dir = android_data_dir()
    old_uwallet_dir = ext_dir + '/uwallet'
    if not os.path.exists(data_dir) and os.path.exists(old_uwallet_dir):
        import shutil
        new_headers_path = android_headers_path()
        old_headers_path = old_uwallet_dir + '/blockchain_headers'
        if not os.path.exists(new_headers_path) and os.path.exists(old_headers_path):
            print_error("Moving headers file to", new_headers_path)
            shutil.move(old_headers_path, new_headers_path)
        print_error("Moving data to", data_dir)
        shutil.move(old_uwallet_dir, data_dir)
    return data_dir

def get_headers_path(config):
    if 'ANDROID_DATA' in os.environ:
        return android_headers_path()
    else:
        return os.path.join(config.path, 'blockchain_headers')

def user_dir():
    if "HOME" in os.environ:
        return os.path.join(os.environ["HOME"], ".uwallet")
    elif "APPDATA" in os.environ:
        return os.path.join(os.environ["APPDATA"], "UWallet")
    elif "LOCALAPPDATA" in os.environ:
        return os.path.join(os.environ["LOCALAPPDATA"], "UWallet")
    elif 'ANDROID_DATA' in os.environ:
        return android_check_data_dir()
    else:
        #raise Exception("No home directory found in environment variables.")
        return

def format_satoshis_plain(x, decimal_point = 8):
    '''Display a satoshi amount scaled.  Always uses a '.' as a decimal
    point and has no thousands separator'''
    scale_factor = pow(10, decimal_point)
    return "{:.8f}".format(Decimal(x) / scale_factor).rstrip('0').rstrip('.')

def format_satoshis(x, is_diff=False, num_zeros = 0, decimal_point = 8, whitespaces=False):
    from locale import localeconv
    if x is None:
        return 'unknown'
    x = int(x)  # Some callers pass Decimal
    scale_factor = pow (10, decimal_point)
    integer_part = "{:n}".format(int(abs(x) / scale_factor))
    if x < 0:
        integer_part = '-' + integer_part
    elif is_diff:
        integer_part = '+' + integer_part
    dp = localeconv()['decimal_point']
    fract_part = ("{:0" + str(decimal_point) + "}").format(abs(x) % scale_factor)
    fract_part = fract_part.rstrip('0')
    if len(fract_part) < num_zeros:
        fract_part += "0" * (num_zeros - len(fract_part))
    result = integer_part + dp + fract_part
    if whitespaces:
        result += " " * (decimal_point - len(fract_part))
        result = " " * (15 - len(result)) + result
    return result.decode('utf8')

def timestamp_to_datetime(timestamp):
    try:
        return datetime.fromtimestamp(timestamp)
    except:
        return None

def format_time(timestamp):
    date = timestamp_to_datetime(timestamp)
    return date.isoformat(' ')[:-3] if date else _("Unknown")


# Takes a timestamp and returns a string with the approximation of the age
def age(from_date, since_date = None, target_tz=None, include_seconds=False):
    if from_date is None:
        return "Unknown"

    from_date = datetime.fromtimestamp(from_date)
    if since_date is None:
        since_date = datetime.now(target_tz)

    td = time_difference(from_date - since_date, include_seconds)
    return td + " ago" if from_date < since_date else "in " + td


def time_difference(distance_in_time, include_seconds):
    #distance_in_time = since_date - from_date
    distance_in_seconds = int(round(abs(distance_in_time.days * 86400 + distance_in_time.seconds)))
    distance_in_minutes = int(round(distance_in_seconds/60))

    if distance_in_minutes <= 1:
        if include_seconds:
            for remainder in [5, 10, 20]:
                if distance_in_seconds < remainder:
                    return "less than %s seconds" % remainder
            if distance_in_seconds < 40:
                return "half a minute"
            elif distance_in_seconds < 60:
                return "less than a minute"
            else:
                return "1 minute"
        else:
            if distance_in_minutes == 0:
                return "less than a minute"
            else:
                return "1 minute"
    elif distance_in_minutes < 45:
        return "%s minutes" % distance_in_minutes
    elif distance_in_minutes < 90:
        return "about 1 hour"
    elif distance_in_minutes < 1440:
        return "about %d hours" % (round(distance_in_minutes / 60.0))
    elif distance_in_minutes < 2880:
        return "1 day"
    elif distance_in_minutes < 43220:
        return "%d days" % (round(distance_in_minutes / 1440))
    elif distance_in_minutes < 86400:
        return "about 1 month"
    elif distance_in_minutes < 525600:
        return "%d months" % (round(distance_in_minutes / 43200))
    elif distance_in_minutes < 1051200:
        return "about 1 year"
    else:
        return "over %d years" % (round(distance_in_minutes / 525600))

block_explorer_info = {
    'Biteasy.com': ('https://www.biteasy.com/blockchain',
                        {'tx': 'transactions', 'addr': 'addresses'}),
    'Bitflyer.jp': ('https://chainflyer.bitflyer.jp',
                        {'tx': 'Transaction', 'addr': 'Address'}),
    'Blockchain.info': ('https://blockchain.info',
                        {'tx': 'tx', 'addr': 'address'}),
    'blockchainbdgpzk.onion': ('https://blockchainbdgpzk.onion',
                        {'tx': 'tx', 'addr': 'address'}),
    'Blockr.io': ('https://btc.blockr.io',
                        {'tx': 'tx/info', 'addr': 'address/info'}),
    'Blocktrail.com': ('https://www.blocktrail.com/BTC',
                        {'tx': 'tx', 'addr': 'address'}),
    'BTC.com': ('https://chain.btc.com',
                        {'tx': 'tx', 'addr': 'address'}),
    'Chain.so': ('https://www.chain.so',
                        {'tx': 'tx/BTC', 'addr': 'address/BTC'}),
    'Insight.is': ('https://insight.bitpay.com',
                        {'tx': 'tx', 'addr': 'address'}),
    'TradeBlock.com': ('https://tradeblock.com/blockchain',
                        {'tx': 'tx', 'addr': 'address'}),
    'system default': ('blockchain:',
                        {'tx': 'tx', 'addr': 'address'}),
}

def block_explorer(config):
    return config.get('block_explorer', 'Blockchain.info')

def block_explorer_tuple(config):
    return block_explorer_info.get(block_explorer(config))

def block_explorer_URL(config, kind, item):
    be_tuple = block_explorer_tuple(config)
    if not be_tuple:
        return
    kind_str = be_tuple[1].get(kind)
    if not kind_str:
        return
    url_parts = [be_tuple[0], kind_str, item]
    return "/".join(url_parts)

# URL decode
#_ud = re.compile('%([0-9a-hA-H]{2})', re.MULTILINE)
#urldecode = lambda x: _ud.sub(lambda m: chr(int(m.group(1), 16)), x)

def parse_URI(uri, on_pr=None):
    import bitcoin
    from bitcoin import COIN

    if ':' not in uri:
        if not bitcoin.is_address(uri):
            raise BaseException("Not a bitcoin address")
        return {'address': uri}

    u = urlparse.urlparse(uri)
    if u.scheme != 'bitcoin':
        raise BaseException("Not a bitcoin URI")
    address = u.path

    # python for android fails to parse query
    if address.find('?') > 0:
        address, query = u.path.split('?')
        pq = urlparse.parse_qs(query)
    else:
        pq = urlparse.parse_qs(u.query)

    for k, v in pq.items():
        if len(v)!=1:
            raise Exception('Duplicate Key', k)

    out = {k: v[0] for k, v in pq.items()}
    if address:
        if not bitcoin.is_address(address):
            raise BaseException("Invalid bitcoin address:" + address)
        out['address'] = address
    if 'amount' in out:
        am = out['amount']
        m = re.match('([0-9\.]+)X([0-9])', am)
        if m:
            k = int(m.group(2)) - 8
            amount = Decimal(m.group(1)) * pow(  Decimal(10) , k)
        else:
            amount = Decimal(am) * COIN
        out['amount'] = int(amount)
    if 'message' in out:
        out['message'] = out['message'].decode('utf8')
        out['memo'] = out['message']
    if 'time' in out:
        out['time'] = int(out['time'])
    if 'exp' in out:
        out['exp'] = int(out['exp'])
    if 'sig' in out:
        out['sig'] = bitcoin.base_decode(out['sig'], None, base=58).encode('hex')

    r = out.get('r')
    sig = out.get('sig')
    name = out.get('name')
    if r or (name and sig):
        def get_payment_request_thread():
            import paymentrequest as pr
            if name and sig:
                s = pr.serialize_request(out).SerializeToString()
                request = pr.PaymentRequest(s)
            else:
                request = pr.get_payment_request(r)
            on_pr(request)
        t = threading.Thread(target=get_payment_request_thread)
        t.setDaemon(True)
        t.start()

    return out


def create_URI(addr, amount, message):
    import bitcoin
    if not bitcoin.is_address(addr):
        return ""
    query = []
    if amount:
        query.append('amount=%s'%format_satoshis_plain(amount))
    if message:
        if type(message) == unicode:
            message = message.encode('utf8')
        query.append('message=%s'%urllib.quote(message))
    p = urlparse.ParseResult(scheme='bitcoin', netloc='', path=addr, params='', query='&'.join(query), fragment='')
    return urlparse.urlunparse(p)


# Python bug (http://bugs.python.org/issue1927) causes raw_input
# to be redirected improperly between stdin/stderr on Unix systems
def raw_input(prompt=None):
    if prompt:
        sys.stdout.write(prompt)
    return builtin_raw_input()
import __builtin__
builtin_raw_input = __builtin__.raw_input
__builtin__.raw_input = raw_input



def parse_json(message):
    n = message.find('\n')
    if n==-1:
        return None, message
    try:
        j = json.loads( message[0:n] )
    except:
        j = None
    return j, message[n+1:]




class timeout(Exception):
    pass

import socket
import errno
import json
import ssl
import time

class SocketPipe:

    def __init__(self, socket):
        self.socket = socket
        self.message = ''
        self.set_timeout(0.1)
        self.recv_time = time.time()

    def set_timeout(self, t):
        self.socket.settimeout(t)

    def idle_time(self):
        return time.time() - self.recv_time

    def get(self):
        while True:
            response, self.message = parse_json(self.message)
            if response is not None:
                return response
            try:
                data = self.socket.recv(1024)
            except socket.timeout:
                raise timeout
            except ssl.SSLError:
                raise timeout
            except socket.error, err:
                if err.errno == 60:
                    raise timeout
                elif err.errno in [11, 35, 10035]:
                    print_error("socket errno %d (resource temporarily unavailable)"% err.errno)
                    time.sleep(0.2)
                    raise timeout
                else:
                    print_error("pipe: socket error", err)
                    data = ''
            except:
                traceback.print_exc(file=sys.stderr)
                data = ''

            if not data:  # Connection closed remotely
                return None
            self.message += data
            self.recv_time = time.time()

    def send(self, request):
        out = json.dumps(request) + '\n'
        self._send(out)

    def send_all(self, requests):
        out = ''.join(map(lambda x: json.dumps(x) + '\n', requests))
        self._send(out)

    def _send(self, out):
        while out:
            try:
                sent = self.socket.send(out)
                out = out[sent:]
            except ssl.SSLError as e:
                print_error("SSLError:", e)
                time.sleep(0.1)
                continue
            except socket.error as e:
                if e[0] in (errno.EWOULDBLOCK,errno.EAGAIN):
                    print_error("EAGAIN: retrying")
                    time.sleep(0.1)
                    continue
                elif e[0] in ['timed out', 'The write operation timed out']:
                    print_error("socket timeout, retry")
                    time.sleep(0.1)
                    continue
                else:
                    traceback.print_exc(file=sys.stdout)
                    raise e



import Queue

class QueuePipe:

    def __init__(self, send_queue=None, get_queue=None):
        self.send_queue = send_queue if send_queue else Queue.Queue()
        self.get_queue = get_queue if get_queue else Queue.Queue()
        self.set_timeout(0.1)

    def get(self):
        try:
            return self.get_queue.get(timeout=self.timeout)
        except Queue.Empty:
            raise timeout

    def get_all(self):
        responses = []
        while True:
            try:
                r = self.get_queue.get_nowait()
                responses.append(r)
            except Queue.Empty:
                break
        return responses

    def set_timeout(self, t):
        self.timeout = t

    def send(self, request):
        self.send_queue.put(request)

    def send_all(self, requests):
        for request in requests:
            self.send(request)



class StoreDict(dict):

    def __init__(self, config, name):
        self.config = config
        self.path = os.path.join(self.config.path, name)
        self.load()

    def load(self):
        try:
            with open(self.path, 'r') as f:
                self.update(json.loads(f.read()))
        except:
            pass

    def save(self):
        with open(self.path, 'w') as f:
            s = json.dumps(self, indent=4, sort_keys=True)
            r = f.write(s)

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        self.save()

    def pop(self, key):
        if key in self.keys():
            dict.pop(self, key)
            self.save()




def check_www_dir(rdir):
    import urllib, urlparse, shutil, os
    if not os.path.exists(rdir):
        os.mkdir(rdir)
    index = os.path.join(rdir, 'index.html')
    if not os.path.exists(index):
        print_error("copying index.html")
        src = os.path.join(os.path.dirname(__file__), 'www', 'index.html')
        shutil.copy(src, index)
    files = [
        "https://code.jquery.com/jquery-1.9.1.min.js",
        "https://raw.githubusercontent.com/davidshimjs/qrcodejs/master/qrcode.js",
        "https://code.jquery.com/ui/1.10.3/jquery-ui.js",
        "https://code.jquery.com/ui/1.10.3/themes/smoothness/jquery-ui.css"
    ]
    for URL in files:
        path = urlparse.urlsplit(URL).path
        filename = os.path.basename(path)
        path = os.path.join(rdir, filename)
        if not os.path.exists(path):
            print_error("downloading ", URL)
            urllib.urlretrieve(URL, path)
