"""Encode and decode the OKTI text image format used by the supplied handout."""

from pathlib import Path

MAX_COLORS = 256
MAX_SHORT_RUN = 15
MAX_LONG_RUN = 255
DIFFERENCE_BIAS = 8


class OktiError(ValueError):
    """Raised when an OKTI or PPM input cannot be processed."""


def _remember(history, pixel):
    """Move pixel to the front of the unique-color history, capped at 256."""
    if pixel in history:
        history.remove(pixel)
    history.insert(0, pixel)
    del history[MAX_COLORS:]


def encode_pixels(width, height, pixels):
    """Return OKTI text for row-major RGB pixels; arguments are dimensions and RGB tuples."""
    if width <= 0 or height <= 0 or len(pixels) != width * height:
        raise OktiError("Image dimensions and pixel count do not match")
    if any(len(p) != 3 or any(c < 0 or c > 255 for c in p) for p in pixels):
        raise OktiError("Pixels must be RGB triples with components from 0 to 255")

    history = [(0, 0, 0)]
    previous = (0, 0, 0)
    output = ["okti", f"{width} {height}"]
    position = 0
    while position < len(pixels):
        pixel = pixels[position]
        repeat_count = 0
        while (position + repeat_count < len(pixels)
               and pixels[position + repeat_count] == previous):
            repeat_count += 1
        if pixel == previous and repeat_count:
            remaining = repeat_count
            while remaining:
                count = min(remaining, MAX_LONG_RUN)
                output.append(f"r{count:x}" if count <= MAX_SHORT_RUN else f"R{count:02x}")
                position += count
                remaining -= count
            _remember(history, pixel)
            continue

        if pixel in history:
            index = history.index(pixel)
            output.append(f"i{index:x}" if index < 16 else f"I{index:02x}")
        else:
            deltas = tuple(pixel[i] - previous[i] for i in range(3))
            if all(-DIFFERENCE_BIAS <= delta < DIFFERENCE_BIAS for delta in deltas):
                output.append("d" + "".join(f"{delta + DIFFERENCE_BIAS:x}" for delta in deltas))
            else:
                output.append("p" + "".join(f"{component:02x}" for component in pixel))
        _remember(history, pixel)
        previous = pixel
        position += 1
    return "\n".join(output) + "\n"


def _tokens_with_lines(data):
    """Yield fixed-width pixel tokens and their source line numbers from OKTI data."""
    line_number = 3
    index = 0
    widths = {"p": 7, "d": 4, "r": 2, "R": 3, "i": 2, "I": 3}
    while index < len(data):
        char = data[index]
        if char in "\r\n":
            if char == "\n" or (char == "\r" and (index + 1 == len(data) or data[index + 1] != "\n")):
                line_number += 1
            index += 1
        elif char in widths:
            width = widths[char]
            end = index + width
            token = data[index:end]
            if len(token) != width or "\n" in token or "\r" in token:
                raise OktiError(f"Incomplete pixel token on line {line_number}: {token!r}")
            yield token, line_number
            index = end
        else:
            end = index + 1
            while end < len(data) and data[end] not in "\r\n":
                end += 1
            raise OktiError(f"Invalid pixel type on line {line_number}: {data[index:end]!r}")


