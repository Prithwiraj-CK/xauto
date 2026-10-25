"""Build out/engage.html: one checklist page with a Like and Reply button per draft.

  python3 engage_page.py [drafts.json]     default out/engage_drafts.json

drafts.json: [{"id", "url", "author", "text", "reply"}, ...]
The page only opens X links; the human taps Like / Post themselves. Done rows grey out (kept in localStorage).
"""
import html
import json
import sys
import urllib.parse
from pathlib import Path

from send_discord import humanize, lint

ROOT = Path(__file__).parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "out" / "engage_drafts.json"
OUT = ROOT / "out" / "engage.html"

ROW = """<div class="row" data-id="{id}">
<div class="who">@{author} <a href="{url}" target="_blank">open</a></div>
<div class="tw">{text}</div>
<textarea>{reply}</textarea>
<div class="btns"><a class="b reply" target="_blank">Reply</a>
<a class="b like" target="_blank" href="https://x.com/intent/like?tweet_id={id}">Like</a>
<label><input type="checkbox"> done</label></div></div>"""

PAGE = """<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Engage checklist</title>
<style>
body{{font:15px system-ui;max-width:640px;margin:0 auto;padding:16px;background:#111;color:#eee}}
.row{{border:1px solid #333;border-radius:10px;padding:12px;margin:10px 0}}
.row.done{{opacity:.35}}.who{{font-weight:600}}.who a{{font-weight:400;color:#8ab4ff}}
.tw{{color:#aaa;margin:6px 0;white-space:pre-wrap}}
textarea{{width:100%;box-sizing:border-box;background:#1b1b1b;color:#eee;border:1px solid #333;border-radius:6px;padding:8px;font:inherit}}
.btns{{display:flex;gap:10px;align-items:center;margin-top:8px}}
.b{{padding:6px 14px;border-radius:16px;background:#1d9bf0;color:#fff;text-decoration:none;cursor:pointer}}
.like{{background:#f91880}}
</style>
<h2>Engage checklist <span id="n"></span></h2>
{rows}
<script>
const done = new Set(JSON.parse(localStorage.getItem("engage_done") || "[]"));
function count() {{ document.getElementById("n").textContent = done.size + "/" + document.querySelectorAll(".row").length; }}
document.querySelectorAll(".row").forEach(r => {{
  const id = r.dataset.id, ta = r.querySelector("textarea"), cb = r.querySelector("input");
  const setLink = () => r.querySelector(".reply").href =
    "https://x.com/intent/post?in_reply_to=" + id + "&text=" + encodeURIComponent(ta.value);
  ta.addEventListener("input", setLink); setLink();
  const paint = () => r.classList.toggle("done", done.has(id));
  cb.checked = done.has(id); paint();
  cb.addEventListener("change", () => {{
    cb.checked ? done.add(id) : done.delete(id); paint(); count();
    localStorage.setItem("engage_done", JSON.stringify([...done]));
  }});
}});
count();
</script>"""


def main():
    drafts = json.loads(SRC.read_text())
    for d in drafts:
        d["reply"] = humanize(d["reply"])
        if lint(d["reply"]) or len(d["reply"].split()) < 4:  # engage group needs 4+ words
            print(f"fix @{d['author']}: {d['reply']!r} {lint(d['reply']) or ['under 4 words']}")
    rows = "\n".join(ROW.format(id=d["id"], url=html.escape(d["url"]), author=html.escape(d["author"]),
                                text=html.escape(d.get("text", "")[:400]), reply=html.escape(d["reply"]))
                     for d in drafts)
    OUT.write_text(PAGE.format(rows=rows))
    print(f"{len(drafts)} rows -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
