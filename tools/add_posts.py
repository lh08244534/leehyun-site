#!/usr/bin/env python3
"""Add research-note posts to index.html and keep the pre-rendered list in sync.

Usage:
    python3 tools/add_posts.py new_posts.json      # add posts (skips URLs already present)
    python3 tools/add_posts.py --rebuild           # only re-render the list from the JSON

new_posts.json is a JSON array of objects with keys:
    id, date (YYYY-MM-DD), lang (ko|fr|en), title, summary, tags, url, body
Existing posts are never modified or removed.
"""
import html, json, re, sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
SITEMAP = ROOT / "sitemap.xml"
LANGNAME = {"fr": "FR", "en": "EN", "ko": "한"}

DATA_RE = re.compile(r'(<script type="application/json" id="posts-data">)(.*?)(</script>)', re.S)
LIST_RE = re.compile(r'(<ul class="posts" id="postlist">)(.*?)(</ul>)', re.S)


def esc(s):
    return html.escape(str(s or ""), quote=True)


def fmt_date(iso):
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", iso or "")
    return f"{m[3]}.{m[2]}.{m[1]}" if m else esc(iso)


def meta(p):
    host = ""
    if p.get("url"):
        host = urlparse(p["url"]).hostname or ""
        host = host[4:] if host.startswith("www.") else host
    out = f'<div class="meta"><span class="badge">{LANGNAME.get(p.get("lang"), "")}</span>'
    if host:
        out += f'<span class="badge">{esc(host)}</span>'
    if (p.get("tags") or "").strip():
        out += f'<span class="tag">{esc(p["tags"].strip())}</span>'
    return out + "</div>"


def render(posts):
    """Same markup as renderList() in the page script, French view (the page default)."""
    rows = []
    for p in sorted(posts, key=lambda x: x.get("date") or "", reverse=True):
        if p.get("url"):
            title = (f'<a class="t" href="{esc(p["url"])}" target="_blank" rel="noopener">'
                     f'{esc(p["title"])} <span aria-hidden="true">↗</span></a>')
        else:
            title = f'<button type="button" class="t" data-open="{esc(p["id"])}">{esc(p["title"])}</button>'
        summary = f'<p>{esc(p["summary"])}</p>' if p.get("summary") else ""
        rows.append(f'<li><time datetime="{esc(p.get("date"))}">{fmt_date(p.get("date"))}</time>'
                    f'<div class="body">{title}{summary}{meta(p)}</div></li>')
    return "".join(rows) or '<li><span></span><p class="empty">Aucun billet pour l’instant.</p></li>'


def main():
    src = INDEX.read_text(encoding="utf-8")
    m = DATA_RE.search(src)
    if not m:
        sys.exit("posts-data block not found")
    posts = json.loads(m.group(2))
    added = []
    if len(sys.argv) == 2 and sys.argv[1] != "--rebuild":
        have_urls = {p.get("url") for p in posts if p.get("url")}
        have_ids = {p.get("id") for p in posts}
        for p in json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")):
            if p.get("url") in have_urls or p.get("id") in have_ids:
                continue
            posts.append({k: p.get(k, "") for k in ("id", "date", "lang", "title", "summary", "tags", "url", "body")})
            added.append(p["title"])
    elif len(sys.argv) != 2:
        sys.exit(__doc__)

    data = json.dumps(posts, ensure_ascii=False).replace("<", "\\u003c")
    src, n1 = DATA_RE.subn(lambda mm: mm.group(1) + data + mm.group(3), src, count=1)
    src, n2 = LIST_RE.subn(lambda mm: mm.group(1) + render(posts) + mm.group(3), src, count=1)
    if n1 != 1 or n2 != 1:
        sys.exit("could not update index.html (blocks not found)")
    INDEX.write_text(src, encoding="utf-8")

    if SITEMAP.exists():
        sm = SITEMAP.read_text(encoding="utf-8")
        SITEMAP.write_text(re.sub(r"<lastmod>[^<]*</lastmod>", f"<lastmod>{date.today().isoformat()}</lastmod>", sm), encoding="utf-8")

    print(json.dumps({"total": len(posts), "added": added}, ensure_ascii=False))


if __name__ == "__main__":
    main()
