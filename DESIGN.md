---
version: alpha
colors:
  background: "#101729"
  foreground: "#f6e8c8"
  primary: "#99ead0"
  danger: "#f18c83"
  muted: "#a4adc5"
typography:
  display:
    fontFamily: "Pygame default sans"
    fontSize: "116px"
  body:
    fontFamily: "Pygame default sans"
    fontSize: "30px"
  utility:
    fontFamily: "monospace"
    fontSize: "20px"
omitted:
  - section: rounded
    reason: "Native vector arcade canvas has no rounded controls."
  - section: spacing
    reason: "Fixed 1280 by 720 game coordinates, not a CSS spacing system."
  - section: components
    reason: "Pygame primitives are documented below instead of web components."
---

## Overview

A keyboard-first vector arcade game for desktop players. Use the cover artwork as the visual reference: an ivory and mint starfighter,
cyan ion exhaust, coral-lit violet rock, and an ink-navy navigation chart.
The signature is rotating low-poly rock against layered, flight-reactive stars.
Avoid dashboard cards, mouse-only menus, and visual clutter during play.

## Colors

Runtime constants in `constants.py` are canonical (ownership model B). The palette
above mirrors BACKGROUND, FOREGROUND, ACCENT, DANGER, and MUTED respectively.
`ui.Renderer`, `Player`, and `Shot` consume those shared constants. Asteroid
lighting interpolates violet shadows and coral highlights from the cover.
CYAN (#65d9ff) communicates engine energy and shields; PANEL (#141b30) backs menus.
The starfield and divider use a quiet secondary shade, #364058. Color never
replaces the textual lives, score, state, and control labels.

## Typography

`ui.Renderer` owns the three fonts. Bundled Pygame sans is used for titles and
body copy; a system monospace face, falling back to Pygame default, carries data.
Keep titles short and centered; keep numeric HUD values aligned.

## Layout

The 1280 by 720 playfield remains the course coordinate system. HUD occupies the top 96px; controls occupy the bottom 41px.
Contract progress lives at lower left; a relative-position radar sits lower right. Title, pause, and game-over screens
share centered title/detail/action geometry, owned by one renderer. World drawing always targets an isolated logical canvas. Windowed mode is
resizable; fullscreen requests the native desktop mode. display.Display clears
the full display every frame and scales the canvas to a centered aspect-preserving
viewport. Black letterboxing is explicit; no world drawing touches the display
directly. F11 toggles modes without replacing simulation state. Mobile and screen-reader gameplay are not
supported by this native canvas implementation.

## Elevation & Depth

Asteroids use irregular subdivided icosahedra, rotating in 3D with surface-normal
lighting and orthographic projection. Circle collisions remain independent of the
mesh. Stars have depth-dependent parallax and velocity streaks; a cached dust
band and quiet orbit-chart rings reference the cover. Twin cyan particle trails
follow thrust, and coral shards mark impacts. Particles are capped at 300.
A translucent overlay dims and freezes the field during menus and upgrades.

## Shapes

Preserve the triangular ship and circular collision model; shade solid rock meshes.
The protection ring communicates temporary invulnerability.

## Components

Canonical owners: Game handles title/playing/paused/upgrade/game_over transitions,
Renderer owns overlays and HUD, Player owns movement/shooting, and the sprite
classes own object drawing. Enter starts or restarts; P or Enter toggles pause;
Escape exits in every state. Focus loss pauses play without losing progress.
Three hull lives, rechargeable shields, and respawn protection provide recoverable collisions.
Best-score persistence failures show text on menus and preserve the in-memory
best; a later save retries. Reduced motion removes particles, star movement/twinkle/streaks, and rock rotation
while keeping the steady protection ring. No forms, async requests, or web primitives
are applicable to this game.

## Do's and Don'ts

Keep all actions keyboard accessible and display controls on every screen.
Keep score and lives readable. Do not add flashing full-screen effects.
Keep menu layout stable and gameplay particle counts bounded.

## Flight and progression contract

Player owns inertial acceleration, drag, boost energy, and cannon configuration.
Game owns shield recharge, hull damage, run-local ranks, contracts, combo scoring,
and upgrade transactions. progression.py owns salvage behavior and module metadata.
Renderer only reads simulation state; drawing never advances time or consumes the
spawn RNG. Decorative randomness uses separate local generators.

Shift boosts while thrusting; exhaustion requires releasing Shift before boosting
again. Shields absorb 25 points per hit, then regenerate 5/sec after six seconds
without impact. An unshielded hit loses one of three hull lives. Each respawn
stops velocity and grants two seconds of protection. Initial shields are 50.

Collect mint diamond salvage to earn XP. Rank thresholds start at 12 and rise by
6 per rank. Reaching a rank freezes combat and offers up to three modules; number
keys install a choice. Escape exits consistently. Capped modules leave the pool;
hull reconstruction remains repeatable and restores shields as well. No run
progression persists across restarts; only best score persists.

Each five kills in a chain adds 0.25 to the score multiplier, capped at x2. A
three-second gap ends the chain; damage also clears it. Kill contracts grant
500 score and 8 XP, with increasing targets. HUD data and radar contacts reflect
actual state. All menus use the same palette, typography, and keyboard labels.

This remains a fixed-resolution native keyboard game: browser forms, mobile
layouts, DOM semantics, async requests, and screen-reader gameplay do not apply.

## Rendering performance

Asteroids outside the canvas are culled before rendering. Each visible rock caches
one local raster, refreshed in 0.04-radian angle steps; translation remains updated
every frame. Small and medium rocks use 20 faces, large rocks 80. Material shades
are precomputed; only front-facing faces are sorted. Renderer keeps a bounded
256-entry text cache and reusable menu/HUD overlays. Display reuses its scaled
buffer until the viewport changes size. benchmark.py measures rendering separately
from simulation, display scaling, and frame pacing.
