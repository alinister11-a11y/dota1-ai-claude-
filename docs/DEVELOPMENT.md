# Development notes

This project was built on a low-end Windows laptop (ASUS X555LI) running Warcraft III 1.27b. The work was done in Claude Code sessions from 16 to 19 October 2026. Every result below was checked in a real game, either through LAN games against bots or through an in-map self-test.

## Goal
Play DotA 1 against **computer bots** with **Dota 2 heroes**, on the classic 1.27b client, and play against **Claude itself** as an opponent.

## 1. The Superpower crash: a hidden compiler limit
**Problem:** the "Superpower" builds of DotA 6.88f AI crashed the game during Create Game or loading, with `ACCESS_VIOLATION` at `Game.dll+0x139cea`. The crash reports were in `%TEMP%\BlizzardError`.

**What was ruled out:** the translation. The untranslated version crashed too.

**Cause:** the AI function `N9F` holds a hero `if/elseif` chain of about 110 branches with very large conditions, and it is already at a limit of the 1.27b script compiler.
- Inserting a single empty `elseif` before the complex branches crashes the game, while the same dummy branch at the end of the chain loads.
- Other long chains made of simple branches load fine.

**Fix:** split the chain in two behind a local flag.

## 2. Chinese-platform maps on vanilla Warcraft III
**Problem:** a 66.9 MB Chinese DotA 6.83d silently dropped back to the menu.

**Cause:** its script declares YDWE "japi" natives that only the KK/11 platforms provide.

**Fix:**
- The natives were replaced with JASS stubs.
- The archive held 57 MB of unreferenced protector padding and used 16 MB sectors. It was rebuilt at 9 MB, and position-keyed (FIX_KEY) encrypted blocks were re-keyed for their new positions.

## 3. Why DracoL1ch's 7.0x maps can't run on 1.27b
DracoL1ch's 7.00e6, 7.03R11 and 7.07a1 maps all carry a memory hack aimed at 1.26a. It works like this:
- AI natives such as `IgnoredUnits` and `AttackMoveXY` are re-declared to read and write memory.
- x86 shellcode is written into the game process.
- The Game.dll base is computed from a pointer (`ptr-0x951060`).
- A `ForForce` exploit runs the payload.

Removing the hack gets as far as the loading screen, then gives a black screen with no gold, because the core setup depends on it. These maps also contain **no computer AI at all**.

A wide search found no public DotA AI map with Dota 2 heroes for any patch. It covered EpicWar, Hive Workshop, GitHub, dotaproject, and Chinese, Vietnamese and Russian sites. So the plan became a port: take Monkey King and Mars into the 6.88 AI map.

## 4. Porting Monkey King and Mars
- **Assets:** 7.03R11 ships without a `(listfile)`. The asset collector starts from names found in the script and the SLK tables, then crawls MDX texture and particle references.
  - It found 74 files, 1.2 MB in total.
  - Every texture resolves either to a ported file or to the base game archives.
  - All models are classic MDX version 800.
- **Object data:** both maps are SLK-optimized. Rows are appended to `UnitData`, `UnitBalance`, `UnitUI`, `UnitAbilities`, `UnitWeapons` and `AbilityData`, and txt profile sections are added. Two bugs were found by bisecting with stage and part flags:
  - hand-written dummy-unit rows crashed `CreateUnit`, so they are now copies of an existing map dummy;
  - adding about 30 lines to the 1,400-line hero-table function `LX7` crashed loading (a second compiler limit), so the entries live in a new function called from one line.
- **Spells:** about 900 lines of plain JASS, using hashtables, timers and dummy casters. They include:
  - stuns (Storm Bolt based) and slows;
  - knockback with pathing checks;
  - line and cone hit tests;
  - a skewer that detects pinning against a tree, terrain or building (trees are detected by issuing a harvest order to a hidden worker);
  - perch and leap arcs using the Crow Form fly-height trick;
  - channel-time scaling;
  - attack-count charges;
  - soldier rings;
  - an arena that holds units inside or outside, using a per-unit inside/outside state;
  - frontal damage blocking that restores the life an attack removed, with a temporary life bonus to avoid overkill.
- **AI:**
  - skill learning goes through the map's own ability tables;
  - item builds are aliased to similar heroes;
  - hero-role filters allow the new heroes;
  - random picks are hooked;
  - a new casting routine handles cooldown tracking, mana checks and target choice;
  - escape logic kicks in at low HP.

## 5. Fair bots
Reading the AI's economy code showed that "Insane" bots were secretly boosted:

| Source | Bonus |
|---|---|
| `Q5F`, `-ne` ("normal exp") | +80% XP handicap |
| `Q5F`, `-he` | +120% XP |
| `Q5F`, `-ap` | +100% XP |
| Superpower layer | another +60% XP |
| `Q2F` | about 600 extra starting gold |
| `Q2F` + `QY8` | a passive-gold bonus of about 3× normal |
| `OZ9` / `OA9` (auto-enabled unless `-ne`/`-ng`) | "dynamic" gold and XP after each death |

All of these were removed. In exchange, a health-aware retreat rule was added: each bot counts visible enemy and allied heroes within 1,000 range, and when outnumbered, the HP threshold for the AI's retreat check goes up. The test results:

| | Bot levels at 11 min | Bot levels at 17–21 min |
|---|---|---|
| Before (boosted) | 6–8 | 8–13 (at 17 min) |
| After (normal) | 5–7 | 7–11 (at 21 min) |

## 6. Claude as an opponent (MCP)
- An MCP server (Python standard library) talks to a JASS bridge inside the map:
  - Preload-based file I/O: `state.txt` is written every 0.5 s and `cmd.txt` is read;
  - game-cache sync keeps every LAN client deterministic;
  - Claude sees only what its team sees.
- **auto mode** lets the map AI keep laning between Claude's orders. **manual mode** gives Claude full control, with a safety retreat.
- A full 34-minute game was played with Claude as Lion.

## Testing methods
- `war3.exe -window -loadfile <map>` plus watching for the Blizzard crash reporter. This catches load and compile crashes within seconds.
- LAN Create Game with 9 Insane bots, driven by a small keyboard and mouse script (DPI-corrected), with on-screen debug readouts.
- An in-map self-test (`-pztest`) that spawns heroes beside trees and enemies, casts every spell and prints measured results: HP before and after, stun state, pin count, perch height, blocked hits.
