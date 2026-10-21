"""Collect public Cars24 complaints from consumercomplaints.in -> data/complaints.jsonl.

Raw text stays local (data/ is gitignored): it is user-written and contains names
and registration numbers. Only ids/urls/labels are published.
Usage: python3 collect.py [pages]   (20 complaints per listing page)
"""
import html, json, re, sys, time, urllib.request
from pathlib import Path

BASE = "https://www.consumercomplaints.in"
COMPANY = "/cars24-services-b115241"
UA = {"User-Agent": "Mozilla/5.0 (research; complaint-triage eval)"}
OUT = Path(__file__).parent / "data" / "complaints.jsonl"


def get(url):
    for wait in (1, 5, 15):  # be polite; the site times out now and then
        time.sleep(wait)
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read().decode("utf-8", "replace")
        except OSError as e:
            print("retry", url, e, file=sys.stderr)
    return ""


def text(fragment):
    fragment = re.sub(r"<table class=\"custom-fields\".*?</table>", "", fragment, flags=re.S)
    fragment = re.sub(r"<br\s*/?>", "\n", fragment)
    return re.sub(r"\n{3,}", "\n\n", html.unescape(re.sub(r"<[^>]+>", "", fragment))).strip()


def parse(page, url):
    title = re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S)
    date = re.search(r'itemprop="datePublished" content="(\d{4}-\d\d-\d\d)', page)
    body = re.search(r'<div itemprop="reviewBody">(.*?)</div>\s*</td>', page, re.S)
    return {"id": re.search(r"-c(\d+)$", url).group(1), "url": url,
            "date": date.group(1) if date else "",
            "title": text(title.group(1)) if title else "",
            "text": text(body.group(1)) if body else ""}


def main(pages):
    OUT.parent.mkdir(exist_ok=True)
    seen = {json.loads(l)["id"] for l in OUT.open()} if OUT.exists() else set()
    with OUT.open("a") as f:
        for p in range(1, pages + 1):
            listing = get(BASE + COMPANY + (f"/page/{p}" if p > 1 else ""))
            for path in dict.fromkeys(re.findall(r'class="complaint-box__title"><a href="(/[^"]+-c\d+)"', listing)):
                url = BASE + path
                if re.search(r"-c(\d+)$", url).group(1) in seen:
                    continue
                page = get(url)
                row = parse(page, url) if page else None
                if row and row["text"]:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
                    seen.add(row["id"])
            print(f"page {p}: {len(seen)} complaints", flush=True)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 8)
