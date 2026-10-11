X10 — Configurable Bonus Multiplier (1.0.0-rc2)
==================================================

X10 scales bonuses where multiplying them has a clear, safe meaning.
Percentage discounts use proper percentage maths, combat bonuses use
Civ VI's combat scaling, and whole-number effects such as charges are
never rounded. Mechanics that cannot be scaled safely stay at their
normal values.

SETUP (Advanced Setup, all defaults are fine):
1. Subscribe to X10 — Configurable Bonus Multiplier. Steam also
   installs the required X10 CE Engine.
2. Make sure no other Community Extension/GameCore replacement is
   enabled.
3. Create a new single-player Gathering Storm game.
4. Open Advanced Setup.
5. Choose X10 — Multiplier; ×10 (Classic) is the default. Choose
   Custom for values such as 7.3 (decimals use a period).
6. Leave all categories enabled, or uncheck anything you want to keep
   at normal strength.
7. Start the game.

Whole-unit bonuses apply only on exact whole-number results; otherwise
they keep official values instead of rounding.

REQUIRES the matching "X10 CE Engine" Workshop item and Gathering
Storm. Windows x64 only. X10 affects saved games: choose settings
when creating the campaign; changing X10 configuration for an
existing campaign is not supported.

FAQ:
- Nothing changed? Check both X10 items are enabled, no other
  GameCore replacement is active, and Multiplier is not Off.
- One bonus stayed normal? It needed a whole number your multiplier
  did not produce, or that mechanic is intentionally left vanilla.
- Secret Society bonuses unchanged? Secret Societies mode must be
  enabled for those definitions to exist.
- Change settings in an existing save? Not supported.
- Custom shows lots of decimal places (7.3000001907349)? Civ VI
  displays the internal floating-point representation; the chosen
  multiplier still works correctly.
- Log? %TEMP%\X10Lifecycle.log (support/troubleshooting).

License: AGPL-3.0 (see LICENSE.txt). Source: see SOURCE.txt.
