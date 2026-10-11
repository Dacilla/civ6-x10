Overpowered Bonuses (1.0.0-rc2)
==================================================

Overpowered Bonuses creates deliberately overpowered builds by
multiplying Civilization VI bonuses. Different bonuses are handled
according to how Civilization VI uses them. Bonuses that require
whole numbers are never rounded. Effects that cannot be multiplied
reliably are left unchanged.

SETUP (Advanced Setup, all defaults are fine):
1. Subscribe to Overpowered Bonuses. Steam also installs the required
   Overpowered Bonuses CE Engine.
2. Make sure no other Community Extension/GameCore replacement is
   enabled.
3. Create a new single-player Gathering Storm game.
4. Open Advanced Setup.
5. Choose Bonus Multiplier; ×10 Classic is the default. Choose
   Custom for values such as 7.3 (decimals use a period).
6. Leave all categories enabled, or uncheck anything you want to keep
   unchanged.
7. Start the game.

Whole-unit bonuses apply only on exact whole-number results; otherwise
they keep their normal values instead of rounding.

REQUIRES the matching "Overpowered Bonuses CE Engine" Workshop item
and Gathering Storm. Windows x64 only. Overpowered Bonuses affects
saved games: choose settings when creating the campaign; changing
these settings for an existing campaign is not supported.

FAQ:
- Nothing changed? Check both Overpowered Bonuses items are enabled,
  no other GameCore replacement is active, and Multiplier is not Off.
- One bonus stayed the same? It may need whole numbers your
  multiplier did not produce, or that effect is intentionally left
  unchanged.
- Secret Society bonuses unchanged? They are available only when
  Secret Societies mode is enabled.
- Change settings in an existing save? Not supported.
- Custom decimal values may show extra digits after you enter them.
  For example, 7.3 may appear as 7.3000001907349. This is only a
  display issue.
- Leaving Custom blank enters 0, which behaves like Off.
- Log? %TEMP%\X10Lifecycle.log (support/troubleshooting). The log
  keeps its internal X10 filename.

License: AGPL-3.0 (see LICENSE.txt). Source: see SOURCE.txt.
