# Student name: [吴彦贝uu]
# Student ID: [202600242]
# Description: encode PPM images as OKTI text and decode OKTI text to PPM.
"""OKTI image utility: encode a PPM image or decode an OKTI file."""

import sys
from pathlib import Path

from okti_codec import OktiError, decode_okti, encode_pixels, read_ppm, write_ppm


def show_image(path, title):
    """Display a PPM path with a title; return a display error string, or None on success."""
    try:
        import tkinter as tk
    except ImportError as error:
        return str(error)
    root = None
    try:
        root = tk.Tk()
        root.title(title)
        image = tk.PhotoImage(file=str(path))
        label = tk.Label(root, image=image)
        label.image = image
        label.pack()
        root.mainloop()
    except tk.TclError as error:
        if root is not None:
            root.destroy()
        return str(error)
    return None


def encode_command(image_path):
    """Encode a PPM path to output.okti and display it; returns nothing."""
    width, height, pixels = read_ppm(image_path)
    output_path = Path("output.okti")
    encoded_text = encode_pixels(width, height, pixels)
    output_path.write_text(encoded_text, encoding="ascii", newline="\n")
    input_size = Path(image_path).stat().st_size
    output_size = output_path.stat().st_size
    saved = input_size - output_size
    percentage = saved * 100 / input_size if input_size else 0.0
    print(f"Encoded {width}x{height} image to {output_path.resolve()}")
    print(f"Size: {input_size} -> {output_size} bytes; change: {saved:+d} bytes ({percentage:+.2f}%)")
    display_error = show_image(image_path, f"Input image: {image_path}")
    if display_error:
        print(f"Image display unavailable: {display_error}")


def decode_command(okti_path, output_path):
    """Decode an OKTI file to PPM and display it; arguments are input and output paths."""
    text = Path(okti_path).read_text(encoding="ascii")
    width, height, pixels = decode_okti(text)
    write_ppm(output_path, width, height, pixels)
    print(f"Decoded {width}x{height} image to {Path(output_path).resolve()}")
    display_error = show_image(output_path, f"Decoded image: {output_path}")
    if display_error:
        print(f"Image display unavailable: {display_error}")


def main(arguments=None):
    """Dispatch command-line or prompted input; argument is argv without program name."""
    if arguments is None:
        arguments = sys.argv[1:]
    try:
        if arguments and arguments[0] == "--decode":
            if len(arguments) not in (2, 3):
                raise OktiError("Usage: python main.py --decode INPUT.okti [OUTPUT.ppm]")
            decode_command(arguments[1], arguments[2] if len(arguments) == 3 else "decoded.ppm")
        else:
            if len(arguments) > 1:
                raise OktiError("Too many command line arguments; provide one PPM image path")
            image_path = arguments[0] if arguments else input("PPM image file: ").strip()
            encode_command(image_path)
    except (OktiError, OSError, UnicodeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
