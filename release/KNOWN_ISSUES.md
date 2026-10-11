# X10 v1.0.0 — known issues (user-facing)

- Windows x64 only. No Mac/Linux support (native GameCore DLL).
- Requires Civilization VI: Gathering Storm.
- Incompatible with any other active GameCore / Community Extension
  replacement: enable exactly one (X10 CE Engine + X10 controller).
- Whole-unit effects (charges, power, resources, ...) stay at official
  values whenever the configured multiplier would produce a fractional
  result. This is deliberate exactness, not a bug: nothing is rounded.
- Ambiguous mechanics stay vanilla by design: percentage-factor scaling,
  healing caps, unique-improvement intrinsics, and other rows documented
  in the release source never scale.
- Two-item install: the controller requires the X10 CE Engine item;
  Steam should pull it automatically once the Required-Item link is set.
- X10 affects saved games: choose settings when creating the campaign;
  changing X10 configuration for an existing campaign is not supported.
- Secret Societies content populates only with the mode enabled.
- Custom decimals may redisplay with floating-point noise (7.3 may
  appear as 7.3000001907349). The chosen multiplier still works
  correctly; this is a Civ VI display artifact.
- Troubleshooting: after reaching the map, inspect
  `%TEMP%\X10Lifecycle.log`.
