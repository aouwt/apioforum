# fuzzy datetime things

times = (
    ("year","years",365*24*60*60), # leap years aren't real
    ("day","days",24*60*60),
    ("hour","hours",60*60),
    ("minute","minutes",60),
    ("second","seconds",1),
)

from datetime import datetime, timedelta 

def fuzzy(seconds,ago=True):
    if isinstance(seconds,timedelta):
        seconds = seconds.total_seconds()
    elif isinstance(seconds,datetime):
        seconds = (seconds-datetime.now()).total_seconds()

    fmt = "{}"
    if ago:
        fmt = "in {}" if seconds > 0 else "{} ago"
    seconds = abs(seconds)
    for t in times:
        if seconds >= t[2]:
            rounded = round((seconds / t[2])*100)/100
            if int(rounded) == rounded:
                rounded = int(rounded)
            if rounded == 1:
                word = t[0]
            else:
                word = t[1]
            return fmt.format(f'{rounded} {word}')
    else:
        return "now"
            
