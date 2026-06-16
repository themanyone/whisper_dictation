#!/usr/bin/python
# -*- coding: utf-8 -*-
##
## Copyright (C) 2026 Henry Kroll III <nospam@thenerdshow.com>
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
## MA 02110-1301, USA.
##
"""
Scan a project directory and generate AGENTS.md.

Walks non-hidden directories (depth ≤ 2), reads text files within
a half-context limit per file, and builds a Markdown guide covering
overview, license, file layout, file inventory, dependencies, service
endpoints, and code conventions.
"""

import os
import re


def is_text_file(path):
    """Return True if path is a text file (not binary)."""
    # Known text extensions — fast path
    text_exts = {".py", ".sh", ".md", ".txt", ".json", ".yml", ".yaml",
                 ".toml", ".cfg", ".conf", ".ini", ".xml", ".html",
                 ".css", ".js", ".ts", ".c", ".h", ".cpp", ".hpp",
                 ".rs", ".go", ".rb", ".pl", ".lua", ".php", ".R",
                 ".r", ".m", ".swift", ".kt", ".gradle", ".env",
                 ".gitignore", ".dockerfile", ".editorconfig",
                 ".flake8", ".isort.cfg", ".mailmap", ".project",
                 ".pydevproject"}
    ext = os.path.splitext(path)[1].lower()
    base = os.path.basename(path).lower()
    if ext in text_exts:
        return True
    if base in ("license", "makefile", "dockerfile", "requirements.txt",
                "gemfile", "cargo", "composer.json", "package.json",
                "pyproject.toml", "setup.py", "cmakelists.txt"):
        return True
    # Fallback: try to read as utf-8; if it contains null bytes, skip.
    try:
        with open(path, "rb") as f:
            raw = f.read(1024)
        return b"\0" not in raw
    except OSError:
        return False


def find_text_files(root, max_depth=2):
    """Walk non-hidden dirs up to *max_depth* and return text file paths."""
    skip_dirs = {".git", "__pycache__", ".ruff_cache",
                 ".github"}
    result = []
    root_len = len(os.path.normpath(root).split(os.sep))
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune hidden and skip dirs
        dirnames[:] = [d for d in dirnames
                       if not d.startswith(".") and d not in skip_dirs]
        depth = len(os.path.normpath(dirpath).split(os.sep)) - root_len
        if depth > max_depth:
            dirnames.clear()
            continue
        for fn in sorted(filenames):
            if fn.startswith("."):
                continue
            full = os.path.join(dirpath, fn)
            if is_text_file(full):
                result.append(full)
    return result


def build_file_tree(root):
    """Build an ASCII directory tree of the project."""
    lines = []
    lines.append(os.path.basename(root) + "/\n")
    skip_dirs = {".git", "__pycache__", ".ruff_cache"}
    entries = sorted(os.listdir(root))
    for i, entry in enumerate(entries):
        full = os.path.join(root, entry)
        if entry.startswith(".") or entry in skip_dirs:
            continue
        prefix = "└── " if i == len(entries) - 1 else "├── "
        lines.append(prefix + entry + ("/\n" if os.path.isdir(full) else "\n"))
        if os.path.isdir(full):
            sub = sorted(os.listdir(full))
            for j, sub_e in enumerate(sub):
                sub_f = os.path.join(full, sub_e)
                if sub_e.startswith("."):
                    continue
                sp = "    " if i == len(entries) - 1 else "│   "
                sp += "└── " if j == len(sub) - 1 else "├── "
                lines.append(sp + sub_e + ("/" if os.path.isdir(sub_f) else "") + "\n")
    return "".join(lines)


