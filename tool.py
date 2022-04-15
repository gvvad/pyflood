import re


def humanize_bytes(num):
    base = 1024.0
    units = ["b", "Kib", "Mib", "Gib"]
    for unit in units:
        if num < base:
            return f"{num:.2f}{unit}"
        num /= base
    return f"{num:.2f}{units[-1]}"


str_re_pattern = re.compile("{(.+?)}")


def string_render(template: str, variants: dict, mapper=None):
    keys = str_re_pattern.findall(template)
    if keys:
        buf = {}
        for key in keys:
            if mapper:
                b = mapper(key)
                if b is None:
                    raise KeyError(key)
                buf[key] = b
            else:
                buf[key] = variants[key]

        return template.format(**buf)

    return template
