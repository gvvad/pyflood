import socks
from urllib.parse import urlparse


class SockSocketEx(socks.socksocket):
    def set_url_proxy(self, _url: str):
        url = urlparse(_url)
        ptype = socks.PROXY_TYPE_HTTP
        paddr = url.hostname
        pport = None if url.port == "" else url.port
        puname = None if url.username == "" else url.username
        ppass = None if url.password == "" else url.password

        if url.scheme.lower() == "socks4":
            ptype = socks.PROXY_TYPE_SOCKS4
        elif url.scheme.lower() == "socks5":
            ptype = socks.PROXY_TYPE_SOCKS5

        self.set_proxy(proxy_type=ptype, addr=paddr, port=pport, username=puname, password=ppass)
