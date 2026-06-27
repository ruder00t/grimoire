#!/usr/bin/env python3
"""
Grimoire: store and recall command-line commands with reusable variables.

Commands are grouped into named chapters (typically one per tool). Session
variables such as {{LHOST}}, {{RHOSTS}}, {{URL}} or {{AD}} are substituted
in when a command is rendered. Variable names are case-insensitive, and
single braces are always literal, so 'awk "{print $1}"' needs no escaping.

Usage:
    grim add '<command>'        Add a command (prompts for a chapter)
    grim show                   Print every command in every chapter
    grim chapters               List chapters and their command counts
    grim get <chapter>          Pick a numbered command from a chapter
    grim set <name> <value>     Set a session variable
    grim options                Show all session variables and their values
    grim --export               Copy the data file to the current directory
    grim --import <file>        Merge a JSON command pack (format in --help)
    grim --help                 Show this help

Data lives in ~/.config/grimoire/grimoire.json
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

LOGO = r"""
    +==========================================+
    |                                          |
    |          G  R  I  M  O  I  R  E          |
    |                                          |
    +==========================================+
"""

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "grimoire"
DATA_FILE = CONFIG_DIR / "grimoire.json"

MAX_COMMANDS = 20
DEFAULT_VARIABLES = {
    "url": "",
    "lhost": "",
    "rhosts": "",
    "ad": "",
    "wordlist": "",
    "user": "",
    "pass": "",
    "userlist": "",
    "passlist": "",
}
TOKEN_RE = re.compile(r"\{\{(\w+)\}\}")

CLIPBOARD_BACKENDS = [
    ["wl-copy"],
    ["xclip", "-selection", "clipboard"],
    ["xsel", "--clipboard", "--input"],
    ["pbcopy"],
]


def load_data():
    if not DATA_FILE.exists():
        data = {"variables": dict(DEFAULT_VARIABLES), "chapters": {}}
        save_data(data)
        return data

    try:
        with DATA_FILE.open(encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        sys.exit(f"grim: could not read {DATA_FILE}: {exc}")

    data.setdefault("variables", dict(DEFAULT_VARIABLES))
    data.setdefault("chapters", {})

    added = False
    for name, value in DEFAULT_VARIABLES.items():
        if name not in data["variables"]:
            data["variables"][name] = value
            added = True
    if added:
        save_data(data)

    return data


def save_data(data):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=CONFIG_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        os.replace(tmp_path, DATA_FILE)
    except OSError as exc:
        os.unlink(tmp_path)
        sys.exit(f"grim: could not write {DATA_FILE}: {exc}")


def substitute(command, variables):
    lookup = {k.lower(): v for k, v in variables.items()}
    unset = set()

    def replace(match):
        name = match.group(1).lower()
        if name not in lookup:
            return match.group(0)
        if lookup[name] == "":
            unset.add(name)
        return lookup[name]

    return TOKEN_RE.sub(replace, command), sorted(unset)


def copy_to_clipboard(text):
    for backend in CLIPBOARD_BACKENDS:
        if shutil.which(backend[0]):
            try:
                subprocess.run(backend, input=text.encode("utf-8"), check=True)
                return backend[0]
            except (subprocess.CalledProcessError, OSError):
                continue
    return None


def ask(prompt):
    try:
        return input(prompt).strip()
    except (KeyboardInterrupt, EOFError):
        print()
        sys.exit("grim: cancelled.")


def cmd_add(args, data):
    command = args.command
    chapters = data["chapters"]

    tokens = {m.lower() for m in TOKEN_RE.findall(command)}
    known = sorted(t for t in tokens if t in data["variables"])
    unknown = sorted(t for t in tokens if t not in data["variables"])
    if known:
        print(f"Detected variables: {', '.join(known)}")
    if unknown:
        print(f"Not (yet) variables, left as-is: {', '.join('{{%s}}' % t for t in unknown)}")

    if chapters:
        print(f"Existing chapters: {', '.join(sorted(chapters))}")
    else:
        print("No chapters yet.")

    chapter = ask("Which chapter? (new or existing name): ")
    if not chapter:
        sys.exit("grim: no chapter given, nothing added.")

    bucket = chapters.setdefault(chapter, [])

    if len(bucket) >= MAX_COMMANDS:
        print(f"Chapter '{chapter}' is full ({MAX_COMMANDS}/{MAX_COMMANDS}):")
        for i, cmd in enumerate(bucket, 1):
            print(f"  {i:>2}. {cmd}")
        choice = ask(f"Slot to overwrite (1-{MAX_COMMANDS}), or Enter to cancel: ")
        if not choice:
            sys.exit("grim: cancelled, nothing changed.")
        if not choice.isdigit() or not 1 <= int(choice) <= len(bucket):
            sys.exit("grim: invalid slot, nothing changed.")
        bucket[int(choice) - 1] = command
        save_data(data)
        print(f"Replaced slot {choice} in '{chapter}'.")
        return

    bucket.append(command)
    save_data(data)
    print(f"Added to '{chapter}' ({len(bucket)}/{MAX_COMMANDS}).")


def cmd_show(args, data):
    chapters = data["chapters"]
    if not chapters:
        print("No chapters yet. Add one with:  grim add '<command>'")
        return
    for name in sorted(chapters):
        bucket = chapters[name]
        print(f"{name}:")
        for i, cmd in enumerate(bucket, 1):
            print(f"  {i:>2}. {cmd}")
        print()


def cmd_chapters(args, data):
    chapters = data["chapters"]
    if not chapters:
        print("No chapters yet. Add one with:  grim add '<command>'")
        return
    for name in sorted(chapters):
        print(f"{name} ({len(chapters[name])})")


def _emit(raw, variables):
    rendered, unset = substitute(raw, variables)
    for name in unset:
        print(f"  warning: {name} is unset", file=sys.stderr)
    print(rendered)
    backend = copy_to_clipboard(rendered)
    if backend:
        print(f"(copied to clipboard via {backend})")
    else:
        print("(no clipboard tool found -- copy the line above, or install "
              "xclip / xsel / wl-clipboard to enable copying)")


def cmd_get(args, data):
    chapters = data["chapters"]

    if not args.chapter:
        if not chapters:
            print("No chapters yet. Add one with:  grim add '<command>'")
            return
        print("Chapters:")
        for name in sorted(chapters):
            print(f"  {name} ({len(chapters[name])})")
        print("\nPick from one with:  grim get <chapter>")
        return

    chapter = args.chapter
    if chapter not in chapters:
        available = ", ".join(sorted(chapters)) or "(none)"
        sys.exit(f"grim: no chapter '{chapter}'. Available: {available}")

    bucket = chapters[chapter]
    if not bucket:
        sys.exit(f"grim: chapter '{chapter}' is empty.")
    print(f"{chapter}:")
    for i, cmd in enumerate(bucket, 1):
        print(f"  {i:>2}. {cmd}")

    choice = ask(f"Which number? (1-{len(bucket)}): ")
    if not choice.isdigit() or not 1 <= int(choice) <= len(bucket):
        sys.exit("grim: invalid choice.")

    print()
    _emit(bucket[int(choice) - 1], data["variables"])


def cmd_options(args, data):
    variables = data["variables"]
    if not variables:
        print("No variables set.")
        return
    extras = sorted(name for name in variables if name not in DEFAULT_VARIABLES)
    names = [n for n in DEFAULT_VARIABLES if n in variables] + extras
    width = max(len(name) for name in names)
    for name in names:
        value = variables[name]
        print(f"  {name:<{width}}  =  {value if value else '(unset)'}")


def cmd_import(path, data):
    src = Path(path)
    if not src.exists():
        sys.exit(f"grim: no such file: {src}")
    try:
        with src.open(encoding="utf-8") as fh:
            incoming = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        sys.exit(f"grim: could not read {src}: {exc}")

    chapters = incoming.get("chapters", incoming)
    if not isinstance(chapters, dict):
        sys.exit("grim: file has no 'chapters' object to import.")

    added_cmds = added_chaps = 0
    for name, cmds in chapters.items():
        if not isinstance(cmds, list):
            continue
        is_new = name not in data["chapters"]
        bucket = data["chapters"].setdefault(name, [])
        if is_new:
            added_chaps += 1
        for cmd in cmds:
            if cmd not in bucket:
                bucket.append(cmd)
                added_cmds += 1

    for vname, vval in incoming.get("variables", {}).items():
        data["variables"].setdefault(vname, vval)

    save_data(data)
    print(f"Imported {added_cmds} commands across {added_chaps} new chapters.")


def cmd_set(args, data):
    name = args.name.lower()
    value = " ".join(args.value)
    data["variables"][name] = value
    save_data(data)
    label = "set" if value else "cleared"
    print(f"{name} {label}" + (f" -> {value}" if value else ""))


def build_parser():
    parser = argparse.ArgumentParser(
        prog="grim",
        description=LOGO + "\nGrimoire: store and recall command-line commands with reusable variables.",
        epilog=(
            "examples:\n"
            "  grim set rhosts 10.10.10.40\n"
            "  grim add 'sudo nmap -sVC {{RHOSTS}}'\n"
            "  grim get nmap\n"
            "  grim show\n"
            "  grim chapters\n"
            "\n"
            "variables:\n"
            "  Commands may contain {{NAME}} tokens that are filled in when rendered.\n"
            "  Change one with:    grim set url example.com\n"
            "  Available names:    " + ", ".join(DEFAULT_VARIABLES) + "\n"
            "  See current values: grim options\n"
            "\n"
            "importing:\n"
            "  'grim --import FILE' merges a JSON file into your grimoire. Commands\n"
            "  are added to the chapters named in the file; existing chapters and\n"
            "  commands are kept, and duplicates are skipped, so importing the same\n"
            "  file twice changes nothing. The file must look like this:\n"
            "\n"
            "    {\n"
            "      \"chapters\": {\n"
            "        \"nmap\": [\"sudo nmap -sVC {{RHOSTS}}\", \"nmap -p- {{RHOSTS}}\"],\n"
            "        \"smb\":  [\"smbclient -L //{{RHOSTS}}/ -N\"]\n"
            "      }\n"
            "    }\n"
            "\n"
            "  A file written by 'grim --export' (which also carries a \"variables\"\n"
            "  block) imports cleanly as well.\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="copy the data file (commands + settings) to the current directory",
    )
    parser.add_argument(
        "--import",
        dest="import_file",
        metavar="FILE",
        help="merge a JSON command pack into your grimoire (format shown below)",
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")
    parser._optionals.title = "other commands"

    p_add = sub.add_parser("add", help="add a command (prompts for a chapter)")
    p_add.add_argument("command", help="the command, quoted, e.g. 'nmap {{RHOSTS}}'")
    p_add.set_defaults(func=cmd_add)

    p_show = sub.add_parser("show", help="print every command in every chapter")
    p_show.set_defaults(func=cmd_show)

    p_chapters = sub.add_parser("chapters", help="list chapters and their command counts")
    p_chapters.set_defaults(func=cmd_chapters)

    p_set = sub.add_parser("set", help="set a session variable")
    p_set.add_argument("name", help="variable name, e.g. rhosts")
    p_set.add_argument("value", nargs="+", help="value to store")
    p_set.set_defaults(func=cmd_set)

    p_get = sub.add_parser("get", help="pick a numbered command from a chapter and copy it")
    p_get.add_argument("chapter", nargs="?", help="chapter to pick from")
    p_get.set_defaults(func=cmd_get)

    p_options = sub.add_parser("options", help="show all session variables and their values")
    p_options.set_defaults(func=cmd_options)

    return parser


def cmd_export():
    load_data()
    dest = Path.cwd() / "grimoire.json"
    if dest.exists():
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        dest = Path.cwd() / f"grimoire-{stamp}.json"
    try:
        shutil.copy2(DATA_FILE, dest)
    except OSError as exc:
        sys.exit(f"grim: export failed: {exc}")
    print(f"Exported to {dest}")


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.export:
        cmd_export()
        return
    if args.import_file:
        cmd_import(args.import_file, load_data())
        return
    if not getattr(args, "func", None):
        parser.print_help()
        return
    data = load_data()
    args.func(args, data)


if __name__ == "__main__":
    main()
