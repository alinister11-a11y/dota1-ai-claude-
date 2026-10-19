# wc3-dota: play DotA (Warcraft III 1.27b) against Claude

An MCP server plus a patched map (`maps/DotA_6_88f_AI_vs_Claude.w3x`) that lets **Claude** take one computer slot in your LAN game, pick a hero and play it against you live.

- The server uses only the Python standard library (Python 3.10+) and speaks MCP over stdio.
- Tools: `game_status`, `list_heroes`, `pick_hero`, `get_state`, `wait`, `act`, `lookup`.
- The `/play-dota` skill (`skill/play-dota/SKILL.md`) tells Claude how to run a game: get in, pick, play the loop, finish.

## Setup
1. **Map:** copy `maps/DotA_6_88f_AI_vs_Claude.w3x` into `Warcraft III\Maps\Scenario\`.
2. **Server:** copy this `mcp-server` folder into your Warcraft III folder as `ClaudeMCP`. The server finds the game folder as its own parent folder. If you keep it somewhere else, set the environment variable `WC3_DIR` to your Warcraft III folder.
3. **Allow the map to read Claude's commands** by setting this registry value, then restart Warcraft III:
   ```
   HKCU\Software\Blizzard Entertainment\Warcraft III  →  "Allow Local Files" (DWORD) = 1
   ```
4. **Register the server** in Claude Code. Copy `example.mcp.json` to your Warcraft III folder as `.mcp.json` and fix the two paths.
5. **Skill (optional):** copy `skill/play-dota` to `<Warcraft III>\.claude\skills\play-dota`.

## Play
1. Open Claude Code in the Warcraft III folder and type `/play-dota` (or "let's play DotA").
2. In Warcraft III, open **Local Area Network → Create Game → "DotA 6.88f AI vs Claude"**.
   - You must be the **first human slot** (normally the host), because the map reads Claude's commands on that PC.
   - Set one slot on the **other team** to *Computer*. The first computer on the enemy team is Claude. Other slots can be friends or normal computers.
   - Start and type a mode (`-ap`, `-sd`, ...). Claude picks within 75 s of game time. Otherwise the map's AI random-picks for that slot.

In game, Claude's slot shows as **Claude** and Claude chats as `[All] Claude: ...`. Anything you type in all-chat reaches Claude.

## How Claude controls the hero
- **auto** (default): the map's AI plays between Claude's orders (laning, farming, buying). Each order from Claude takes over for `holdtime` seconds.
- **manual**: Claude steers everything. A safety net walks the hero home below 20% HP.
- If Claude sends no commands for 150 s, the AI takes the hero back.
- Fair play: Claude sees only what its team sees. Enemies in fog are reported as "not visible".

## How it works
- `tools/patch_map.py` builds the map from a DotA 6.88f AI map. It:
  - wraps the map AI's "is computer" checks, so the AI leaves Claude's hero alone while Claude steers;
  - stops the AI from random-picking for Claude's slot until Claude has had time to pick;
  - injects `tools/bridge.j`;
  - lints the injected JASS. 1.27b silently refuses a map when a local shadows a global or a variable is named like a type.
- The bridge writes `CustomMapData\ClaudeBridge\state.txt` every 0.5 s and reads `cmd.txt`, using Warcraft III Preload file I/O. Commands are synced to every LAN client through game-cache sync.
- `data/kb.json` (heroes, skills, items) is built from the map by `tools/build_kb.py`.
- Other tools:
  - `tools/mpq.py`: a read-only MPQ extractor, with PKWare DCL, zlib and bzip2 support.
  - `tools/compact.py`: rebuilds an MPQ, replaces files and re-keys position-encrypted blocks.

Rebuild the map (run from the Warcraft III folder; the patcher refuses to overwrite an existing output):
```bash
python -I ClaudeMCP\tools\patch_map.py . Maps\Scenario\DotA_6_88f_AI_Superpower_EN.w3x Maps\Scenario\DotA_6_88f_AI_vs_Claude.w3x
```

## 1.27b pitfalls found while building it
- Preload paths resolve under `<Warcraft III>\CustomMapData\`.
- Reading files needs **Allow Local Files = 1**.
- A Preload file that contains an empty string literal `""`, or a string longer than about 260 characters, crashes Storm.dll.
- After replacing a file inside an MPQ, its CRC32 in `(attributes)` must be updated.
- The LAN map list shows the name from the HM3W file header, not the one in `war3map.w3i`.

## Known limits
- Tested on LAN with one human and computers. Two human PCs have not been tested.
- Claude reacts in seconds, not milliseconds. Fine micro comes from the map AI (auto mode) and the auto-retreat.
- The server log is written to `ClaudeMCP\logs\server.log`.
