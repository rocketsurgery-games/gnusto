"""
Terminal image display using Kitty graphics protocol.

Supports displaying images inline in terminals that support the protocol:
- Kitty
- iTerm2 (via iTerm2 image protocol)
- WezTerm
- Ghostty

Usage:
    from gnusto.terminal_images import display_image, is_supported

    if is_supported():
        display_image("path/to/image.png", width=40)  # 40 columns wide
"""

import base64
import io
import os
import sys
from pathlib import Path
from typing import Literal

# Terminal type detection
_TERM = os.environ.get("TERM", "")
_TERM_PROGRAM = os.environ.get("TERM_PROGRAM", "")
_KITTY_WINDOW_ID = os.environ.get("KITTY_WINDOW_ID", "")
_WEZTERM_PANE = os.environ.get("WEZTERM_PANE", "")


def detect_protocol() -> Literal["kitty", "iterm2", "sixel", "none"]:
    """Detect which terminal image protocol is supported.

    Returns:
        Protocol name: "kitty", "iterm2", "sixel", or "none"
    """
    # Kitty detection
    if _KITTY_WINDOW_ID or "kitty" in _TERM.lower():
        return "kitty"

    # WezTerm supports Kitty protocol
    if _WEZTERM_PANE or "wezterm" in _TERM_PROGRAM.lower():
        return "kitty"

    # Ghostty supports Kitty protocol
    if "ghostty" in _TERM.lower() or "ghostty" in _TERM_PROGRAM.lower():
        return "kitty"

    # iTerm2 detection
    if _TERM_PROGRAM == "iTerm.app" or "iterm" in _TERM_PROGRAM.lower():
        return "iterm2"

    # TODO: Add sixel detection for terminals that support it

    return "none"


def is_supported() -> bool:
    """Check if the current terminal supports inline images."""
    return detect_protocol() != "none"


def display_image(
    image_path: str | Path,
    width: int | None = None,
    height: int | None = None,
    preserve_aspect: bool = True,
    file=None,
) -> bool:
    """Display an image inline in the terminal.

    Args:
        image_path: Path to the image file
        width: Width in terminal columns (None for auto)
        height: Height in terminal rows (None for auto)
        preserve_aspect: Preserve aspect ratio when resizing
        file: Output file (defaults to sys.stdout)

    Returns:
        True if image was displayed, False if not supported
    """
    protocol = detect_protocol()

    if protocol == "none":
        return False

    if file is None:
        file = sys.stdout

    path = Path(image_path)
    if not path.exists():
        return False

    if protocol == "kitty":
        return _display_kitty(path, width, height, preserve_aspect, file)
    elif protocol == "iterm2":
        return _display_iterm2(path, width, height, preserve_aspect, file)

    return False


def display_pil_image(
    image,
    width: int | None = None,
    height: int | None = None,
    preserve_aspect: bool = True,
    file=None,
) -> bool:
    """Display a PIL Image inline in the terminal.

    Args:
        image: PIL Image object
        width: Width in terminal columns (None for auto)
        height: Height in terminal rows (None for auto)
        preserve_aspect: Preserve aspect ratio when resizing
        file: Output file (defaults to sys.stdout)

    Returns:
        True if image was displayed, False if not supported
    """
    protocol = detect_protocol()

    if protocol == "none":
        return False

    if file is None:
        file = sys.stdout

    # Convert to PNG bytes
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    data = buffer.getvalue()

    if protocol == "kitty":
        return _display_kitty_data(data, width, height, preserve_aspect, file)
    elif protocol == "iterm2":
        return _display_iterm2_data(data, width, height, preserve_aspect, file)

    return False


def _display_kitty(
    path: Path,
    width: int | None,
    height: int | None,
    preserve_aspect: bool,
    file,
) -> bool:
    """Display image using Kitty graphics protocol."""
    # Convert to PNG format (Kitty requires PNG, not JPEG)
    from PIL import Image
    img = Image.open(path)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    data = buffer.getvalue()
    return _display_kitty_data(data, width, height, preserve_aspect, file)


def _display_kitty_data(
    data: bytes,
    width: int | None,
    height: int | None,
    preserve_aspect: bool,
    file,
) -> bool:
    """Display image data using Kitty graphics protocol.

    Protocol reference: https://sw.kovidgoyal.net/kitty/graphics-protocol/
    """
    # Encode image data
    encoded = base64.standard_b64encode(data).decode("ascii")

    # Build control sequence
    # a=T: transmit and display
    # f=100: PNG format
    # t=d: direct (data follows)
    # c=width, r=height (in cells)
    params = ["a=T", "f=100", "t=d"]

    if width:
        params.append(f"c={width}")
    if height:
        params.append(f"r={height}")

    # Chunked transmission (max 4096 bytes per chunk)
    chunk_size = 4096
    chunks = [encoded[i:i+chunk_size] for i in range(0, len(encoded), chunk_size)]

    for i, chunk in enumerate(chunks):
        is_last = i == len(chunks) - 1
        m_value = 0 if is_last else 1  # m=1 means more data follows

        if i == 0:
            # First chunk includes all parameters
            param_str = ",".join(params + [f"m={m_value}"])
        else:
            # Subsequent chunks only have m parameter
            param_str = f"m={m_value}"

        # Write escape sequence: ESC_G<params>;<data>ESC\
        file.write(f"\033_G{param_str};{chunk}\033\\")

    file.write("\n")
    file.flush()
    return True


def _display_iterm2(
    path: Path,
    width: int | None,
    height: int | None,
    preserve_aspect: bool,
    file,
) -> bool:
    """Display image using iTerm2 image protocol."""
    with open(path, "rb") as f:
        data = f.read()
    return _display_iterm2_data(data, width, height, preserve_aspect, file)


def _display_iterm2_data(
    data: bytes,
    width: int | None,
    height: int | None,
    preserve_aspect: bool,
    file,
) -> bool:
    """Display image data using iTerm2 image protocol.

    Protocol reference: https://iterm2.com/documentation-images.html
    """
    encoded = base64.standard_b64encode(data).decode("ascii")

    # Build parameters
    params = ["inline=1"]

    if width:
        params.append(f"width={width}")
    if height:
        params.append(f"height={height}")
    if preserve_aspect:
        params.append("preserveAspectRatio=1")

    param_str = ";".join(params)

    # Write escape sequence: OSC 1337 ; File = <params> : <data> BEL
    file.write(f"\033]1337;File={param_str}:{encoded}\007")
    file.write("\n")
    file.flush()
    return True


def get_terminal_size() -> tuple[int, int]:
    """Get terminal size in columns and rows.

    Returns:
        Tuple of (columns, rows)
    """
    try:
        size = os.get_terminal_size()
        return size.columns, size.lines
    except OSError:
        return 80, 24  # Default fallback
