# In a Big Forest

A small point-and-click item-trading game: walk around, earn or trade items,
and use them to unlock single-button minigames. Built to be finished in
under an hour, with minimal instructions — figuring out what to do next is
part of the fun.

## Download

No Python install needed — these are self-contained binaries. Your save
slots are written next to the executable, so keep the extracted folder
around between play sessions.

**[⬇ Linux](https://github.com/g-chris/in-a-big-forest/releases/latest/download/in-a-big-forest-linux-x86_64.tar.gz)**

```sh
tar -xzf in-a-big-forest-linux-x86_64.tar.gz
./in-a-big-forest
```

**[⬇ Windows](https://github.com/g-chris/in-a-big-forest/releases/latest/download/in-a-big-forest-windows-x86_64.zip)**

Unzip, then double-click `in-a-big-forest.exe`. Windows will likely show a
"Windows protected your PC" SmartScreen warning the first time, since the
exe isn't signed — click **More info** → **Run anyway**.

**[⬇ macOS (Apple Silicon)](https://github.com/g-chris/in-a-big-forest/releases/latest/download/in-a-big-forest-macos-arm64.zip)**

Unzip, then **right-click → Open** on `in-a-big-forest` the first time (a
plain double-click will get blocked by Gatekeeper since the app isn't
notarized). Intel Macs aren't built yet — ask if you need one.

## Controls

- **Move:** arrow keys or WASD
- **Interact / advance dialogue:** Space
- **Inventory:** I
- **Save (while inventory is open):** S
- Minigames each use just one or two keys — the game won't tell you which;
  that's the challenge.

## Running from source

```sh
git clone https://github.com/g-chris/in-a-big-forest.git
cd in-a-big-forest
pip install -r requirements.txt
python3 game.py
```

## Development

See [CONVENTIONS.txt](CONVENTIONS.txt) for the project's design philosophy
and the checklists to follow when adding tiles or minigames. Pushing a tag
like `v0.1.0` (`git tag v0.1.0 && git push origin v0.1.0`) triggers
[.github/workflows/release.yml](.github/workflows/release.yml), which
builds the Linux/Windows/macOS binaries above and attaches them to a
GitHub Release.
