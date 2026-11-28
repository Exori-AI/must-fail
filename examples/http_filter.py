"""http_filter.py: turn a filter that lives behind HTTP into a stdin command mustfail.py can run.

    python3 mustfail.py --refuse-codes 1 --cases my_cases.json \
      --cmd "python3 examples/http_filter.py --url http://localhost:8000/check --json-key text --field flagged"

Reads the text on stdin, POSTs it, reads one field of the JSON answer.
  exit 0  accept (field is falsy), prints the text back
  exit 1  refuse (field is truthy, or equals --block-value), prints nothing
  exit 3  error: connection refused, timeout, HTTP status >= 400, not JSON, field missing

Why exit 3 matters: the curl | grep line this replaces exits 0 when the service is down, so an outage
reads as "accepted everything". With --refuse-codes 1, mustfail.py scores rc 3 as an error that fails
the row on either side, so a dead service can't pass or fail cases quietly.

Standard library only. Headers via --header 'Name: value' (repeatable); keep keys out of shell history
by using --header-env NAME=ENVVAR, which reads the value from the environment.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def get_field(obj, path):
    for part in path.split("."):
        if isinstance(obj, list):
            obj = obj[int(part)]
        else:
            obj = obj[part]
    return obj


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--url", required=True)
    ap.add_argument("--json-key", default=None,
                    help="send {key: text} as JSON (default: send the raw text as the body)")
    ap.add_argument("--field", required=True, help="dotted path in the JSON answer, e.g. results.0.flagged")
    ap.add_argument("--block-value", default=None,
                    help="refuse when the field's string form equals this (default: refuse when truthy)")
    ap.add_argument("--header", action="append", default=[])
    ap.add_argument("--header-env", action="append", default=[])
    ap.add_argument("--timeout", type=float, default=15)
    a = ap.parse_args()

    text = sys.stdin.buffer.read()
    if a.json_key:
        body = json.dumps({a.json_key: text.decode("utf-8", "surrogateescape")}, ensure_ascii=True).encode()
        ctype = "application/json"
    else:
        body, ctype = text, "text/plain; charset=utf-8"
    req = urllib.request.Request(a.url, data=body, method="POST", headers={"Content-Type": ctype})
    for h in a.header:
        k, _, v = h.partition(":")
        req.add_header(k.strip(), v.strip())
    for h in a.header_env:
        k, _, env = h.partition("=")
        if env not in os.environ:
            print(f"http_filter: env {env} not set", file=sys.stderr)
            sys.exit(3)
        req.add_header(k.strip(), os.environ[env])

    try:
        with urllib.request.urlopen(req, timeout=a.timeout) as r:
            raw = r.read()
    except (urllib.error.URLError, OSError, ValueError) as e:
        print(f"http_filter: request failed: {e}", file=sys.stderr)
        sys.exit(3)
    try:
        value = get_field(json.loads(raw), a.field)
    except (ValueError, KeyError, IndexError, TypeError) as e:
        print(f"http_filter: no field {a.field!r} in answer ({type(e).__name__}): {raw[:200]!r}", file=sys.stderr)
        sys.exit(3)

    blocked = str(value) == a.block_value if a.block_value is not None else bool(value)
    if blocked:
        sys.exit(1)
    sys.stdout.buffer.write(text)


if __name__ == "__main__":
    main()
