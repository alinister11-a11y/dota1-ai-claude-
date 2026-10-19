# heroport: build the Monkey King + Mars map

This pipeline builds `maps/DotA_688_AI_Superpower_MK_Mars.w3x` from two inputs:
- `maps/DotA_6_88f_AI_Superpower_EN.w3x`, the base map;
- DracoL1ch's **DotA 7.03R11** (`DotA_Allstars_7.03R11.w3x`, 175 MB from EpicWar, map 349985), the source of the models, icons, stats and tooltips. It is not included in this repo.

The spells are re-implemented in plain JASS in `pz_heroes.j`, because the 7.03R11 spell code depends on a 1.26a memory hack.

The build is reproducible: running it on the inputs above produces a byte-identical copy of the released map. SHA-256 of the result:
`9795398D7FA10866449E10E42287737A3281F02517AE01423251FA69608E3BED`

## Requirements
- Python 3.10+ (standard library only). The MPQ and SLK helpers are in `../mcp-server/tools`.
- The Warcraft III 1.27b game folder (for `common.j`/`Blizzard.j` lint and for texture checks). Set `WC3_DIR` to that folder.

## Build
```bash
python -I collect_assets.py DotA_Allstars_7.03R11.w3x assets seeds.txt
```
```bash
python -I build_port.py ../maps/DotA_6_88f_AI_Superpower_EN.w3x DotA_Allstars_7.03R11.w3x assets pz_heroes.j out.w3x --name "DotA AI 6.88 MK+Mars"
```
- `collect_assets.py` pulls 74 model, texture and icon files out of a map that has no `(listfile)`. It starts from seed names and follows MDX texture (`TEXS`) and particle (`PREM`) references, plus portrait and disabled-icon name variants.
- `--test` builds a debug version:
  - on-screen `[PZ]` logs, including a 30 s economy readout;
  - the first bot picks are forced to Monkey King and Mars;
  - all slots are set to Computer;
  - the chat command `-pztest` (or `-pztest mars`) runs an automatic check of every spell.
- `--stage N`, `--units ...` and `--parts LVBRPGE` turn individual parts on and off. They were used to bisect crashes.

## Load test
```powershell
$env:WC3_DIR = "C:\Games\Warcraft III"; powershell -File loadtest.ps1 -Map Maps\Scenario\out.w3x
```
It launches `war3.exe -window -loadfile`, waits, and reports whether the Blizzard crash reporter appeared, along with the crash text. `ui.ps1` is the small mouse and keyboard driver used to host LAN games with bots. Note that on a display scaled to 125%, Warcraft III reads the cursor at 1.25× the position set.

## What the build changes
- **Object data:** SLK rows are appended for the heroes, 18 abilities, 2 draft-selector units and 5 dummy units. Txt profile sections are added for tooltips and icons, and both heroes go into the tavern sell lists.
- **Script:**
  - hero table entries 113 and 114 (`PZHeroTable`);
  - AI skill tables (`V5`);
  - item-build aliases (`BVE`);
  - hero-role filter (`JR7`);
  - random picks (`PZRandHero`);
  - normal economy: `Q5F`, `Q2F`, `OZ9` and `OA9` neutralized;
  - outnumbered-retreat threshold (`ME7` plus `PZThreat`).
- **Archive:** a fresh MPQ v1 is written by `wc3edit.write_mpq` with a complete `(listfile)`.

## Pitfalls found
- **`LX7`**, the hero-table function (about 1,400 lines), sits at a 1.27b compiler limit. About 30 extra lines crash loading, so keep it the same size and call a new function.
- **Hand-written dummy-unit SLK rows** crashed the game on `CreateUnit`. Copying an existing unit's rows (`o00G`) works.
- **The ANcl order string `acidbomb`** was never cast as a point order, while `shockwave` works.
- **`-loadfile` creates no computer players**, even when `war3map.w3i` marks slots as Computer. Bot tests need the LAN lobby.
- **The 6.88 map teleports every newly created hero to its base** about 1 s after creation.
- **Single-player pauses while the window is in the background.**
