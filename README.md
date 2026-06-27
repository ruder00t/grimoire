=== Grimoire ====

A small command-line tool for storing and recalling shell commands. Commands
are grouped into named chapters (typically one per tool), and reusable
variables like `{{RHOSTS}}` or `{{URL}}` are filled in when a command is
rendered.

=== Requirements ===

- Python 3.8 or newer (standard library only)
- A clipboard tool (`wl-copy`, `xclip`, `xsel`, or `pbcopy`). The install script
  sets one up for you if you don't have one.

=== Installation ===

Clone the repository and run the install script. It links `grim` onto your
PATH (into `~/.local/bin`) and installs a clipboard tool if you don't have one:

```
git clone https://github.com/YOUR-USERNAME/grimoire.git
cd grimoire
bash install.sh
```

If `~/.local/bin` is not on your PATH, the script prints the one line to add to
your shell config. To remove the link later, run `bash install.sh --uninstall`.

The install uses a symlink, so `git pull` updates the installed command
automatically.

=== Manual install ===

If you'd rather not run the script:

```
chmod +x grim.py
mkdir -p ~/.local/bin
ln -s "$PWD/grim.py" ~/.local/bin/grim
```

If `~/.local/bin` is not already on your PATH, add this line to your shell
config (`~/.bashrc` or `~/.zshrc`) and start a new shell:

```
export PATH="$HOME/.local/bin:$PATH"
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
