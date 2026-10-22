import math

def escape_field_key(value):
    return str(value).replace("\\", "\\\\").replace(" ", "\\ ").replace(",", "\\,").replace("=", "\\=")


def format_field_value(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return f"{value}i"
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"InfluxDB does not accept non-finite field values: {value}")
        return repr(value)
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    raise ValueError(f"Unsupported InfluxDB field value: {value!r}")


def to_line_protocol(frame_id, signals, table):
    tags = f"can_id=0x{frame_id:X}"
    fields = ",".join(
        f"{escape_field_key(name)}={format_field_value(value)}"
        for name, value in signals.items()
    )
    if not fields:
        raise ValueError("Decoded CAN frame contains no signals")
    return f"{table},{tags} {fields}\n"