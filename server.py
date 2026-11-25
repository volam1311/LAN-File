
from calendar import c
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import socket
import html
import email
import mimetypes
import time
from urllib.parse import quote, unquote, urlsplit
from email.policy import default as policy

HOST = "0.0.0.0"
PORT = 8000
PAGE = Path(__file__).parent / "page.html"
SHARED = Path(__file__).parent / "shared"
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 10 MB

def local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()

def safe_destination(name: str) -> Path | None:
    """Return a path inside SHARED, or None if the name is not allowed.

    Does not care whether the file already exists.
    """
    if name in {"", ".", ".."}:
        return None
    if "/" in name or "\\" in name:
        return None
    root = SHARED.resolve()
    candidate = (root / name).resolve()
    if not candidate.is_relative_to(root):
        return None
    return candidate

def format_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{num_bytes} B"

def list_page():
    items = []
    paths = [
        path
        for path in SHARED.iterdir()
        if path.is_file() and not path.name.startswith(".")
    ]
    paths.sort(key=lambda path: path.name.lower())
    for path in paths:
        info = path.stat()
        shown = html.escape(path.name)
        href = "/download/" + quote(path.name)
        when = time.strftime("%Y-%m-%d %H:%M", time.localtime(info.st_mtime))
        items.append(
            f'<li><a href="{href}">{shown}</a>'
            f" — {format_size(info.st_size)} — {when}</li>"
        )
    inside = "\n".join(items)
    address = html.escape(f"http://{local_ip()}:{PORT}")
    template = PAGE.read_text(encoding="utf-8")
    return template.replace("{{ADDRESS}}", address).replace("{{ITEMS}}", inside)


def send_html(handler, status, page):
    body = page.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)

def send_file(handler: BaseHTTPRequestHandler, path: Path) -> None:
    data = path.read_bytes()
    guessed, _encoding = mimetypes.guess_type(path.name)
    content_type = guessed or "application/octet-stream"
    ascii_name = path.name.replace('"', "").encode("ascii", "replace").decode("ascii")
    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header(
        "Content-Disposition",
        f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(path.name)}",
    )
    handler.end_headers()
    handler.wfile.write(data)


def read_upload(handler: BaseHTTPRequestHandler) -> tuple[str, bytes] | None:
    """Return (filename, file_bytes) from a multipart POST, or None."""
    content_type = handler.headers.get("Content-Type", "")
    if "\r" in content_type or "\n" in content_type:
        return None
    header = f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n"
    message = email.message_from_bytes(
        header.encode("utf-8") + handler.uploaded_body,
        policy=policy,
    )
    if not message.is_multipart():
        return None
    for part in message.iter_parts():
        filename = part.get_filename()
        if not filename:
            continue
        data = part.get_payload(decode=True)
        if data is None:
            return None
        return Path(filename).name, data
    return None

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        requested = unquote(urlsplit(self.path).path)

        if requested == "/":
            send_html(self, 200, list_page())
            return

        prefix = "/download/"
        if requested.startswith(prefix):
            name = requested[len(prefix):]
            path = safe_destination(name)
            if path is None or not path.is_file():
                send_html(self, 404, "<h1>No such file</h1>")
                return
            send_file(self, path)
            return

        send_html(self, 404, "<h1>Not found</h1>")

    def do_POST(self):
        requested = urlsplit(self.path).path
        if requested != "/upload":
            send_html(self, 404, "<h1>Not found</h1>")
            return

        length_text = self.headers.get("Content-Length")
        if length_text is None:
            send_html(self, 400, "<h1>Missing Content-Length</h1>")
            return
        try:
            length = int(length_text)
        except ValueError:
            send_html(self, 400, "<h1>Bad Content-Length</h1>")
            return
        if length > MAX_UPLOAD_SIZE:
            send_html(self, 413, "<h1>File is larger than 50 MB</h1>")
            return

        self.uploaded_body = self.rfile.read(length)
        parsed = read_upload(self)
        if parsed is None:
            send_html(self, 400, "<h1>No file in that upload</h1>")
            return

        filename, data = parsed
        destination = safe_destination(filename)
        if destination is None:
            send_html(self, 400, "<h1>That file name is not allowed</h1>")
            return
        if destination.exists():
            send_html(self, 409, "<h1>A file with that name is already there</h1>")
            return

        destination.write_bytes(data)
        self.send_response(303)
        self.send_header("Location", "/")
        self.send_header("Content-Length", "0")
        self.end_headers()

def main():
    server = HTTPServer((HOST, PORT), Handler)
    print(f"http://{local_ip()}:{PORT}")
    server.serve_forever()

if __name__ == "__main__":
    main()