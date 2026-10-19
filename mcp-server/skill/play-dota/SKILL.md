---
name: play-dota
description: Play a live Warcraft III DotA game against the user as the enemy hero, through the wc3-dota MCP server (map "DotA 6.88f AI vs Claude"). Use when the user wants to play DotA or Warcraft III against Claude, or says "let's play".
---

# Play DotA against the user

You control one computer slot in the user's LAN game through the `wc3-dota` MCP tools.
The game runs in real time while you think, so keep every step short and keep acting
until the game ends.

## 1. Get into the game
1. Call `game_status`.
2. If there is no live game, give the user its setup steps in a few lines (host LAN on
   "DotA 6.88f AI vs Claude", set one slot on the other team to Computer, start, type a
   mode). Then poll `game_status` about every 15 s (sleep with a short shell command
   in between) until it reports a live, linked game. Don't ask the user to report back.
3. You have 75 s of game time to pick. Otherwise the map's AI picks a random hero for you.

## 2. Pick a hero
- `list_heroes` shows only the heroes you may pick right now (e.g. your 3 options in -sd).
- Prefer heroes whose strength is a few targeted spells: a stun, a hex or a nuke
  (Lion, Sven, Lina, Zeus, Witch Doctor, Sand King, Tidehunter, Night Stalker...).
  If the user's hero is already visible, pick something that answers it.
- `pick_hero` with a short, friendly `say` line. A default skill build is set
  automatically. Use `act` "build ..." if you want your own.

## 3. Play loop (until the game ends)
Repeat:
1. `wait` with 6–12 s. It wakes up early when an enemy hero appears, you take damage or
   drop below 40% HP, you die or respawn, you get a skill point, or there is a kill or chat.
2. Decide from the returned state, then send one `act` call holding all orders for this
   step (separate them with `;`).

Guidelines:
- Stay in `mode auto` (the default). The map's AI lanes, farms, buys and retreats between
  your orders, and each order gives you control for `holdtime` seconds (default 8).
  Raise `holdtime` (15–25) for a gank or a teamfight. Use `mode manual` only for longer
  plans, and always go back to auto.
- Fight with skills: `cast <skill> h<player>` on visible enemy heroes in range, then
  `attack h<player>`. The state shows cooldowns and mana, and the server refuses casts
  that are not ready. Chain disables, and save the ultimate for a kill.
- Below ~35% HP with enemies near: `back`. While you steer there is also an automatic
  retreat at 20% (`retreat_at` changes it).
- Spend gold at the base shops: `back`, then `buy <item>` when near the fountain. Combined
  items are bought as their parts plus the recipe (`lookup <item>` shows them).
- Use `lane top|mid|bot` to rejoin a lane, `amove X Y` to push.
- Answer the user's chat with `say`, with friendly banter at most about once a minute.
  Never spam.
- Fair play: you only see what your hero's team sees. Don't guess at hidden information.
- Don't write commentary to the user during the game. Their attention is on the game,
  and long messages cost you reaction time.

## 4. Game over
The game is over when an Ancient is destroyed (a `building` event for a Tree/Throne) or
the state stops updating. Then say `gg` in chat if the game is still open, and give the
user a 3–5 line summary: your hero, kills/deaths you saw, and the turning point.
