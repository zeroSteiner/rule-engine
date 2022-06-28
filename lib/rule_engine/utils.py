import datetime
import re


_sub_regex = r'[0-9]+([,.][0-9]+)?'
timedelta_regex = (
    r'P(?!\b)'
    f'(?P<weeks>{_sub_regex}W)?'
    f'(?P<days>{_sub_regex}D)?'
    r'(T'
    f'(?P<hours>{_sub_regex}H)?'
    f'(?P<minutes>{_sub_regex}M)?'
    f'(?P<seconds>{_sub_regex}S)?'
    r')?'
)
timedelta_re = re.compile(f"^{timedelta_regex}$")

def parse_timedelta(periodstring):
    if periodstring == "P":
        raise ValueError('empty timedelta string')

    match = timedelta_re.match(periodstring)
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
