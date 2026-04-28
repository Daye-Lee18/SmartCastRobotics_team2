#!/usr/bin/env python3
"""
Render docs/project/*.md → docs/project/*.html.

GitHub-dark 테마 기반 단일 파일 HTML 생성. 외부 CDN 의존 없음.
"""

from __future__ import annotations

import html as html_mod
import sys
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "docs" / "project"

EXTENSIONS = [
    "fenced_code",
    "codehilite",
    "tables",
    "toc",
    "sane_lists",
    "attr_list",
    "nl2br",
    "admonition",
]

EXTENSION_CONFIGS = {
    "codehilite": {"guess_lang": False, "css_class": "codehilite"},
    "toc": {"permalink": False, "baselevel": 1, "toc_depth": "2-3"},
}


CSS = """
:root {
  --bg: #0d1117;
  --panel: #161b22;
  --panel-2: #1c2229;
  --border: #30363d;
  --text: #c9d1d9;
  --text-dim: #8b949e;
  --accent: #58a6ff;
  --accent-2: #f0883e;
  --ok: #56d364;
  --warn: #d29922;
  --ng: #f85149;
  --purple: #bc8cff;
  --cyan: #79c0ff;
  --code-bg: #0d1117;
}

* { box-sizing: border-box; }

html, body {
  margin: 0;
  padding: 0;
}

body {
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, "SF Pro Display", "Apple SD Gothic Neo",
               "Noto Sans KR", "Segoe UI", sans-serif;
  line-height: 1.7;
  padding: 2rem 1rem 6rem;
}

.container {
  max-width: 1080px;
  margin: 0 auto;
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 2.5rem 3rem;
  box-shadow: 0 4px 24px rgba(0,0,0,0.35);
}

.nav {
  max-width: 1080px;
  margin: 0 auto 1rem;
  padding: 0.6rem 1rem;
  background: var(--panel-2);
  border: 1px solid var(--border);
  border-radius: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  font-size: 0.9rem;
}

.nav a {
  color: var(--accent);
  text-decoration: none;
  padding: 0.2rem 0.55rem;
  border-radius: 6px;
  transition: background 0.15s ease;
}

.nav a:hover { background: #24292f; }
.nav a.current {
  background: #1f6feb;
  color: #fff;
}

h1, h2, h3, h4, h5 {
  color: #f0f6fc;
  margin-top: 2em;
  margin-bottom: 0.6em;
  border-bottom: 1px solid var(--border);
  padding-bottom: 0.3em;
  line-height: 1.3;
}

h1 { font-size: 2rem; margin-top: 0; }
h2 { font-size: 1.5rem; }
h3 { font-size: 1.2rem; border-bottom: none; }
h4 { font-size: 1.05rem; border-bottom: none; color: var(--cyan); }
h5 { font-size: 0.98rem; border-bottom: none; color: var(--purple); }

a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

p { margin: 0.8em 0; }

blockquote {
  margin: 1em 0;
  padding: 0.6em 1.2em;
  border-left: 4px solid var(--accent-2);
  background: var(--panel-2);
  color: var(--text-dim);
  border-radius: 0 6px 6px 0;
}

blockquote p { margin: 0.3em 0; }

ul, ol {
  padding-left: 1.6em;
  margin: 0.8em 0;
}

li { margin: 0.3em 0; }

hr {
  border: 0;
  border-top: 1px solid var(--border);
  margin: 2em 0;
}

code {
  background: #24292f;
  color: var(--cyan);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: "SF Mono", "JetBrains Mono", "Cascadia Code", Consolas, monospace;
  font-size: 0.88em;
}

pre {
  background: var(--code-bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 1em 1.2em;
  overflow-x: auto;
  margin: 1em 0;
  font-size: 0.9em;
  line-height: 1.55;
}

pre code {
  background: transparent;
  color: var(--text);
  padding: 0;
  border-radius: 0;
  font-size: 1em;
}

.codehilite {
  background: var(--code-bg) !important;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 0.1em 0;
  margin: 1em 0;
  overflow-x: auto;
}

.codehilite pre {
  background: transparent;
  border: 0;
  margin: 0;
  padding: 0.9em 1.2em;
}

/* pygments inline tokens (monokai-ish) */
.codehilite .k, .codehilite .kd, .codehilite .kr { color: #ff7b72; }
.codehilite .s, .codehilite .s1, .codehilite .s2, .codehilite .sa, .codehilite .sb,
.codehilite .sc, .codehilite .se, .codehilite .si, .codehilite .sx { color: #a5d6ff; }
.codehilite .c, .codehilite .c1, .codehilite .cm, .codehilite .cs { color: #8b949e; font-style: italic; }
.codehilite .nf, .codehilite .nc, .codehilite .nt { color: #d2a8ff; }
.codehilite .nb, .codehilite .bp { color: #79c0ff; }
.codehilite .m, .codehilite .mi, .codehilite .mf { color: #f0883e; }
.codehilite .o, .codehilite .ow { color: #ff7b72; }

table {
  border-collapse: collapse;
  margin: 1em 0;
  width: 100%;
  font-size: 0.92em;
  overflow-x: auto;
  display: block;
}

table thead { background: var(--panel-2); }

th, td {
  border: 1px solid var(--border);
  padding: 0.55em 0.85em;
  text-align: left;
  vertical-align: top;
}

th {
  color: #f0f6fc;
  font-weight: 600;
}

tr:nth-child(even) td { background: rgba(177, 186, 196, 0.04); }

img { max-width: 100%; height: auto; border-radius: 6px; }

strong { color: #f0f6fc; }

.footer {
  max-width: 1080px;
  margin: 2rem auto 0;
  padding: 1rem;
  font-size: 0.85em;
  color: var(--text-dim);
  text-align: center;
}

@media (max-width: 720px) {
  .container { padding: 1.5rem 1.2rem; }
  h1 { font-size: 1.6rem; }
  table { font-size: 0.85em; }
}
"""


