-- X10 UX prototype configuration (DISPOSABLE, Phase 7C.1).
-- Native SetupParameters only: preset dropdown via a custom Domain +
-- DomainValues, custom decimal field gated by ParameterDependencies, seven
-- native bool module checkboxes. All keys are X10_UX_* (never production
-- X10_MULTIPLIER / X10_MODULE_*). GroupId AdvancedOptions, contiguous
-- SortIndex 2400-2408 (verified free against installed SetupParameters.xml:
-- AdvancedOptions uses 2000/2010/3000/3010/3020). Single-player scope is
-- explicit; every other mode flag is 0; nothing is changeable after start.

INSERT OR IGNORE INTO Parameters
  (ParameterId, Name, Description, Domain, DefaultValue, Hash,
   ConfigurationGroup, ConfigurationId, GroupId, SortIndex,
   Visible, SupportsSinglePlayer, SupportsLANMultiplayer,
   SupportsInternetMultiplayer, SupportsHotSeat, SupportsPlayByCloud,
   ChangeableAfterGameStart)
VALUES
  ('X10UxPreset', 'LOC_X10_UX_PRESET_NAME', 'LOC_X10_UX_PRESET_DESC',
   'X10UxMultiplierPresets', 10, 0,
   'Game', 'X10_UX_PRESET', 'AdvancedOptions', 2400,
   1, 1, 0, 0, 0, 0, 0),
  ('X10UxCustom', 'LOC_X10_UX_CUSTOM_NAME', 'LOC_X10_UX_CUSTOM_DESC',
   'text', NULL, 0,
   'Game', 'X10_UX_CUSTOM', 'AdvancedOptions', 2401,
   1, 1, 0, 0, 0, 0, 0),
  ('X10UxBoolTraits', 'LOC_X10_UX_MOD_TRAITS_NAME', 'LOC_X10_UX_MOD_TRAITS_DESC',
   'bool', '1', 0,
   'Game', 'X10_UX_BOOL_TRAITS', 'AdvancedOptions', 2402,
   1, 1, 0, 0, 0, 0, 0),
  ('X10UxBoolPolicies', 'LOC_X10_UX_MOD_POLICIES_NAME', 'LOC_X10_UX_MOD_POLICIES_DESC',
   'bool', '1', 0,
   'Game', 'X10_UX_BOOL_POLICIES', 'AdvancedOptions', 2403,
   1, 1, 0, 0, 0, 0, 0),
  ('X10UxBoolGovernments', 'LOC_X10_UX_MOD_GOVERNMENTS_NAME', 'LOC_X10_UX_MOD_GOVERNMENTS_DESC',
   'bool', '1', 0,
   'Game', 'X10_UX_BOOL_GOVERNMENTS', 'AdvancedOptions', 2404,
   1, 1, 0, 0, 0, 0, 0),
  ('X10UxBoolPantheons', 'LOC_X10_UX_MOD_PANTHEONS_NAME', 'LOC_X10_UX_MOD_PANTHEONS_DESC',
   'bool', '1', 0,
   'Game', 'X10_UX_BOOL_PANTHEONS', 'AdvancedOptions', 2405,
   1, 1, 0, 0, 0, 0, 0),
  ('X10UxBoolWonders', 'LOC_X10_UX_MOD_WONDERS_NAME', 'LOC_X10_UX_MOD_WONDERS_DESC',
   'bool', '1', 0,
   'Game', 'X10_UX_BOOL_WONDERS', 'AdvancedOptions', 2406,
   1, 1, 0, 0, 0, 0, 0),
  ('X10UxBoolGovernors', 'LOC_X10_UX_MOD_GOVERNORS_NAME', 'LOC_X10_UX_MOD_GOVERNORS_DESC',
   'bool', '1', 0,
   'Game', 'X10_UX_BOOL_GOVERNORS', 'AdvancedOptions', 2407,
   1, 1, 0, 0, 0, 0, 0),
  ('X10UxBoolSuzerain', 'LOC_X10_UX_MOD_SUZERAIN_NAME', 'LOC_X10_UX_MOD_SUZERAIN_DESC',
   'bool', '1', 0,
   'Game', 'X10_UX_BOOL_SUZERAIN', 'AdvancedOptions', 2408,
   1, 1, 0, 0, 0, 0, 0);

-- Preset domain values. The Custom sentinel is provisionally 101: only
-- valid if the framework stores the domain value in a safely readable
-- scalar variant (to be proven by the scratch config-variant run).
INSERT OR IGNORE INTO DomainValues
  (Domain, Value, Name, Description, SortIndex)
VALUES
  ('X10UxMultiplierPresets', 0, 'LOC_X10_UX_PRESET_OFF', 'LOC_X10_UX_PRESET_OFF_DESC', 10),
  ('X10UxMultiplierPresets', 2, 'LOC_X10_UX_PRESET_2', 'LOC_X10_UX_PRESET_2_DESC', 20),
  ('X10UxMultiplierPresets', 3, 'LOC_X10_UX_PRESET_3', 'LOC_X10_UX_PRESET_3_DESC', 30),
  ('X10UxMultiplierPresets', 5, 'LOC_X10_UX_PRESET_5', 'LOC_X10_UX_PRESET_5_DESC', 40),
  ('X10UxMultiplierPresets', 10, 'LOC_X10_UX_PRESET_10', 'LOC_X10_UX_PRESET_10_DESC', 50),
  ('X10UxMultiplierPresets', 20, 'LOC_X10_UX_PRESET_20', 'LOC_X10_UX_PRESET_20_DESC', 60),
  ('X10UxMultiplierPresets', 50, 'LOC_X10_UX_PRESET_50', 'LOC_X10_UX_PRESET_50_DESC', 70),
  ('X10UxMultiplierPresets', 100, 'LOC_X10_UX_PRESET_100', 'LOC_X10_UX_PRESET_100_DESC', 80),
  ('X10UxMultiplierPresets', 101, 'LOC_X10_UX_PRESET_CUSTOM', 'LOC_X10_UX_PRESET_CUSTOM_DESC', 90);

-- Preset default is INTEGER 10, not TEXT '10': the setup driver coerces
-- DefaultValue only for bool/int/uint domains and otherwise compares with
-- == against domain values, so a text default can never match the numeric
-- DomainValues and the UI falls back to the first row ("blech! get the
-- first valid value" in SetupParameters.lua). Parameters.DefaultValue is
-- typeless: unquoted 10 stores INTEGER and matches domain value 10.

-- Custom field visible only when the preset is Custom (101). If the setup
-- UI ignores this, the graceful fallback is the always-visible field with
-- its "Used only when ..." description (already worded that way below).
INSERT OR IGNORE INTO ParameterDependencies
  (ParameterId, ConfigurationGroup, ConfigurationId, Operator, ConfigurationValue)
VALUES
  ('X10UxCustom', 'Game', 'X10_UX_PRESET', 'Equals', 101);
