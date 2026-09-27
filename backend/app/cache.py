import json
import time

from .tracking import _conn, init_db


def get(key):
    init_db()
    with _conn() as c:
        r = c.execute("SELECT value, expires FROM cache WHERE key=?", (key,)).fetchone()
    if r and r["expires"] > time.time():
        return json.loads(r["value"])
    return None

def set(key, value, ttl_s: int):
    with _conn() as c:
        c.execute("INSERT OR REPLACE INTO cache VALUES(?,?,?)",
                  (key, json.dumps(value), time.time() + ttl_s))
        