DOCS = [
    ("README.md", "README.html", "00. 문서 인덱스"),
    ("01_PRD.md", "01_PRD.html", "01. PRD"),
    ("02_DESIGN.md", "02_DESIGN.html", "02. DESIGN"),
    ("03_PROCESS.md", "03_PROCESS.html", "03. PROCESS"),
    ("04_DEVELOPMENT.md", "04_DEVELOPMENT.html", "04. DEVELOPMENT"),
    ("05_TRAINING.md", "05_TRAINING.html", "05. TRAINING"),
    ("06_MANUAL.md", "06_MANUAL.html", "06. MANUAL"),
]


def build_nav(current_html: str) -> str:
    parts = ['<div class="nav">']
    for _, href, label in DOCS:
        cls = "current" if href == current_html else ""
        parts.append(f'<a class="{cls}" href="{href}">{html_mod.escape(label)}</a>')
    parts.append("</div>")
    return "\n".join(parts)


def rewrite_md_links(html: str) -> str:
    """내부 .md 링크를 .html 로 치환 (docs/project/ 내부 링크만)."""
    out = html
    for md_name, html_name, _ in DOCS:
        out = out.replace(f'href="./{md_name}"', f'href="./{html_name}"')
        out = out.replace(f'href="{md_name}"', f'href="{html_name}"')
    return out


def render_one(md_path: Path, out_path: Path, title: str, current_html: str) -> None:
    md_text = md_path.read_text(encoding="utf-8")
    html_body = markdown.markdown(
        md_text,
        extensions=EXTENSIONS,
        extension_configs=EXTENSION_CONFIGS,
        output_format="html5",
    )
    html_body = rewrite_md_links(html_body)

    nav = build_nav(current_html)
    doc = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{html_mod.escape(title)} — SmartCast Robotics 프로젝트 문서</title>
<style>{CSS}</style>
</head>
<body>
{nav}
<main class="container">
{html_body}
</main>
<div class="footer">
  SmartCast Robotics 프로젝트 문서 · V6 (2026-04-24) ·
  <a href="README.html">문서 인덱스</a>
</div>
</body>
</html>
"""
    out_path.write_text(doc, encoding="utf-8")


def main() -> int:
    if not SRC_DIR.exists():
        print(f"[!] source dir not found: {SRC_DIR}", file=sys.stderr)
        return 1

    for md_name, html_name, title in DOCS:
        src = SRC_DIR / md_name
        out = SRC_DIR / html_name
        if not src.exists():
            print(f"[skip] {md_name} (missing)")
            continue
        render_one(src, out, title, html_name)
        print(f"[ok] {md_name} -> {html_name}  ({out.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
