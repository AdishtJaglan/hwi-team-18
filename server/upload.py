
"""
Simple CLI to upload one or more local files to the /api/upload_raw/ endpoint.
Usage:
  python upload.py /full/path/to/image.jpg --location "New Delhi" --sublocation "North"
  python upload.py file1.jpg file2.png --location "mumbai" 
  python3 upload.py ../../../../Downloads/no-urban.png --location "New Delhi" --sublocation "North"
"""

import argparse
import os
import sys
import mimetypes
import requests

DEFAULT_URL = "http://127.0.0.1:8000/api/upload_raw/"

def upload_file(filepath, url, location, sublocation, timeout=30):
    if not os.path.isfile(filepath):
        print(f"[ERR] file not found: {filepath}", file=sys.stderr)
        return False, {"error": "file not found", "path": filepath}

    fname = os.path.basename(filepath)
    mime_type, _ = mimetypes.guess_type(filepath)
    mime_type = mime_type or "application/octet-stream"

    with open(filepath, "rb") as f:
        files = {"file": (fname, f, mime_type)}
        data = {"location": location or "", "sublocation": sublocation or ""}
        try:
            resp = requests.post(url, files=files, data=data, timeout=timeout)
        except requests.RequestException as e:
            return False, {"error": "request_exception", "detail": str(e)}
    try:
        payload = resp.json()
    except ValueError:
        payload = {"text": resp.text}

    success = 200 <= resp.status_code < 300
    return success, {"status_code": resp.status_code, "response": payload, "filepath": filepath}

def main():
    p = argparse.ArgumentParser(description="Upload local file(s) to Django /api/upload_raw/")
    p.add_argument("files", nargs="+", help="Path(s) to file(s) to upload")
    p.add_argument("--url", default=DEFAULT_URL, help=f"Upload endpoint URL (default: {DEFAULT_URL})")
    p.add_argument("--location", required=True, help="Location (e.g. 'New Delhi')")
    p.add_argument("--sublocation", default="", help="Sublocation (e.g. 'North')")
    p.add_argument("--timeout", type=int, default=30, help="Request timeout seconds")
    args = p.parse_args()

    any_fail = False
    for fpath in args.files:
        print(f"\nUploading: {fpath}  ->  {args.url}")
        ok, info = upload_file(fpath, args.url, args.location, args.sublocation, timeout=args.timeout)
        if ok:
            print("[OK] uploaded:", info["response"])
        else:
            any_fail = True
            print("[FAIL]", info)

    if any_fail:
        sys.exit(2)

if __name__ == "__main__":
    main()
