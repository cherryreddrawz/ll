from .utils import create_ssl_socket, shutdown_socket, make_embed, send_webhook
from zlib import decompress
from itertools import cycle
try:
    from orjson import loads as json_loads
except ImportError:
    from json import loads as json_loads

GROUP_IGNORED = 0
GROUP_TRACKED = 1

def thread_func(thread_num, worker_num, thread_barrier, thread_event,
                check_counter, ssl_context, proxy_iter,
                gid_range, gid_cutoff, gid_chunk_size,
                get_funds, webhook_url, timeout):
    gid_iter = cycle(range(*gid_range))
    gid_count = gid_range[1] - gid_range[0]
    gid_cache = {}
    gid_chunk = None

    thread_barrier.wait()
    thread_event.wait()

    while True:
        try:
            proxy_addr = next(proxy_iter)
        except StopIteration:
            proxy_addr = None

        try:
            sock = create_ssl_socket(
                ("groups.roblox.com", 443),
                ssl_context=ssl_context,
                proxy_addr=proxy_addr,
                timeout=timeout)
        except:
            continue
        
        while True:
            if not gid_chunk:
                if gid_chunk_size > gid_count:
                    # no more un-ignored groups left to scan
                    # kill thread
                    return
                
                gid_chunk = []
                while gid_chunk_size > len(gid_chunk):
                    gid = next(gid_iter)
                    if gid_cache.get(gid) != GROUP_IGNORED:
                        gid_chunk.append(gid)

            try:
                # request bulk group info
                sock.send(f"GET /v2/groups?groupIds={','.join(map(str, gid_chunk))} HTTP/1.1\n"
                           "Host:groups.roblox.com\n"
                           "Accept-Encoding:deflate\n"
                           "\n".encode())
                resp = sock.recv(1024 ** 2)
                if not resp.startswith(b"HTTP/1.1 200 OK"):
                    break
                resp = resp.split(b"\r\n\r\n", 1)[1]
                while resp[-1] != 0:
                    resp += sock.recv(1024 ** 2)
                group_assoc = {
                    x["id"]: x
                    for x in json_loads(decompress(resp, -15)[8:-1])
                }

                for gid in gid_chunk:
                    group_status = gid_cache.get(gid)
                    group_info = group_assoc.get(gid)

                    if group_status == GROUP_IGNORED:
                        continue
                    
                    if not group_info:
                        # info for group wasn't included in response
                        if not gid_cutoff or gid_cutoff > gid:
                            # assume it's deleted and ignore it in future requests
                            gid_cache[gid] = GROUP_IGNORED
                            gid_count -= 1
                        continue
                    
                    if not group_status:
                        if group_info["owner"]:
                            # group has an owner and this is our first time checking it
                            # add it as a tracked group
                            gid_cache[gid] = GROUP_TRACKED
                        else:
                            # group doesn't have an owner and this is only our first time checking it
                            # assume it's manual-approval/locked and ignore it in future requests
                            gid_cache[gid] = GROUP_IGNORED
                            gid_count -= 1
                        continue

                    if group_info["owner"]:
                        # group has an owner and this is *not* our first time checking it
                        # skip to next group
                        continue
                    
                    # group doesn't have an owner, but it did when we last checked
                    # request extra info and determine if it's claimable
                    sock.send(f"GET /v1/groups/{gid} HTTP/1.1\n"
                               "Host:groups.roblox.com\n"
                               "\n".encode())
                    resp = sock.recv(1024**2)
                    if not resp.startswith(b"HTTP/1.1 200 OK"):
                        break
                    group_info = json_loads(resp.split(b"\r\n\r\n", 1)[1])

                    if not group_info["publicEntryAllowed"] \
                        or group_info["owner"] \
                        or "isLocked" in group_info:
                        # group is unclaimable
                        # ignore group in future requests
                        gid_cache[gid] = GROUP_IGNORED
                        gid_count -= 1
                        continue

                    # get amount of funds in group
                    if get_funds:
                        funds_sock = create_ssl_socket(
                            ("economy.roblox.com", 443),
                            ssl_context=ssl_context,
                            proxy_addr=proxy_addr,
                            timeout=timeout)
                        try:
                            funds_sock.send(f"GET /v1/groups/{group_info['id']}/currency HTTP/1.1\n"
                                            "Host:economy.roblox.com\n"
                                            "\n".encode())
                            resp = funds_sock.recv(1024**2)
                            if resp.startswith(b"HTTP/1.1 200 OK"):
                                group_info["funds"] = json_loads(resp.split(b"\r\n\r\n", 1)[1])["robux"]
                            elif not b'"code":3,' in resp:
                                break
                        finally:
                            shutdown_socket(funds_sock)

                    # log group as claimable
                    print(" ~ ".join([
                        f"https://www.roblox.com/groups/{gid}",
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
                    gid_cache[gid] = GROUP_IGNORED
                    gid_count -= 1

                check_counter.add(len(gid_chunk))
                gid_chunk = None

            except KeyboardInterrupt:
                exit()
            
            except Exception as err:
                break
            
        shutdown_socket(sock)