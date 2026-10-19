# The maps

All maps run on **Warcraft III: The Frozen Throne 1.27b**. Copy them into `Warcraft III\Maps\Scenario\` and host them from **Local Area Network → Create Game**. The lobby name shown below is what appears in the in-game map list.

---

## 1. DotA AI 6.88 MK+Mars (recommended)
**File:** `DotA_688_AI_Superpower_MK_Mars.w3x` (10.1 MB)
**Based on:** DotA 6.88f AI with the "Superpower" layer (map 3 below)

### What's new
- **Two Dota 2 heroes with full bot support.**
  - **Monkey King** sits in Vengeful Spirit's tavern: Boundless Strike, Tree Dance, Primal Spring, Jingu Mastery and Wukong's Command.
  - **Mars** sits in the tavern that has 4 heroes: Spear of Mars, God's Rebuke, Bulwark and Arena of Blood.
  - Models, icons, stats and tooltips are ported from DracoL1ch's DotA 7.03R11.
  - All spells are re-implemented in plain JASS, because the 7.03R11 code needs the 1.26a memory hack.
  - Not ported: Monkey King's Mischief and both heroes' Aghanim's Scepter upgrades.
- **Bots play the new heroes.**
  - They learn skills through the map's AI tables.
  - Item builds are borrowed: Juggernaut's for Monkey King, Axe's for Mars.
  - A new AI routine casts their spells.
  - Each bot pick has a 25% chance to be Monkey King or Mars, so they show up in most games.
- **Normal economy for bots.** The original map secretly boosted Insane bots. All of this is removed:
  - The `-ne` mode ("normal exp") actually **added** +80% XP, `-he` added +120%, and `-ap` alone added +100%. Superpower added another +60%.
  - Insane bots earned about 3× the passive gold and got about 600 extra starting gold.
  - Unless you typed `-ne`/`-ng`, a "dynamic" catch-up system gave bots more gold and XP every time they died.
- **Health-aware bots.**
  - Every bot counts the visible enemy and allied heroes around it. When outnumbered, it retreats at a higher HP threshold (up to +30%, capped at 70%).
  - Below 35% HP, Monkey King escapes onto a tree and Mars pushes chasers away with Spear.

### Tested
- **LAN game, 9 Insane bots, 22 minutes, no crash.**
  - Bots stayed at 100% XP with no bonus gold all game.
  - Bot levels were 5–7 at 11 minutes and 7–11 at 21 minutes. The boosted original had them at 8–13 by minute 17.
  - In that game, Mars pinned heroes with Spear 4 times and Arena spears hit 4 times. Monkey King triggered Jingu 4 times and his soldiers landed 52 hits.
- **Automatic self-test of every spell**, run with a debug build:
  - Tree Dance perches at a height of 220.
  - Primal Spring dealt 324 damage on landing.
  - Boundless Strike stunned its target.
  - Jingu charged after 4 hits.
  - Spear pinned its target to a tree and stunned it.
  - Rebuke slowed and pushed back.
  - Arena kept an enemy inside and spear-hit it twice.
  - Bulwark blocked 12 hits.

---

## 2. DotA 6.88f AI vs Claude
**File:** `DotA_6_88f_AI_vs_Claude.w3x` (11.2 MB)
**Based on:** DotA 6.88f AI Superpower EN (map 3)

This is the map used by the [wc3-dota MCP server](../mcp-server/). The first computer slot on the team opposite the host is controlled by **Claude**. The map's own AI keeps playing that hero between Claude's orders. Setup is in [mcp-server/README.md](../mcp-server/README.md).

**Tested:** a full 34-minute game with one human and computers, where Claude played Lion. Games with two human PCs use the same sync path but have not been tested on two machines.

Note: this map is built from map 3, so its bots still have the original gold and XP bonuses. It can be rebuilt from the MK+Mars map with `mcp-server/tools/patch_map.py`.

---

## 3. DotA AI 6.8G9b (6.88f AI Superpower, English)
**File:** `DotA_6_88f_AI_Superpower_EN.w3x` (13.1 MB)
**Based on:** DotA 6.88f AI (Chinese AI community build of DracoL1ch's 6.88f), plus the "Superpower" AI layer and an English translation

**What was fixed:** every Superpower build crashed Warcraft III 1.27b while the game was being created or loaded (`ACCESS_VIOLATION` in Game.dll).
- The cause was not the translation. The original AI script's function `N9F` has a hero `if/elseif` chain of about 110 branches with huge conditions, and it already sits at a 1.27b script-compiler limit. Adding even one empty `elseif` before those branches crashes the game.
- The fix splits the chain in two behind a local flag.

**Tested:** LAN Create Game with 9 Insane bots, 5 minutes, no crash. This map keeps the original bot gold and XP bonuses.

---

## 4. DotA v6.83d CN Fixed
**File:** `DotA_v6.83d_CN_fixed.w3x` (9.5 MB)
**Based on:** a Chinese DotA 6.83d (中文版) built for the KK/11 game platforms (`qcloud_20102382.w3x`, 66.9 MB)

**What was fixed:** on vanilla 1.27b the original silently returned to the main menu.
- Its script declares six YDWE "japi" natives (`EXGetUnitAbility`, `EXSetAbilityDataReal`, and others) that only exist on those platforms.
- These were replaced with plain JASS stubs. The "is attack" damage query is approximated from the damage source's current order.
- About 57 MB of unreferenced protector padding was removed. The 16 MB sector layout was rebuilt, and encrypted blocks were re-keyed for their new positions.
- The map-list name was set to "DotA v6.83d CN Fixed".

**Tested:** loads with `-loadfile` and through LAN Create Game into a running game. A LAN start needs at least one opponent slot filled. Platform skins and the japi-scaled Lina Fiery Soul bonus can't work on vanilla Warcraft III.

---

## 5. SG DotA v7.15 AI Superpower
**File:** `SG_DotA_v7.15_AI_Superpower.w3x` (2.5 MB)
**Based on:** SG DotA v7.15 AI (Hive Workshop)

**What was added for computer heroes:**
- a 0.5-second AI tick;
- automatic skill learning (the original never spends computer heroes' skill points);
- spell casting, which tries target, then point, then no-target orders taken from each ability's base order;
- a retreat to the fountain below 25% HP;
- +60% XP handicap for computers;
- a "SUPERPOWER AI" message.

**Tested:** debug LAN game with 9 Insane bots for 5 minutes: 117 casts, 26 skills learned, 12 retreats, kills happening, no crash.

---

## Which map should I play?
- **To play against bots with new heroes and fair bots:** DotA AI 6.88 MK+Mars.
- **To play against Claude:** DotA 6.88f AI vs Claude, with the MCP server running.
- **For the Chinese 6.83d experience:** DotA v6.83d CN Fixed.
