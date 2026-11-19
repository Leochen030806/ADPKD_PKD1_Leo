#!/usr/bin/env python3
"""Export PKD1 / STR / PGT-M related Claude conversations to readable Markdown.

Two sources are supported:

1. Claude Code local transcripts (default):
     ~/.claude/projects/<project>/<session>.jsonl   (Windows: %USERPROFILE%\\.claude\\projects)
   Every file Claude wrote with the Write tool is also restored verbatim under
   <out>/<session>/files/, so scripts produced during a session are recovered.

2. A claude.ai account export (Settings -> Privacy -> Export data):
     --claude-ai-export path/to/conversations.json

Only conversations whose text matches the keywords are exported (case-insensitive).

Usage:
  python export_local_claude_sessions.py --out session_exports
  python export_local_claude_sessions.py --claude-ai-export conversations.json --out chat_exports
  python export_local_claude_sessions.py --keywords PKD1 STR "PGT-M" --all   # --all: ignore keywords
Standard library only.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

DEFAULT_KEYWORDS = [
    "PKD1", "PKD2", "ADPKD", "PGT-M", "PGTM", "STR", "microsatellite", "primer",
    "引物", "GeneMapper", "Coriell", "multiplex", "simplex", "LIZ", "TRExplorer",
    "Panel Studio", "胶图", "下单表", "总表", "haplotype", "单倍型",
]


def safe(name, limit=80):
    name = re.sub(r'[\\/:*?"<>|\r\n\t]+', "_", str(name)).strip(" ._")
    return (name or "untitled")[:limit]


def blocks_to_md(content, files_out=None):
    """Render a message `content` (str or list of blocks) to Markdown lines."""
    if isinstance(content, str):
        return [content]
    out = []
    for b in content or []:
        if not isinstance(b, dict):
            continue
        t = b.get("type")
        if t == "text":
            out.append(b.get("text", ""))
        elif t == "thinking":
            continue
        elif t == "tool_use":
            name, inp = b.get("name", ""), b.get("input", {}) or {}
            if name == "Write" and files_out is not None and "content" in inp:
                files_out.append((inp.get("file_path", "unnamed"), inp["content"]))
                out.append(f"> 🛠 **Write** `{inp.get('file_path')}` ({len(inp['content'])} chars, restored under files/)")
            elif name in ("Edit", "MultiEdit"):
                out.append(f"> 🛠 **{name}** `{inp.get('file_path')}`")
            elif name in ("Bash", "PowerShell"):
                out.append(f"> 🛠 **{name}**\n```\n{str(inp.get('command', ''))[:2000]}\n```")
            else:
                s = json.dumps(inp, ensure_ascii=False)
                out.append(f"> 🛠 **{name}** {s[:500]}")
        elif t == "tool_result":
            c = b.get("content")
            if isinstance(c, list):
                c = "\n".join(x.get("text", "") for x in c if isinstance(x, dict))
            c = str(c or "")
            out.append("<details><summary>tool result</summary>\n\n```\n" + c[:3000] + "\n```\n</details>")
    return out


def matches(text, kws):
    low = text.lower()
    return any(k.lower() in low for k in kws)


def restore_files(files, dest):
    for i, (path, content) in enumerate(files):
        p = Path(str(path).replace("\\", "/"))
        target = dest / "files" / f"{i:03d}_{safe(p.name, 120)}"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        with (dest / "files" / "_index.tsv").open("a", encoding="utf-8") as idx:
            idx.write(f"{target.name}\t{path}\n")


def export_claude_code(root, out, kws, all_):
    n = 0
    for jf in sorted(Path(root).glob("*/*.jsonl")):
        lines, files, title, raw = [], [], None, []
        for line in jf.open(encoding="utf-8", errors="replace"):
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if ev.get("type") == "summary" and ev.get("summary"):
                title = title or ev["summary"]
            msg = ev.get("message")
            if not isinstance(msg, dict) or ev.get("type") not in ("user", "assistant"):
                continue
            body = blocks_to_md(msg.get("content"), files)
            if not any(x.strip() for x in body):
                continue
            raw.extend(body)
            lines.append(f"\n### {ev['type'].upper()} · {ev.get('timestamp', '')}\n")
            lines.extend(body)
        text = "\n".join(raw)
        if not text or not (all_ or matches(text, kws)):
            continue
        name = safe(f"{jf.parent.name}__{title or jf.stem}")
        dest = out / name
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "transcript.md").write_text(
            f"# {title or jf.stem}\n\nsource: `{jf}`\n" + "\n".join(lines), encoding="utf-8")
        restore_files(files, dest)
        n += 1
        print(f"  exported {name}  ({len(files)} files restored)")
    return n


def export_claude_ai(path, out, kws, all_):
    data = json.load(open(path, encoding="utf-8"))
    n = 0
    for conv in data:
        msgs = conv.get("chat_messages", [])
        lines, raw = [], []
        for m in msgs:
            body = blocks_to_md(m.get("content") or m.get("text", ""))
            raw.extend(body)
            lines.append(f"\n### {str(m.get('sender', '')).upper()} · {m.get('created_at', '')}\n")
            lines.extend(body)
        text = (conv.get("name") or "") + "\n" + "\n".join(raw)
        if not (all_ or matches(text, kws)):
            continue
        name = safe(f"{(conv.get('created_at') or '')[:10]}_{conv.get('name') or conv.get('uuid')}")
        dest = out / name
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "transcript.md").write_text(f"# {conv.get('name')}\n" + "\n".join(lines), encoding="utf-8")
        n += 1
        print(f"  exported {name}")
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="session_exports")
    ap.add_argument("--projects-dir", default=str(Path.home() / ".claude" / "projects"))
    ap.add_argument("--claude-ai-export", help="conversations.json from a claude.ai data export")
    ap.add_argument("--keywords", nargs="+", default=DEFAULT_KEYWORDS)
    ap.add_argument("--all", action="store_true", help="export everything, ignore keywords")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.claude_ai_export:
        n = export_claude_ai(a.claude_ai_export, out, a.keywords, a.all)
    else:
        if not os.path.isdir(a.projects_dir):
            sys.exit(f"no Claude Code transcripts at {a.projects_dir}")
        n = export_claude_code(a.projects_dir, out, a.keywords, a.all)
    print(f"done: {n} conversation(s) -> {out.resolve()}")


if __name__ == "__main__":
    main()
