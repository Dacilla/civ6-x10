-- X10 controller configuration (production, Phase 7C.2).
-- Native SetupParameters UI: preset dropdown + custom value + bool module
-- checkboxes under Advanced Setup (SortIndex 2400-2408, verified free).
--   X10_MULTIPLIER_PRESET (integer dropdown; Custom sentinel 101)
--   X10_MULTIPLIER        (text custom value; ALSO the legacy key: absent or
--                          UNSET preset falls back to it; default '10')
--   X10_MODULE_*          (native bool checkboxes; legacy INT32 0/1 still
--                          accepted by the reader; all default ON)
-- Shared-definition ownership (unchanged rule): a shared definition is
-- transformed ONLY if ALL owning supported modules are enabled. Per-entry
-- owners bitmask in the generated registry: 1=traits 2=policies
-- 4=governments 8=pantheons 16=wonders 32=governors 64=suzerain
-- (city-state) 128=promotions 256=dedications 512=modes 1024=religion
-- 2048=greatpeople 4096=projects.
-- Preset DefaultValue is SQLite INTEGER 10 (not TEXT): the setup driver
-- only coerces bool/int/uint domains and ==-compares custom-domain
-- defaults, so a text default can never match and the UI falls back to
-- the first domain row. Single-player scope is explicit; nothing here is
-- changeable after game start.
INSERT OR IGNORE INTO Parameters
  (ParameterId, Name, Description, Domain, DefaultValue, Hash,
   ConfigurationGroup, ConfigurationId, GroupId, SortIndex,
   Visible, SupportsSinglePlayer, SupportsLANMultiplayer,
   SupportsInternetMultiplayer, SupportsHotSeat, SupportsPlayByCloud,
   ChangeableAfterGameStart)
VALUES
  ('X10Preset', 'LOC_X10_PRESET_NAME', 'LOC_X10_PRESET_DESC',
   'X10MultiplierPresets', 10, 0,
   'Game', 'X10_MULTIPLIER_PRESET', 'AdvancedOptions', 2400,
   1, 1, 0, 0, 0, 0, 0),
  ('X10Custom', 'LOC_X10_CUSTOM_NAME', 'LOC_X10_CUSTOM_DESC',
   'text', '10', 0,
   'Game', 'X10_MULTIPLIER', 'AdvancedOptions', 2401,
   1, 1, 0, 0, 0, 0, 0),
  ('X10ModuleTraits', 'LOC_X10_MOD_TRAITS_NAME', 'LOC_X10_MOD_TRAITS_DESC',
   'bool', '1', 0,
   'Game', 'X10_MODULE_TRAITS', 'AdvancedOptions', 2402,
   1, 1, 0, 0, 0, 0, 0),
  ('X10ModulePolicies', 'LOC_X10_MOD_POLICIES_NAME', 'LOC_X10_MOD_POLICIES_DESC',
   'bool', '1', 0,
   'Game', 'X10_MODULE_POLICIES', 'AdvancedOptions', 2403,
   1, 1, 0, 0, 0, 0, 0),
  ('X10ModuleGovernments', 'LOC_X10_MOD_GOVERNMENTS_NAME', 'LOC_X10_MOD_GOVERNMENTS_DESC',
   'bool', '1', 0,
   'Game', 'X10_MODULE_GOVERNMENTS', 'AdvancedOptions', 2404,
   1, 1, 0, 0, 0, 0, 0),
  ('X10ModulePantheons', 'LOC_X10_MOD_PANTHEONS_NAME', 'LOC_X10_MOD_PANTHEONS_DESC',
   'bool', '1', 0,
   'Game', 'X10_MODULE_PANTHEONS', 'AdvancedOptions', 2405,
   1, 1, 0, 0, 0, 0, 0),
  ('X10ModuleWonders', 'LOC_X10_MOD_WONDERS_NAME', 'LOC_X10_MOD_WONDERS_DESC',
   'bool', '1', 0,
   'Game', 'X10_MODULE_WONDERS', 'AdvancedOptions', 2406,
   1, 1, 0, 0, 0, 0, 0),
  ('X10ModuleGovernors', 'LOC_X10_MOD_GOVERNORS_NAME', 'LOC_X10_MOD_GOVERNORS_DESC',
   'bool', '1', 0,
   'Game', 'X10_MODULE_GOVERNORS', 'AdvancedOptions', 2407,
   1, 1, 0, 0, 0, 0, 0),
  ('X10ModuleSuzerain', 'LOC_X10_MOD_SUZERAIN_NAME', 'LOC_X10_MOD_SUZERAIN_DESC',
   'bool', '1', 0,
   'Game', 'X10_MODULE_SUZERAIN', 'AdvancedOptions', 2408,
   1, 1, 0, 0, 0, 0, 0),
  ('X10ModulePromotions', 'LOC_X10_MOD_PROMOTIONS_NAME', 'LOC_X10_MOD_PROMOTIONS_DESC',
   'bool', '1', 0,
   'Game', 'X10_MODULE_PROMOTIONS', 'AdvancedOptions', 2409,
   1, 1, 0, 0, 0, 0, 0),
  ('X10ModuleDedications', 'LOC_X10_MOD_DEDICATIONS_NAME', 'LOC_X10_MOD_DEDICATIONS_DESC',
   'bool', '1', 0,
   'Game', 'X10_MODULE_DEDICATIONS', 'AdvancedOptions', 2410,
   1, 1, 0, 0, 0, 0, 0),
  ('X10ModuleModes', 'LOC_X10_MOD_MODES_NAME', 'LOC_X10_MOD_MODES_DESC',
   'bool', '1', 0,
   'Game', 'X10_MODULE_MODES', 'AdvancedOptions', 2411,
   1, 1, 0, 0, 0, 0, 0),
  ('X10ModuleReligion', 'LOC_X10_MOD_RELIGION_NAME', 'LOC_X10_MOD_RELIGION_DESC',
   'bool', '1', 0,
   'Game', 'X10_MODULE_RELIGION', 'AdvancedOptions', 2412,
   1, 1, 0, 0, 0, 0, 0),
  ('X10ModuleGreatPeople', 'LOC_X10_MOD_GREATPEOPLE_NAME', 'LOC_X10_MOD_GREATPEOPLE_DESC',
   'bool', '1', 0,
   'Game', 'X10_MODULE_GREATPEOPLE', 'AdvancedOptions', 2413,
   1, 1, 0, 0, 0, 0, 0),
  ('X10ModuleProjects', 'LOC_X10_MOD_PROJECTS_NAME', 'LOC_X10_MOD_PROJECTS_DESC',
   'bool', '1', 0,
   'Game', 'X10_MODULE_PROJECTS', 'AdvancedOptions', 2414,
   1, 1, 0, 0, 0, 0, 0);

