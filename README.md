# In a Big Forest

A small point-and-click item-trading game: walk around, earn or trade items,
and use them to unlock single-button minigames. Built to be finished in
under an hour, with minimal instructions — figuring out what to do next is
part of the fun.

## Download

**[⬇ Download for Linux](https://github.com/g-chris/in-a-big-forest/releases/latest/download/in-a-big-forest-linux-x86_64.tar.gz)**

No Python install needed — it's a self-contained binary.

```sh
tar -xzf in-a-big-forest-linux-x86_64.tar.gz
./in-a-big-forest
```

Your save slots are written next to the executable, so keep the extracted
folder around between play sessions.

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
[.github/workflows/release-linux.yml](.github/workflows/release-linux.yml),
which builds the Linux binary above and attaches it to a GitHub Release.
