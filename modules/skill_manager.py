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
Skill loading for whisper_dictation — Agent Skills format.

Implements the https://agentskills.io open standard:

Skills are subdirectories containing a SKILL.md with YAML frontmatter
(name + description required, then Markdown body instructions).

Progressive disclosure (three tiers):
  1. Catalog — name + description injected at session start
  2. Instructions — full SKILL.md body loaded on activation
  3. Resources — scripts, references, assets loaded on demand

Scan paths (user-level only):
  - ~/.agents/skills/          (cross-client standard)
  - ~/.config/whisper_dictation/skills/  (client-specific)

Tools and skills are different:
  - Tools define callable functions (LLM function calling).
  - Skills define behavior context injected on demand.
"""

import logging
import os
import yaml

# ── Scan paths in priority order (first found wins for name collisions) ──
USER_CROSS = os.path.expanduser("~/.agents/skills")
USER_CLIENT = os.path.expanduser("~/.config/whisper_dictation/skills")

SCAN_PATHS = [USER_CROSS, USER_CLIENT]


def _parse_skill_dir(path):
    """Parse a skill directory: read SKILL.md, extract frontmatter + body.

    Returns a dict with keys:
      name, description, body, path, frontmatter (raw dict)
    or None if the directory doesn't contain a valid SKILL.md.
    """
    skill_md = os.path.join(path, "SKILL.md")
    if not os.path.isfile(skill_md):
        return None

    try:
        with open(skill_md, encoding="utf-8") as f:
            raw = f.read()
    except Exception as e:
        logging.warning(f"Failed to read {skill_md}: {e}")
        return None

    frontmatter = {}
    body = raw

    # Extract YAML frontmatter between --- delimiters
    if raw.startswith("---"):
        end = raw.find("---", 3)
        if end != -1:
            yaml_block = raw[3:end]
            body = raw[end + 3:].strip()
            # Lenient YAML parsing with fallback for unquoted colons
            try:
                frontmatter = yaml.safe_load(yaml_block) or {}
            except yaml.YAMLError:
                # Fallback: try wrapping values with colons in quotes
                try:
                    import re as _re
                    fixed = _re.sub(
                        r'(description|license|compatibility):\s*(.+)',
                        lambda m: f'{m.group(1)}: "{m.group(2).strip()}"'
                        if ":" in m.group(2) else m.group(0),
                        yaml_block,
                    )
                    frontmatter = yaml.safe_load(fixed) or {}
                except yaml.YAMLError:
                    logging.warning(f"Unparseable YAML frontmatter in {skill_md}")
                    return None

    if not isinstance(frontmatter, dict):
        frontmatter = {}

    name = frontmatter.get("name", os.path.basename(path))
    description = frontmatter.get("description", "")

    if not description:
        logging.warning(f"Skill {path} has no description — skipping")
        return None

    return {
        "name": name,
        "description": description,
        "body": body,
        "path": path,
        "frontmatter": frontmatter,
    }


def load_skills():
    """Discover skills across all scan paths.

    Returns a list of skill dicts ordered by scan path priority.
    Within each path, skills are sorted by name.
    Name collisions: first path wins, within same path first found wins.
    """
    seen = set()
    skills = []
    for base in SCAN_PATHS:
        if not os.path.isdir(base):
            continue
        # Scan first-level subdirectories for SKILL.md
        for entry in sorted(os.listdir(base)):
            skill_dir = os.path.join(base, entry)
            if not os.path.isdir(skill_dir):
                continue
            if entry in (".git", "node_modules", "__pycache__"):
                continue
            parsed = _parse_skill_dir(skill_dir)
            if parsed is None:
                continue
            # Deduplicate by name (first path wins)
            if parsed["name"] in seen:
                logging.debug(f"Skill '{parsed['name']}' shadowed by higher-priority path")
                continue
            seen.add(parsed["name"])
            # List bundled resources
            resources = []
            for sub in ("scripts", "references", "assets"):
                sub_path = os.path.join(skill_dir, sub)
                if os.path.isdir(sub_path):
                    resources.append(sub)
            parsed["resources"] = resources
            skills.append(parsed)
    return skills


def format_catalog(skills):
    """Format a skill catalog for injection into the system prompt.

    Returns a string listing each skill's name and description,
    or an empty string if no skills are available.
    """
    if not skills:
        return ""
    parts = [
        "## Available Skills",
        "",
        "The following skills are available. When a task matches a skill's",
        "description, call the `load_skill` function to load its full",
        "instructions into context.",
        "",
    ]
    for s in skills:
        desc_line = s["description"].replace("\n", " ").strip()
        parts.append(f"- **{s['name']}**: {desc_line}")
    return "\n".join(parts)


def load_skill_body(skills, name):
    """Return the full SKILL.md body for a skill by name.

    Used as the handler for the ``load_skill`` tool — the LLM calls this
    when it determines a skill is relevant.

    Returns the body text, or None if not found.
    """
    for s in skills:
        if s["name"] == name:
            resources = s.get("resources", [])
            body = s["body"]
            if resources:
                body += "\n\nBundled resources: " + ", ".join(resources)
            return body
    return None