INSERT OR IGNORE INTO DomainValues
  (Domain, Value, Name, Description, SortIndex)
VALUES
  ('X10MultiplierPresets', 0, 'LOC_X10_PRESET_OFF', 'LOC_X10_PRESET_OFF_DESC', 10),
  ('X10MultiplierPresets', 2, 'LOC_X10_PRESET_2', 'LOC_X10_PRESET_2_DESC', 20),
  ('X10MultiplierPresets', 3, 'LOC_X10_PRESET_3', 'LOC_X10_PRESET_3_DESC', 30),
  ('X10MultiplierPresets', 5, 'LOC_X10_PRESET_5', 'LOC_X10_PRESET_5_DESC', 40),
  ('X10MultiplierPresets', 10, 'LOC_X10_PRESET_10', 'LOC_X10_PRESET_10_DESC', 50),
  ('X10MultiplierPresets', 20, 'LOC_X10_PRESET_20', 'LOC_X10_PRESET_20_DESC', 60),
  ('X10MultiplierPresets', 50, 'LOC_X10_PRESET_50', 'LOC_X10_PRESET_50_DESC', 70),
  ('X10MultiplierPresets', 100, 'LOC_X10_PRESET_100', 'LOC_X10_PRESET_100_DESC', 80),
  ('X10MultiplierPresets', 101, 'LOC_X10_PRESET_CUSTOM', 'LOC_X10_PRESET_CUSTOM_DESC', 90);

-- Custom field visible only when the preset is Custom (101).
INSERT OR IGNORE INTO ParameterDependencies
  (ParameterId, ConfigurationGroup, ConfigurationId, Operator, ConfigurationValue)
VALUES
  ('X10Custom', 'Game', 'X10_MULTIPLIER_PRESET', 'Equals', 101);
