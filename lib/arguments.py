from multiprocessing import cpu_count
import argparse

def parse_human_int(s):
    if s[-1] == "m":
        s = int(float(s[:-1]) * 1000000)
    else:
        s = int(s)
    return s

def parse_range(range_string):
    fields = tuple(map(parse_human_int, range_string.split("-", 1)))
    return fields

def get_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--threads", type=int, default=50, help="amount of threads per worker")
    parser.add_argument("-w", "--workers", type=int, default=cpu_count(), help="amount of workers (processes)")
    parser.add_argument("-r", "--range", type=parse_range, required=True, nargs="+", help="range of group ids to be scanned")
    parser.add_argument("-c", "--cut-off", type=parse_human_int, help="group ids past this point won't be blacklisted based on their current validity status")
    parser.add_argument("-p", "--proxy-file", type=argparse.FileType("r", encoding="UTF-8", errors="ignore"), help="list of HTTP proxies, separated by newline")
    parser.add_argument("-u", "--webhook-url", type=str, help="found groups will be posted to this url")
    parser.add_argument("--get-funds", type=int, default=1, help="attempt to obtain amount of funds in a group")
    parser.add_argument("--chunk-size", type=int, default=100, help="amount of groups to be sent per API request")
    parser.add_argument("--timeout", type=float, default=5.0, help="timeout for server connections and responses")
    arguments = parser.parse_args()
    return arguments