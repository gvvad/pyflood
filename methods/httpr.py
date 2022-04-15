from . import BaseMethod
import requests


class Method(BaseMethod):
    def __init__(self, params: dict):
        super().__init__(params)
        if self.params["Port"] is None:
            self.params["Port"] = 443 if self.url.scheme == "https" else 80

    def worker(self):
        rpc = self.params["RPC"]

        while not self.is_terminate:
            s = requests.Session()
            if self.params.get("Proxy"):
                p = self.params["Proxy"]
                s.proxies.update({"http": p, "https": p})

            headers = self.params["Headers"]
            timeout = self.params["Timeout"]

            try:
                for _ in range(0, rpc):
                    if self.is_terminate:
                        break
                    self.throttle()

                    self.total_sent_count += 1
                    res = s.get(url=self.params["Url"],
                                timeout=timeout, headers=headers)
                    if res.status_code == 200:
                        self.put_to_receive_queue(res)

            except (OSError, IOError) as e:
                self.last_error = e
                self.total_failed_count += 1
