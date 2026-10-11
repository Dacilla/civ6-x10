# Overpowered Bonuses v1.0.0 - known issues (user-facing)

- Windows x64 only. No Mac/Linux support (native GameCore DLL).
- Requires Civilization VI: Gathering Storm.
- Incompatible with any other active GameCore / Community Extension
  replacement: enable exactly one engine and controller pair
  (Overpowered Bonuses CE Engine + Overpowered Bonuses).
- Whole-unit effects such as charges, power, and resources are left
  unchanged whenever the configured multiplier would produce a
  fraction. These bonuses are never rounded.
- Some effects are intentionally left unchanged because multiplying
  them would not produce a reliable result. Examples: healing caps,
  certain percentage scaling, and the base stats of unlocked unique
  units and Improvements.
- Two-item install: the controller requires the Overpowered Bonuses
  CE Engine item. Steam should pull it automatically once the
  Required-Item link is set.
- Overpowered Bonuses affects saved games: choose settings when
  creating the campaign; changing these settings for an existing
  campaign is not supported.
- Secret Society bonuses are available only when Secret Societies
  mode is enabled.
- Custom decimal values may show extra digits after you enter them.
  For example, 7.3 may appear as 7.3000001907349. This is only a
  display issue.
- If you need support, include `%TEMP%\X10Lifecycle.log` after
  reaching the map. The log keeps its internal X10 filename.
