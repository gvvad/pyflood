import socket
from threading import Thread, Event
from queue import *
from time import time, sleep
from socket import socket, gethostbyname_ex, SHUT_RD
from ssl import SSLSocket
from urllib.parse import urlparse
from http.client import HTTPResponse
from random import randint, choices
from tool import string_render
from importlib import import_module
import re
import string
import gzip
import zlib

RND_RE = re.compile("RndStr([0-9]+)")


class ParamDict(dict):
    def __init__(self, obj) -> None:
        super().__init__(obj)
        self.user_mappers = {}

    def __getitem__(self, key):
        if key in self.user_mappers:
            return self.user_mappers[key][0](self.user_mappers[key][1] or self)

        re_res = RND_RE.search(key)
        if re_res:
            n = int(re_res[1])
            return ''.join(choices(string.ascii_lowercase + string.digits, k=n))

        obj = self.obj_expander(self.get(key))

        if key == "Cookie":
            if type(obj) is dict:
                return "; ".join([f"{key}={val}" for key, val in obj.items()])
            if type(obj) is str:
                return obj

        return obj

    def set_custom_mapper(self, key: str, mapper: callable, scope=None):
        self.user_mappers[key] = (mapper, scope)

    def obj_expander(self, obj):
        if type(obj) is list:
            return self.obj_expander(obj[randint(0, len(obj)-1)])

        if type(obj) is dict:
            res = {}
            for key, val in obj.items():
                try:
                    res[key] = self.obj_expander(val)
                except KeyError:
                    continue
            return res

        if type(obj) is str and obj.find("{") != -1:
            return string_render(obj, self, self.__getitem__)

        return obj


class ReceiveThread(Thread):
    def __init__(self, receive_queue: Queue):
        super().__init__()
        self.queue = receive_queue
        self.received = 0
        self.terminate_event = Event()
        self._last_receive = None

    def run(self) -> None:
        while not self.is_terminate:
            resp = self.queue.get()

            if resp is None:
                break
            if type(resp) in (socket, SSLSocket):
                try:
                    while not self.is_terminate:
                        b = resp.recv(1024 * 4)
                        if len(b):
                            self.received += len(b)
                            self._last_receive = b
                        else:
                            break
                    resp.shutdown(SHUT_RD)
                except (OSError, IOError):
                    self._last_receive = None
                continue

            if type(resp) is HTTPResponse:
                if resp.status == 200:
                    try:
                        b = resp.read()
                        self.received += len(b)
                        self._last_receive = b
                    except (OSError, IOError):
                        self._last_receive = None
                    resp.close()
                continue

            if hasattr(resp, "content"):
                self._last_receive = resp.content
                self.received += len(self._last_receive)
                continue

    @staticmethod
    def decode_bytes(buf: bytes, trunc=32):
        try:
            _b = buf
            if _b[:2] == b'\x1F\x8B':
                _b = gzip.decompress(_b)
            
            if _b[:2] == b'\x78\x9C' or _b[:2] == b'\x78\x01' or _b[:2] == b'\x78\xDA':
                _b = zlib.decompress(_b)
                
            s = _b[:trunc].decode().split("\n")[0].strip()
            return f"[Received {len(_b)} bytes: {s}...]"
        except (UnicodeDecodeError, gzip.BadGzipFile, zlib.error):
            return f"[Can't decode {len(buf)} bytes.]"

    @property
    def last_receive(self):
        if self._last_receive:
            return self.decode_bytes(self._last_receive)
        return None

    @property
    def is_terminate(self):
        return self.terminate_event.is_set()

    def terminate(self):
        self.queue.put_nowait(None)
        self.terminate_event.set()


class BaseMethod(Thread):
    def __init__(self, params: dict):
        super().__init__()
        self.params = ParamDict(params)

        self.url = urlparse(self.params.get("Url") or "/")

        if not self.params.get("Ip"):
            a, b, c = gethostbyname_ex(self.params["Host"])
            self.params["Ip"] = c

        self.throttle_value = int(self.params.get("Throttle"))

        self.terminate_event = Event()
        self.total_sent = 0
        self.total_sent_count = 0

        self.total_failed_count = 0

        self.sent_timestamp = time()
        self.sent_point = 0
        self.sent_count_timestamp = time()
        self.sent_count_point = 0

        self.throttle_count = 0

        self.receive_queue = Queue()
        self.receive_thread = ReceiveThread(self.receive_queue)
        self.no_receive = self.params.get("NoReceive")

        if not self.params.get("Path"):
            self.params["Path"] = self.url.path or "/"

        self._last_e = None

        self.SockSocketEx = None

    @staticmethod
    def calc_rate(timestamp, old_value, new_value):
        now = time()
        try:
            return (new_value - old_value) / (now - timestamp), now, new_value
        except ZeroDivisionError:
            return 0, now, new_value

    def worker(self):
        """ Virtual method """
        raise NotImplemented()

    def run(self) -> None:
        try:
            self.worker()
        finally:
            print(f"Job [{self.params['Host']}] terminated.")
            self.receive_thread.terminate()

    def start(self) -> None:
        if not self.no_receive:
            self.receive_thread.start()
        super(BaseMethod, self).start()

    def create_socket(self, *args):
        try:
            if self.params.get("Proxy"):
                if self.SockSocketEx is None:
                    self.SockSocketEx = import_module("socksocketex").SockSocketEx
                s = self.SockSocketEx(*args)
                s.set_url_proxy(self.params["Proxy"])
                return s
        except Exception as e:
            print(e)
            pass
        return socket(*args)

    def send_to_socket(self, s, data):
        self.total_sent_count += 1
        s.sendall(data)
        self.total_sent += len(data)
        self.last_error = None

        # msg_len = len(data)
        # sended = 0
        # while sended < msg_len:
        #     self.total_sent_count += 1
        #     sent = s.send(data[sended:])
        #     if sent == 0:
        #         return False
        #     sended += sent
        #     self.total_sent += sent
        #
        # self.last_error = None
        # return True

    def put_to_receive_queue(self, obj):
        if self.receive_queue.qsize() < 10 and not self.no_receive:
            self.receive_queue.put(obj)
        else:
            try:
                if type(obj) in (socket, SSLSocket):
                    obj.shutdown(SHUT_RD)
                elif type(obj) is HTTPResponse:
                    obj.close()
            except (OSError, IOError):
                pass

    def throttle(self):
        if self.throttle_value == 0:
            return
        self.throttle_count += 1
        if (self.throttle_value - self.throttle_count) <= 0:
            self.throttle_count = 0
            sleep(0.1)

    @property
    def last_error(self):
        if self._last_e:
            return self._last_e
        return self.receive_thread.last_receive

    @last_error.setter
    def last_error(self, value=None):
        self._last_e = value

    @property
    def is_terminate(self):
        return self.terminate_event.is_set()

    def terminate(self):
        self.terminate_event.set()

    @property
    def sent_bytes(self):
        return self.total_sent

    @property
    def sent_rate(self):
        res, self.sent_timestamp, self.sent_point = \
            self.calc_rate(self.sent_timestamp, self.sent_point, self.sent_bytes)
        return res

    @property
    def sent_count(self):
        return self.total_sent_count

    @property
    def sent_count_rate(self):
        res, self.sent_count_timestamp, self.sent_count_point = \
            self.calc_rate(self.sent_count_timestamp, self.sent_count_point, self.sent_count)
        return res

    @property
    def received_bytes(self):
        return self.receive_thread.received

    @property
    def failed_count(self):
        return self.total_failed_count
