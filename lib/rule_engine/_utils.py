import datetime
import re


_sub_regex = r'[0-9]+([,.][0-9]+)?'
timedelta_regex = (
    r'P(?!\b)'
    r'(?P<weeks>' + _sub_regex + r'W)?'
    r'(?P<days>' + _sub_regex + r'D)?'
    r'(T'
    r'(?P<hours>' + _sub_regex + r'H)?'
    r'(?P<minutes>' + _sub_regex + r'M)?'
    r'(?P<seconds>' + _sub_regex + r'S)?'
    r')?'
)

def parse_timedelta(periodstring):
    if periodstring == "P":
        raise ValueError('empty timedelta string')

    match = re.match("^" + timedelta_regex + "$", periodstring)
    if not match:
        raise ValueError('invalid timedelta string')

    groups = match.groupdict()
    for key, val in groups.items():
        if val is None:
            val = "0n"
        groups[key] = float(val[:-1].replace(',', '.'))

    return datetime.timedelta(
        weeks=groups['weeks'],
        days=groups['days'],
        hours=groups['hours'],
        minutes=groups['minutes'],
        seconds=groups['seconds'],
    )
