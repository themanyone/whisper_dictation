#!/usr/bin/python
# -*- coding: utf-8 -*-
##
## Copyright (C) 2023-2026 Henry Kroll III <nospam@thenerdshow.com>
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
import os
import platform


def _get_system_info():
    """Return a short string like 'Debian GNU/Linux 13 (trixie) with bash'
    or 'Windows 11 with PowerShell', detected via stdlib."""
    os_name = platform.system()
    parts = []

    if os_name == "Windows":
        # Try to get a friendly Windows version
        win_ver = " ".join(v for v in platform.win32_ver() if v)
        parts.append(win_ver or "Windows")
        # Detect PowerShell availability
        if os.environ.get("PSModulePath"):
            parts.append("with PowerShell")
        else:
            parts.append("with cmd.exe")
    elif os_name == "Linux":
        try:
            info = platform.freedesktop_os_release()
            parts.append(info.get("PRETTY_NAME", "Linux"))
        except (AttributeError, OSError):
            parts.append("Linux")
        shell = os.environ.get("SHELL", "").rsplit("/", 1)[-1]
        if shell:
            parts.append(f"with {shell}")
    elif os_name == "Darwin":
        parts.append("macOS")
        shell = os.environ.get("SHELL", "").rsplit("/", 1)[-1]
        if shell:
            parts.append(f"with {shell}")
    else:
        parts.append(os_name)

    return " ".join(parts)


if __name__ == "__main__":
    info = _get_system_info()
    print(info)
