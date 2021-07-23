from .utils import create_ssl_socket, shutdown_socket, make_embed, send_webhook
from zlib import decompress
try:
    from orjson import loads as json_loads
except ImportError:
    from json import loads as json_loads
import re

BATCH_GROUP_PATTERN = re.compile(b'{"id":(\d+),.{25}.+?,"owner":(.)')
BATCH_GROUP_REQUEST = (
    b"GET /v2/groups?groupIds=%b HTTP/1.1\n"
    b"Host:groups.roblox.com\n"
    b"Accept-Encoding:deflate\n"
    b"\n")
SINGLE_GROUP_REQUEST = (
    b"GET /v1/groups/%b HTTP/1.1\n"
    b"Host:groups.roblox.com\n"
    b"\n")
FUNDS_REQUEST = (
    b"GET /v1/groups/%b/currency HTTP/1.1\n"
    b"Host:economy.roblox.com\n"
    b"\n")

def thread_func(thread_num, worker_num, thread_barrier, thread_event,
                check_counter, ssl_context, proxy_iter,
                gid_ranges, gid_cutoff, gid_chunk_size,
                get_funds, webhook_url, timeout):
    gid_list = []
    for gid_range in gid_ranges:
        gid_list += list(map(lambda x: str(x).encode(), range(*gid_range)))
    gid_list_len = len(gid_list)
    gid_list_idx = 0
    gid_tracked = set()

    thread_barrier.wait()
    thread_event.wait()

    while True:
        proxy_addr = next(proxy_iter) if proxy_iter else None

        try:
            sock = create_ssl_socket(
                ("groups.roblox.com", 443),
                ssl_context=ssl_context,
                proxy_addr=proxy_addr,
                timeout=timeout)
        except:
            continue
        
        while True:
            if gid_chunk_size > gid_list_len:
                return

            gid_chunk = [
                gid_list[(gid_list_idx:=gid_list_idx+1) % gid_list_len]
                for _ in range(gid_chunk_size)
            ]

            try:
                # request batch group info
                sock.send(BATCH_GROUP_REQUEST % b",".join(gid_chunk))
                resp = sock.recv(1024 ** 2)
                if resp[:15] != b"HTTP/1.1 200 OK":
                    break
                resp = resp.partition(b"\r\n\r\n")[2]
                while resp[-1] != 0:
                    resp += sock.recv(1024 ** 2)
                owner_status = {
                    m[0]: m[1] == b"{"
                    for m in BATCH_GROUP_PATTERN.findall(decompress(resp, -15))
                }

                for gid in gid_chunk:
                    if not gid in owner_status:
                        # info for group wasn't included in response
                        if not gid_cutoff or gid_cutoff > int(gid):
                            # assume it's deleted and ignore it in future requests
                            gid_list.remove(gid)
                            gid_list_len -= 1
                        continue
                    
                    if not gid in gid_tracked:
                        if owner_status[gid]:
                            # group has an owner and this is our first time checking it
                            # add it as a tracked group
                            gid_tracked.add(gid)
                        else:
                            # group doesn't have an owner and this is only our first time checking it
                            # assume it's manual-approval/locked and ignore it in future requests
                            gid_list.remove(gid)
                            gid_list_len -= 1
                        continue

                    if owner_status[gid]:
                        # group has an owner and this is *not* our first time checking it
                        # skip to next group
                        continue

                    # group is tracked and doesn't have an owner
                    # request extra info and determine if it's claimable
                    sock.send(SINGLE_GROUP_REQUEST % gid)
                    resp = sock.recv(1024 ** 2)
                    if not resp.startswith(b"HTTP/1.1 200 OK"):
                        break
                    group_info = json_loads(resp.partition(b"\r\n\r\n")[2])

                    if not group_info["publicEntryAllowed"] \
                        or group_info["owner"] \
                        or "isLocked" in group_info:
                        # group is unclaimable
                        # ignore group in future requests
                        gid_list.remove(gid)
                        gid_list_len -= 1
                        continue

                    # get amount of funds in group
                    if get_funds:
                        funds_sock = create_ssl_socket(
                            ("economy.roblox.com", 443),
                            ssl_context=ssl_context,
                            proxy_addr=proxy_addr,
                            timeout=timeout)
                        try:
                            funds_sock.send(FUNDS_REQUEST % gid)
                            resp = funds_sock.recv(1024 ** 2)
                            if resp.startswith(b"HTTP/1.1 200 OK"):
                                group_info["funds"] = json_loads(resp)["robux"]
                            elif not b'"code":3,' in resp:
                                break
                        finally:
                            shutdown_socket(funds_sock)

                    # log group as claimable
                    print(" ~ ".join([
                        f"https://www.roblox.com/groups/{gid.decode()}",
                        f"{group_info['memberCount']} members",
                        (f"R$ {group_info['funds']}" if group_info.get("funds") is not None else '?') + " funds",
                        group_info["name"]
                    ]))

                    if webhook_url:
                        send_webhook(
                            webhook_url,
                            embeds=[make_embed(group_info)]
                        )

                    # ignore group in future requests
                    gid_list.remove(gid)
                    gid_list_len -= 1

                check_counter.add(gid_chunk_size)

            except KeyboardInterrupt:
                exit()
            
            except Exception as err:
                break
            
        shutdown_socket(sock)
