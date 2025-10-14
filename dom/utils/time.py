import datetime


def format_datetime(date_str):
    """Convert datetime string to ISO 8601 format with timezone"""
    try:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    except ValueError:
        return date_str


def format_duration(duration_str):
    """Format duration to include milliseconds"""
    if "." not in duration_str:
        return duration_str + ".000"
    return duration_str
