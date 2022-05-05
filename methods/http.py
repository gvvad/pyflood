from . import BaseMethod
from socket import AF_INET, SOCK_STREAM, SHUT_WR
import ssl


class Method(BaseMethod):
    def __init__(self, params: dict):
        super().__init__(params)
        if self.params["Port"] is None:
            self.params["Port"] = 443 if self.url.scheme == "https" else 80

        self.params.set_custom_mapper("CookieSub", self.cookie_sub)

    @staticmethod
    def cookie_sub(scope):
        if scope.get("Cookie"):
            return f"\r\nCookie: {scope['Cookie']}"
        return ""

    def worker(self):
        is_ssl = self.url.scheme == "https"
        context = ssl.create_default_context()
        rpc = self.params["RPC"]

        while not self.is_terminate:
            s = self.create_socket(AF_INET, SOCK_STREAM)
            s.settimeout(self.params["Timeout"])

            try:
                s.connect((self.params["Ip"], self.params["Port"]))
                if is_ssl:
                    s = context.wrap_socket(s, server_hostname=self.params["Host"])
                self.put_to_receive_queue(s)

                for _ in range(0, rpc):
                    if self.is_terminate:
                        break
                    self.throttle()
                    data = self.params["Message"].encode(encoding="raw_unicode_escape")

                    self.send_to_socket(s, data)
                s.shutdown(SHUT_WR)
            except (OSError, IOError) as e:
                self.last_error = e
                self.total_failed_count += 1
