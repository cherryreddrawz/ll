from .utils import create_ssl_socket, shutdown_socket, make_embed, send_webhook
try:
    import orjson as json
except ImportError:
    import json

GROUP_IGNORED = 0
GROUP_TRACKED = 1

def thread_func(thread_num, worker_num, thread_barrier, thread_event,
                check_counter, ssl_context, proxy_iter,
                gid_iter, gid_cutoff, gid_cache, gid_chunk_size,
                webhook_url, timeout):
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
                gid_chunk = []
                while gid_chunk_size > len(gid_chunk):
                    gid = next(gid_iter)
                    if gid_cache.get(gid) == GROUP_IGNORED:
                        continue
                    gid_chunk.append(gid)

            try:
                # request bulk group info
                sock.send(f"GET /v2/groups?groupIds={','.join(map(str, gid_chunk))} HTTP/1.1\n"
                           "Host:groups.roblox.com\n"
                           "\n".encode())
                resp = sock.recv(1024 ** 2)
                if not resp.startswith(b"HTTP/1.1 200 OK"):
                    raise ConnectionAbortedError(
                        f"Unexpected response while requesting group details: {resp[:64]}")
                expected_length = int(resp.split(b"content-length:", 1)[1].split(b"\r", 1)[0].strip())
                resp = resp.split(b"\r\n\r\n", 1)[1]
                while expected_length > len(resp):
                    resp += sock.recv(1024 ** 2)
                resp = {x["id"]: x for x in json.loads(resp)["data"]}
                
                for gid in gid_chunk:
                    group_status = gid_cache.get(gid)
                    group_info = resp.get(gid)

                    if group_status == GROUP_IGNORED:
                        continue
                    
                    if not group_info and (not gid_cutoff or gid_cutoff > gid):
                        # info for group wasn't included in response
                        # assume it's deleted and ignore it in future requests
                        gid_cache[gid] = GROUP_IGNORED
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
                        raise ConnectionAbortedError(
                            f"Unexpected response while requesting extra group details: {resp[:64]}")
                    group_info = json.loads(resp.split(b"\r\n\r\n", 1)[1])

                    if group_info["owner"]:
                        # groups shouldn't switch owners in such a short amount of time
                        # assume group is bugged and ignore it in future reequests
                        gid_cache[gid] = GROUP_IGNORED
                        continue

                    if group_info.get("isLocked"):
                        # group is locked
                        # ignore it in future requests
                        gid_cache[gid] = GROUP_IGNORED
                        continue
                    
                    if not group_info["publicEntryAllowed"]:
                        # group requires manual approval for each join request
                        # ignore it in future requests
                        gid_cache[gid] = GROUP_IGNORED
                        continue

                    print(group_info)

                    # get amount of funds in group
                    funds_sock = create_ssl_socket(
                        ("economy.roblox.com", 443),
                        ssl_context=ssl_context,
                        proxy_addr=proxy_addr,
                        timeout=timeout)
                    try:
                        funds_sock.send(f"GET /v1/groups/{group_info['id']}/currency HTTP/1.1\n"
                                         "Host:economy.roblox.com\n"
                                         "\r\n".encode())
                        resp = funds_sock.recv(1024**2)
                        if not resp.startswith(b"HTTP/1.1 200 OK") and not b'"code":3,' in resp:
                            raise ConnectionAbortedError(
                                f"Unexpected response while requesting group fund details: {resp[:64]}")
                        group_info["funds"] = json.loads(resp.split(b"\r\n\r\n", 1)[1]).get("robux")
                    except Exception as err:
                        print("fund thing", err)
                        raise
                    finally:
                        shutdown_socket(funds_sock)

                    # log group as claimable
                    print(" ~ ".join([
                        group_info["name"],
                        f"{group_info['memberCount']} members",
                        (f"R$ {group_info['funds']}" if group_info["funds"] is not None else '?') + " funds",
                        f"https://www.roblox.com/groups/{gid}"
                    ]))

                    if webhook_url:
                        send_webhook(
                            webhook_url,
                            embeds=[make_embed(group_info)])

                    # ignore group in future requests
                    gid_cache[gid] = GROUP_IGNORED

                check_counter.add(len(gid_chunk))
                gid_chunk = None

            except KeyboardInterrupt:
                exit()
            
            except Exception as err:
                print(f"{err!r}")
                break
            
        shutdown_socket(sock)