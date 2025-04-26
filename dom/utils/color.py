import re
import webcolors


def get_hex_color(value: str) -> str:
    value = value.strip().lower()
    if value.startswith('#'):
        if re.fullmatch(r'#([0-9a-f]{6})', value):
            return value
        else:
            raise ValueError(f"Invalid hex color: {value}")
    try:
        return webcolors.name_to_hex(value)
    except ValueError:
        raise ValueError(f"Unknown color name: {value}")
