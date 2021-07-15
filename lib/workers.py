from .threads import thread_func
from .utils import ChunkCounter, set_cpu_affinity, slice_range
from multiprocessing import cpu_count
import threading
import itertools
import ssl
import time

def worker_func(worker_num, worker_barrier, thread_count,
                count_queue,
                proxy_list,
                gid_ranges,
                **thread_kwargs):
    set_cpu_affinity(worker_num % cpu_count())
    
    check_counter = ChunkCounter()
    proxy_iter = itertools.cycle(proxy_list) if proxy_list else None
    ssl_context = ssl.create_default_context()

    thread_barrier = threading.Barrier(thread_count + 1)
    thread_event = threading.Event()
    threads = []

    for num in range(thread_count):
        thread = threading.Thread(
            target=thread_func,
            name=f"Scanner-{num}",
            daemon=True,
            kwargs=dict(
                thread_num=num,
                worker_num=worker_num,
                thread_barrier=thread_barrier,
                thread_event=thread_event,
                check_counter=check_counter,
                ssl_context=ssl_context,
                proxy_iter=proxy_iter,
                gid_ranges=[
                    slice_range(gid_range, num, thread_count)
                    for gid_range in gid_ranges
                ],
                **thread_kwargs
            )
        )
        threads.append(thread)
    
    for thread in threads:
        thread.start()
    thread_barrier.wait()
    worker_barrier.wait()
    thread_event.set()
    
    try:
        while any(t.is_alive() for t in threads):
            count_queue.put((time.time(), check_counter.wait(1)))
    except KeyboardInterrupt:
        pass