def initialize_project(root=None, agents_path=None):
    """Scan *root* (default: CWD), write AGENTS.md, return True if written."""
    root = root or os.getcwd()
    agents_path = agents_path or os.path.join(root, "AGENTS.md")
    proj_name = os.path.basename(root)
    sections = []

    # ── Project name & overview ────────────────────────────────────────
    readme = os.path.join(root, "README.md")
    overview = f"{proj_name} — a project in this directory."
    if os.path.isfile(readme):
        with open(readme) as f:
            first = f.read(500)
        for line in first.splitlines():
            if line.startswith("# ") and not line.startswith("###"):
                overview = f"{proj_name} — {line.lstrip('# ').strip()}"
                break

    sections.append(f"# {proj_name} — Agent Guide\n")
    sections.append(f"## Project Overview\n")
    sections.append(overview + "\n")

    # ── License ───────────────────────────────────────────────────────
    license_path = os.path.join(root, "LICENSE")
    if os.path.isfile(license_path):
        with open(license_path) as f:
            lic = f.read(200)
        for line in lic.splitlines():
            if "GNU GENERAL PUBLIC LICENSE" in line:
                ver = line.split("Version")[-1].strip() if "Version" in line else ""
                sections.append(f"\n**License:** GNU GPL{ ' v' + ver if ver else '' }\n")
                break
        else:
            sections.append(f"\n**License:** See LICENSE file.\n")

    # ── Find all non-hidden text files (depth ≤ 2) ────────────────────
    text_files = find_text_files(root)
    file_info = {}
    for tf in text_files:
        rel = os.path.relpath(tf, root)
        with open(tf, errors="replace") as f:
            head = f.read(2000)  # half a context window per file
        lines = head.splitlines()
        shebang = lines[0] if lines and lines[0].startswith("#!") else None
        docstring = ""
        classes = []
        functions = []
        for line in lines:
            if line.startswith('"""') and not docstring:
                docstring = line.strip('"').strip()
            if line.startswith("class "):
                classes.append(line.split("(")[0].split(":")[0].strip())
            if line.startswith("def "):
                functions.append(line.split("(")[0].replace("def ", "").strip())
        file_info[rel] = {
            "shebang": shebang,
            "docstring": docstring,
            "classes": classes,
            "functions": functions,
        }

    # ── Detect external service URLs/ports across all text files ──────
    urls = set()
    ports = set()
    url_pattern = re.compile(r'(https?://[^\s"\')\]]+)')
    port_pattern = re.compile(r'\bport\s*[:=]\s*(\d+)', re.I)
    for tf in text_files:
        with open(tf, errors="replace") as f:
            src = f.read(4000)
        for m in url_pattern.finditer(src):
            u = m.group(1).rstrip("/")
            if "127.0.0.1" in u or "localhost" in u:
                urls.add(u)
        for m in port_pattern.finditer(src):
            ports.add(m.group(1))

    # ── requirements.txt ──────────────────────────────────────────────
    req_path = os.path.join(root, "requirements.txt")
    deps = []
    if os.path.isfile(req_path):
        with open(req_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    deps.append(line)

    # ── Directory structure ────────────────────────────────────────────
    sections.append("\n## Architecture & File Layout\n")
    sections.append("```\n")
    sections.append(build_file_tree(root))
    sections.append("```\n")

    # ── File inventory ─────────────────────────────────────────────────
    sections.append("\n## File Inventory\n")
    sections.append("| File | Shebang | Purpose | Key Classes | Key Functions |\n")
    sections.append("|---|---|---|---|---|\n")
    for rel, info in sorted(file_info.items()):
        purpose = info["docstring"][:80] if info["docstring"] else ""
        cls = ", ".join(info["classes"][:3]) if info["classes"] else ""
        funcs = ", ".join(info["functions"][:4]) if info["functions"] else ""
        sheb = info["shebang"] if info["shebang"] else ""
        sections.append(f"| `{rel}` | `{sheb}` | {purpose} | {cls} | {funcs} |\n")

    # ── Dependencies ──────────────────────────────────────────────────
    if deps:
        sections.append("\n## Dependencies\n")
        sections.append("```\n")
        for d in deps:
            sections.append(d + "\n")
        sections.append("```\n")

    # ── External services ─────────────────────────────────────────────
    if urls or ports:
        sections.append("\n## Service Endpoints Detected\n")
        if urls:
            sections.append("**URLs:**\n")
            for u in sorted(urls):
                sections.append(f"- `{u}`\n")
        if ports:
            sections.append("**Ports:**\n")
            for p in sorted(ports):
                sections.append(f"- `{p}`\n")

    # ── Code conventions (inferred from source) ───────────────────────
    sections.append("\n## Code Conventions\n")
    shebangs_seen = set()
    encodings_seen = set()
    for rel, info in file_info.items():
        if info["shebang"]:
            shebangs_seen.add(info["shebang"])
        full = os.path.join(root, rel)
        with open(full, errors="replace") as f:
            f.readline()
            second = f.readline()
            if "# -*- coding:" in second:
                encodings_seen.add(second.strip())
    if shebangs_seen:
        sections.append(f"- **Shebang:** `{'`, `'.join(sorted(shebangs_seen))}`\n")
    if encodings_seen:
        for e in encodings_seen:
            sections.append(f"- **Encoding:** `{e}`\n")
    sections.append("- **Naming:** Classes use `CamelCase`, functions use `snake_case`\n")

    content = "".join(sections)
    if os.path.exists(agents_path):
        with open(agents_path) as f:
            existing = f.read()
        if existing == content:
            return False  # already up to date
    with open(agents_path, "w") as f:
        f.write(content)
    return True  # written


if __name__ == "__main__":
    import sys
    root = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    written = initialize_project(root=root)
    print("AGENTS.md written." if written else "AGENTS.md is up to date.")
