==== GRIMOIRE =====

(Designed for Kali and Debian disto's)


A small command-line tool for storing and recalling shell commands. Commands
are grouped into named chapters (typically one per tool), and reusable
variables like `{{RHOSTS}}` or `{{URL}}` are filled in when a command is
rendered.

=== Requirements ===

- Python 3.8 or newer (standard library only)
- A clipboard tool (`wl-copy`, `xclip`, `xsel`, or `pbcopy`). The install script
  sets one up for you if you don't have one.

=== Installation ===

Clone the repository and run the install script. Run it **without** `sudo` — it
asks for your password only if it actually needs root (to write
`/usr/local/bin` or install a clipboard package):

```
git clone https://github.com/YOUR-USERNAME/grimoire.git
cd grimoire
bash install.sh
```

This places a small launcher at `/usr/local/bin/grim` that runs `grim.py` from
the repository, and installs a clipboard tool if you don't have one. Because
`/usr/local/bin` is on the default PATH, `grim` works immediately. `grim.py`
itself is never modified, so `git pull` keeps the command up to date. To remove
it, run `bash install.sh --uninstall`.

To install into a directory you own instead (no root needed), set `BINDIR`:

```
BINDIR="$HOME/.local/bin" bash install.sh
```

(If that directory isn't on your PATH, the script tells you the line to add.)

=== Manual install ===

Create the launcher yourself:

```
printf '#!/bin/sh\nexec python3 "%s" "$@"\n' "$PWD/grim.py" | sudo tee /usr/local/bin/grim >/dev/null
sudo chmod +x /usr/local/bin/grim
```

Confirm it works:

```
grim --help
```

Data is stored in `~/.config/grimoire/grimoire.json`.

==== Usage ===

```
grim set rhosts 10.10.10.10           # set a variable
grim add 'sudo nmap -sVC {{RHOSTS}}'  # add a command (prompts for a chapter)
grim show                             # print every command in every chapter
grim chapters                         # list chapters and their counts
grim get nmap                         # pick a numbered command and copy it
grim options                          # show variables and their current values
```

Available variables: `url`, `lhost`, `rhosts`, `ad`, `wordlist`, `user`,
`pass`, `userlist`, `passlist`. Variable names are case-insensitive. Single
braces are always literal, so `awk '{print $1}'` needs no escaping.

=== Sharing command packs ===

Export your grimoire to the current directory:

```
grim --export
```

Import a pack, merging it into your chapters. Existing chapters and commands
are kept, and duplicates are skipped, so importing the same file twice changes
nothing:

```
grim --import path/to/pack.json
```

A pack is a JSON file shaped like this:

```json
{
  "chapters": {
    "nmap": ["sudo nmap -sVC {{RHOSTS}}", "nmap -p- {{RHOSTS}}"],
    "smb":  ["smbclient -L //{{RHOSTS}}/ -N"]
  }
}
```

A file produced by `grim --export` (which also carries a `variables` block)
imports cleanly as well.
