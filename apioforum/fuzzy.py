# fuzzy datetime things

units = (
    ("y", "year","years",365*24*60*60), # leap years aren't real
    ("d", "day","days",24*60*60),
    ("h", "hour","hours",60*60),
    ("m", "minute","minutes",60),
    ("s", "second","seconds",1),
)

from datetime import datetime, timedelta, timezone

def fuzzy(seconds, ago=False):
    if isinstance(seconds, timedelta):
        seconds = seconds.total_seconds()
    elif isinstance(seconds, datetime):
        seconds = (seconds.replace(tzinfo=timezone.utc) - datetime.now(tz=timezone.utc)).total_seconds()

    components_used = 0
    fmt = "{}"
    buf = ""
    if ago:
        fmt = "in {}" if seconds > 0 else "{} ago"
    elif seconds > 0: fmt = "in {}"
    seconds = abs(seconds)
    for short, _, _, unit_length in units:
        if seconds >= unit_length:
            components_used += 1
            qty = seconds // unit_length
            buf += str(int(qty)) + short
            seconds -= qty * unit_length
        if components_used == 2: break
    if not buf: return "now"

    return fmt.format(buf)
