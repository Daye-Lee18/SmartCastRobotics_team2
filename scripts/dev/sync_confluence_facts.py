#!/usr/bin/env python3
"""Confluence → docs/CONFLUENCE_FACTS.md 동기화 스크립트.

⚠️ READ-ONLY 정책:
    이 스크립트는 Confluence addinedute space (homepage 753829 하부) 의
    페이지를 **절대 수정/생성/삭제하지 않는다**. GET 요청만 수행한다.
    사용자 명시 허락 없이 PUT/POST/DELETE 를 추가하는 것은 금지된다.


동작 방식:
  1. docs/CONFLUENCE_FACTS.md 를 파싱해 `### X.Y Title (PAGE_ID)` 형태의 섹션 헤더에서
     page ID 목록을 추출한다.
  2. 각 페이지의 최신 version 번호를 Confluence REST API v2 로 조회해
     docs/.confluence_snapshot.json 의 기록과 비교한다.
  3. 변경된 페이지는 body(storage)를 받아 HTML→Markdown 으로 변환 후
     CONFLUENCE_FACTS.md 의 해당 섹션을 in-place 로 덮어쓴다.
  4. 섹션 안에 `<!-- CURATED:START -->...<!-- CURATED:END -->` 로 감싼 블록은 보존한다.
     (코드베이스 교차검증 등 직접 작성한 메모 보호용)
  5. 변경이 감지되면 git add + commit 까지 자동 수행한다.

인증:
  macOS Keychain 에서 API 토큰을 읽는다.
    service : casting-factory-atlassian
    account : kiminbean@gmail.com

실행:
  scripts/sync_confluence_facts.py            (launchd 에서 매일 09:07 자동 실행)
  scripts/sync_confluence_facts.py --dry-run  (변경 감지만, 파일/git 수정 안 함)
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

# ---------- 설정 ----------
BASE_URL = "https://dayelee313.atlassian.net"
EMAIL = "kiminbean@gmail.com"
KEYCHAIN_SERVICE = "casting-factory-atlassian"
SPACE_KEY = "addinedute"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCS_FILE = PROJECT_ROOT / "docs" / "CONFLUENCE_FACTS.md"
SNAPSHOT_FILE = PROJECT_ROOT / "docs" / ".confluence_snapshot.json"
LOG_FILE = PROJECT_ROOT / "logs" / "confluence_sync.log"

SECTION_RE = re.compile(r"^(#{3,4})\s+(.+?)\s+\((\d{4,})\)\s*$", re.M)
CURATED_RE = re.compile(r"<!--\s*CURATED:START\s*-->.*?<!--\s*CURATED:END\s*-->", re.S)
LAST_UPDATE_RE = re.compile(r"(> \*\*마지막 업데이트\*\*:)\s*[^\n]*", re.M)

log = logging.getLogger("confluence-sync")


# ---------- 유틸 ----------
def get_token() -> str:
    result = subprocess.run(
        ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-a", EMAIL, "-w"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def api_get(path: str, token: str) -> dict:
    url = f"{BASE_URL}{path}"
    auth = base64.b64encode(f"{EMAIL}:{token}".encode()).decode()
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Basic {auth}",
            "Accept": "application/json",
            "User-Agent": "casting-factory-confluence-sync/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def fetch_page(page_id: str, token: str) -> dict:
    return api_get(f"/wiki/api/v2/pages/{page_id}?body-format=storage", token)


# ---------- HTML → Markdown 최소 변환기 ----------
# Confluence storage 포맷을 읽기 쉬운 마크다운으로 바꾸기 위한 용도.
# 완벽한 변환기가 아니며 문단/헤딩/리스트/표/링크/인라인 강조만 지원한다.
class HtmlToMarkdown(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.list_stack: list[str] = []
        self._href = ""
        self.in_cell = False
        self.cell_buf: list[str] = []
        self.row_cells: list[str] = []
        self.first_row = True

    def _nl(self) -> None:
        if self.out and not self.out[-1].endswith("\n"):
            self.out.append("\n")

    def handle_starttag(self, tag, attrs):  # noqa: D401
        t = tag.lower()
        if t in ("p", "div"):
            self._nl()
        elif t and len(t) == 2 and t[0] == "h" and t[1].isdigit():
            self._nl()
            self.out.append("\n" + "#" * int(t[1]) + " ")
        elif t == "ul":
            self.list_stack.append("ul")
        elif t == "ol":
            self.list_stack.append("ol")
        elif t == "li":
            indent = "  " * (len(self.list_stack) - 1)
            marker = "- " if self.list_stack and self.list_stack[-1] == "ul" else "1. "
            self.out.append(f"\n{indent}{marker}")
        elif t in ("strong", "b"):
            self.out.append("**")
        elif t in ("em", "i"):
            self.out.append("*")
        elif t == "code":
            self.out.append("`")
        elif t == "pre":
            self._nl()
            self.out.append("\n```\n")
        elif t == "br":
            self.out.append("\n")
        elif t == "a":
            self._href = dict(attrs).get("href", "")
            self.out.append("[")
        elif t == "table":
            self.first_row = True
            self._nl()
            self.out.append("\n")
        elif t == "tr":
            self.row_cells = []
        elif t in ("td", "th"):
            self.in_cell = True
            self.cell_buf = []

    def handle_endtag(self, tag):
        t = tag.lower()
        if t in ("p", "div"):
            self._nl()
        elif t and len(t) == 2 and t[0] == "h" and t[1].isdigit():
            self._nl()
        elif t in ("ul", "ol"):
            if self.list_stack:
                self.list_stack.pop()
            self._nl()
        elif t in ("strong", "b"):
            self.out.append("**")
        elif t in ("em", "i"):
            self.out.append("*")
        elif t == "code":
            self.out.append("`")
        elif t == "pre":
            self.out.append("\n```\n")
        elif t == "a":
            self.out.append(f"]({self._href})")
            self._href = ""
        elif t in ("td", "th"):
            self.in_cell = False
            cell = "".join(self.cell_buf).strip().replace("\n", " ").replace("|", "\\|")
            self.row_cells.append(cell or " ")
        elif t == "tr":
            if self.row_cells:
                self.out.append("| " + " | ".join(self.row_cells) + " |\n")
                if self.first_row:
                    self.out.append("|" + "---|" * len(self.row_cells) + "\n")
                    self.first_row = False
        elif t == "table":
            self._nl()

    def handle_data(self, data):
        if self.in_cell:
            self.cell_buf.append(data)
        else:
            self.out.append(data)

    def result(self) -> str:
        text = "".join(self.out)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


def html_to_markdown(html: str) -> str:
    # Confluence 매크로 태그(ac:*, ri:*) 는 마크다운으로 깔끔히 옮기기 어려워 제거한다.
    html = re.sub(r"<ac:[^>]*/>", "", html)
    html = re.sub(r"<ac:[^>]*>.*?</ac:[^>]+>", "", html, flags=re.S)
    html = re.sub(r"<ri:[^>]*/?>", "", html)
    parser = HtmlToMarkdown()
    parser.feed(html)
    return parser.result()


# ---------- 섹션 파싱/치환 ----------
def parse_sections(md: str) -> list[tuple[str, str, int, int, int]]:
    """(page_id, title, level, start, end) 튜플 목록. end 는 섹션 끝 offset."""
    matches = list(SECTION_RE.finditer(md))
    sections: list[tuple[str, str, int, int, int]] = []
    for i, m in enumerate(matches):
        level = len(m.group(1))
        title = m.group(2).strip()
        page_id = m.group(3)
        start = m.start()
        end = len(md)
        for nxt in matches[i + 1 :]:
            if len(nxt.group(1)) <= level:
                end = nxt.start()
                break
        sections.append((page_id, title, level, start, end))
    return sections


def replace_section(md: str, start: int, end: int, new_block: str) -> str:
    old = md[start:end]
    curated = CURATED_RE.findall(old)
    new_section = new_block.rstrip() + "\n\n"
    if curated:
        new_section += "\n\n".join(curated) + "\n\n"
    return md[:start] + new_section + md[end:]


# ---------- 메인 ----------
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="파일/git 변경 없이 비교만")
    parser.add_argument(
        "--init-snapshot",
        action="store_true",
        help="현재 버전만 snapshot 에 기록하고 본문은 건드리지 않음 (최초 1회 초기화용)",
    )
    args = parser.parse_args()

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()],
    )
    log.info("=" * 60)
    log.info("Confluence sync start")

    try:
        token = get_token()
    except Exception as e:
        log.error(f"Keychain token read failed: {e}")
        return 1

    md = DOCS_FILE.read_text(encoding="utf-8")
    sections = parse_sections(md)
    log.info(f"Discovered {len(sections)} page sections")

    snapshot: dict[str, int] = {}
    if SNAPSHOT_FILE.exists():
        try:
            snapshot = json.loads(SNAPSHOT_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            log.warning("snapshot json unreadable, treating as empty")

    new_snapshot: dict[str, int] = {}
    plans: list[tuple[str, str, int, str]] = []  # (page_id, title, version, html)

    for page_id, title, *_ in sections:
        try:
            page = fetch_page(page_id, token)
        except urllib.error.HTTPError as e:
            log.warning(f"[{page_id}] HTTP {e.code}: {e.reason}")
            new_snapshot[page_id] = snapshot.get(page_id, 0)
            continue
        except Exception as e:
            log.warning(f"[{page_id}] fetch failed: {e}")
            new_snapshot[page_id] = snapshot.get(page_id, 0)
            continue

        version = int(page.get("version", {}).get("number", 0))
        new_snapshot[page_id] = version
        prev = snapshot.get(page_id)
        if args.init_snapshot:
            log.info(f"[{page_id}] {title}: init → v{version}")
            continue
        if prev == version:
            continue
        log.info(f"[{page_id}] {title}: v{prev} → v{version}")
        html = page.get("body", {}).get("storage", {}).get("value", "") or ""
        api_title = page.get("title", title)
        plans.append((page_id, api_title, version, html))

    changed_desc: list[str] = []

    if plans:
        # 섹션 맵은 매번 덮어쓰면 offset 이 어긋나므로 뒤에서부터 적용한다.
        section_map = {s[0]: s for s in parse_sections(md)}
        plans.sort(key=lambda p: -section_map[p[0]][3])  # start offset 내림차순
        for page_id, title, version, html in plans:
            _, _, sec_level, start, end = section_map[page_id]
            body_md = html_to_markdown(html)
            header = (
                f"{'#' * sec_level} {title} ({page_id})\n\n"
                f"**Confluence URL**: {BASE_URL}/wiki/spaces/{SPACE_KEY}/pages/{page_id}\n"
                f"**최종 수정**: v{version} ({date.today().isoformat()} sync)\n\n"
                f"{body_md}\n"
            )
            md = replace_section(md, start, end, header)
            changed_desc.append(f"{page_id} v{version} ({title})")
            # 남은 plan 들은 앞쪽이라 offset 변화 없음 (뒤→앞 순서 덕).

        md = LAST_UPDATE_RE.sub(
            rf"\1 {date.today().isoformat()} (cron sync: {len(plans)}건)", md, count=1
        )

    if args.dry_run:
        log.info(f"[dry-run] would change {len(plans)} sections")
        for c in changed_desc:
            log.info(f"  - {c}")
        return 0

    if args.init_snapshot:
        SNAPSHOT_FILE.write_text(
            json.dumps(new_snapshot, indent=2, sort_keys=True, ensure_ascii=False),
            encoding="utf-8",
        )
        log.info(f"snapshot initialized with {len(new_snapshot)} pages (no content changes)")
        return 0

    # 스냅샷은 항상 갱신 (변경 없어도 새 페이지 추적용).
    SNAPSHOT_FILE.write_text(
        json.dumps(new_snapshot, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8"
    )

    if not plans:
        log.info("No changes detected.")
        return 0

    DOCS_FILE.write_text(md, encoding="utf-8")

    # git commit
    try:
        subprocess.run(
            ["git", "add", str(DOCS_FILE.relative_to(PROJECT_ROOT))],
            cwd=PROJECT_ROOT,
            check=True,
        )
        msg_body = "\n".join(f"- {c}" for c in changed_desc)
        msg = (
            f"chore(docs): Confluence 팩트 자동 동기화 ({date.today().isoformat()})\n\n"
            f"변경된 페이지 {len(changed_desc)}건:\n{msg_body}\n\n"
            f"Auto-generated by scripts/sync_confluence_facts.py (launchd)"
        )
        subprocess.run(["git", "commit", "-m", msg], cwd=PROJECT_ROOT, check=True)
        log.info(f"Committed {len(changed_desc)} page updates")
    except subprocess.CalledProcessError as e:
        log.error(f"git commit failed: exit={e.returncode}")
        return 2
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # pragma: no cover
        logging.getLogger("confluence-sync").exception(f"fatal: {e}")
        sys.exit(99)
