# roblox-group-scanner-v2
Python 3 tool for finding unclaimed groups on Roblox. Supports multi-threading, multi-processing and HTTP proxies.

Unlike [roblox-group-scanner](https://github.com/h0nde/roblox-group-scanner), this tool uses the batch endpoint for group details, thus resulting in performance increases of up to 100x.

# Usage
```bash
python scanner.py -w 16 -r 1-11500000 -c 11000000 -p proxies.txt -u WEBHOOKURL
```

```
usage: scanner.py [-h] [-t THREADS] [-w WORKERS] -r RANGE [-c CUT_OFF] [-p PROXY_FILE] [-u WEBHOOK_URL]
                  [--chunk-size CHUNK_SIZE] [--timeout TIMEOUT]

optional arguments:
  -h, --help            show this help message and exit
  -t THREADS, --threads THREADS
                        Amount of threads to be created per worker
  -w WORKERS, --workers WORKERS
                        Amount of processes to be created
  -r RANGE, --range RANGE
                        Range of group ids to be scanned
  -c CUT_OFF, --cut-off CUT_OFF
                        Group ids past this point won't be blacklisted based on their current validity status
  -p PROXY_FILE, --proxy-file PROXY_FILE
                        List of HTTP proxies, separated by newline
  -u WEBHOOK_URL, --webhook-url WEBHOOK_URL
                        Found groups will be posted to the specified webhook URL
  --chunk-size CHUNK_SIZE
                        Amount of groups to be sent per API request
  --timeout TIMEOUT     Timeout for server connections and responses
```