def decode_okti(text):
    """Decode OKTI text into (width, height, row-major RGB tuples)."""
    lines = text.splitlines(keepends=True)
    first = lines[0].rstrip("\r\n") if lines else ""
    if first != "okti":
        raise OktiError(f"Not an OKTI file; first line is {first!r}")
    dimension_line = lines[1].rstrip("\r\n") if len(lines) > 1 else ""
    parts = dimension_line.split()
    try:
        if len(parts) != 2:
            raise ValueError
        width, height = map(int, parts)
    except ValueError as exc:
        raise OktiError(f"Invalid image dimensions: {dimension_line!r}") from exc
    if width <= 0 or height <= 0:
        raise OktiError(f"Invalid image dimensions: {dimension_line!r}")

    data = "".join(lines[2:])
    pixels = []
    history = [(0, 0, 0)]
    previous = (0, 0, 0)
    for token, line_number in _tokens_with_lines(data):
        kind = token[0]
        try:
            if kind == "p":
                pixel = tuple(int(token[offset:offset + 2], 16) for offset in (1, 3, 5))
                pixels.append(pixel)
                _remember(history, pixel)
                previous = pixel
            elif kind == "d":
                pixel = tuple(previous[i] + int(token[i + 1], 16) - DIFFERENCE_BIAS for i in range(3))
                if any(component < 0 or component > 255 for component in pixel):
                    raise OktiError(f"Difference produces an invalid RGB value on line {line_number}")
                pixels.append(pixel)
                _remember(history, pixel)
                previous = pixel
            elif kind in "rR":
                count = int(token[1:], 16)
                if count < 1:
                    raise OktiError(f"Run length must be positive on line {line_number}")
                pixels.extend([previous] * count)
                _remember(history, previous)
            else:
                color_index = int(token[1:], 16)
                pixel = history[color_index]
                pixels.append(pixel)
                _remember(history, pixel)
                previous = pixel
        except (IndexError, ValueError) as exc:
            if isinstance(exc, OktiError):
                raise
            raise OktiError(f"Invalid pixel data on line {line_number}: {token!r}") from exc
        if len(pixels) > width * height:
            raise OktiError(f"Pixel count exceeds dimensions at line {line_number}")
    if len(pixels) != width * height:
        raise OktiError(f"Expected {width * height} pixels but decoded {len(pixels)}")
    return width, height, pixels


def read_ppm(path):
    """Read an 8-bit P3 or P6 PPM and return (width, height, row-major RGB tuples)."""
    raw = Path(path).read_bytes()
    tokens = []
    cursor = 0
    while len(tokens) < 4:
        while cursor < len(raw) and chr(raw[cursor]).isspace():
            cursor += 1
        if cursor < len(raw) and raw[cursor] == ord("#"):
            while cursor < len(raw) and raw[cursor] not in (10, 13):
                cursor += 1
        else:
            start = cursor
            while cursor < len(raw) and not chr(raw[cursor]).isspace() and raw[cursor] != ord("#"):
                cursor += 1
            if start == cursor:
                raise OktiError("Invalid PPM header")
            tokens.append(raw[start:cursor].decode("ascii"))
    magic, width_text, height_text, maximum_text = tokens
    try:
        width, height, maximum = int(width_text), int(height_text), int(maximum_text)
    except ValueError as exc:
        raise OktiError("Invalid PPM dimensions or maximum channel value") from exc
    if magic not in ("P3", "P6") or width <= 0 or height <= 0 or maximum != 255:
        raise OktiError("Only positive-size 8-bit P3/P6 PPM files are supported")
    count = width * height * 3
    if magic == "P6":
        if cursor >= len(raw) or not chr(raw[cursor]).isspace():
            raise OktiError("PPM header is missing its pixel-data separator")
        if raw[cursor] == 13 and cursor + 1 < len(raw) and raw[cursor + 1] == 10:
            cursor += 2
        else:
            cursor += 1
        samples = raw[cursor:cursor + count]
        if len(samples) != count:
            raise OktiError("PPM pixel data is truncated")
        values = list(samples)
    else:
        while cursor < len(raw) and chr(raw[cursor]).isspace():
            cursor += 1
        text = raw[cursor:].decode("ascii")
        clean = "\n".join(line.split("#", 1)[0] for line in text.splitlines())
        try:
            values = [int(value) for value in clean.split()]
        except ValueError as exc:
            raise OktiError("Invalid P3 pixel value") from exc
        if len(values) != count or any(value < 0 or value > 255 for value in values):
            raise OktiError("P3 pixel count or channel value is invalid")
    return width, height, [tuple(values[i:i + 3]) for i in range(0, count, 3)]


def write_ppm(path, width, height, pixels):
    """Write RGB pixels to a binary P6 PPM file."""
    if len(pixels) != width * height:
        raise OktiError("Pixel count does not match output dimensions")
    header = f"P6\n{width} {height}\n255\n".encode("ascii")
    body = bytes(component for pixel in pixels for component in pixel)
    Path(path).write_bytes(header + body)

