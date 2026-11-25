# LAN File

A small file server for your own Wi-Fi. Run it on your Mac, then open the same address in a browser on your phone to list, download, and upload files in one folder.

Both devices use the browser they already have. Nothing else is installed, and the server uses only the Python standard library.

## What it does

- Lists the files in `shared/`, with size and last-modified time.
- Downloads a file when you tap its name.
- Accepts an upload into that same folder, up to 50 MB.
- Refuses a name that would write or read outside `shared/`.
- Refuses an upload when a file with that name is already there.

The page is `page.html`. Python fills in the shared address and the file list, then sends the page.

## Requirements

- Python 3.11 or newer
- A Mac and a phone on the same Wi-Fi

## Run

From this folder:

```bash
mkdir -p shared
python3 server.py
```

The terminal prints an address such as `http://192.168.1.23:8000`. Open that address on the Mac and on the phone. `127.0.0.1` only works on the Mac, so it is not the link you share.

Put a file in `shared/` if you want something on the list before the first upload:

```bash
echo "hello from the mac" > shared/hello.txt
```

Stop the server with Ctrl+C. If the port is already taken, an older copy is still running. Quit it, or find it with `lsof -i :8000`.

## Layout

```
LAN File/
  server.py     the server
  page.html     the page the browser sees
  shared/       the only folder the server reads and writes
```

`shared/` is created next to `server.py`. Run the server from this folder so that path stays correct.

## Limits

This is for a network you trust.

- Anyone on that Wi-Fi who knows the address can list, download, and upload. There is no login.
- The server listens on every interface (`0.0.0.0`, port `8000`) so the phone can reach it. Set the host to `127.0.0.1` if you only want the Mac.
- Do not forward the port on your router, or run this on a machine that is open to the internet.
- Uploads larger than 50 MB are rejected. Hidden files (names starting with `.`) are left off the list.
