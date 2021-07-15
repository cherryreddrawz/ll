# roblox-group-scanner-v2
Python 3 tool for finding unclaimed groups on Roblox. Supports multi-threading, multi-processing and HTTP proxies.

Unlike [roblox-group-scanner](https://github.com/h0nde/roblox-group-scanner), this tool uses the batch endpoint for group details, thus resulting in performance gains of up to 100x.

# Usage
```bash
python scanner.py -w 16 -r 1-11500000 -c 11000000 -u WEBHOOKURL
```

```
  -t THREADS, --threads THREADS
                        amount of threads per worker
  -w WORKERS, --workers WORKERS
                        amount of workers (processes)
  -r RANGE, --range RANGE
                        range of group ids to be scanned
  -c CUT_OFF, --cut-off CUT_OFF
                        group ids past this point won't be blacklisted based on their current validity status
  -p PROXY_FILE, --proxy-file PROXY_FILE
                        list of HTTP proxies, separated by newline
  -u WEBHOOK_URL, --webhook-url WEBHOOK_URL
                        found groups will be posted to this url
  --chunk-size CHUNK_SIZE
                        amount of groups to be sent per API request
  --get-funds GET_FUNDS
                        attempt to obtain amount of funds in a group
  --timeout TIMEOUT     timeout for server connections and responses
```
