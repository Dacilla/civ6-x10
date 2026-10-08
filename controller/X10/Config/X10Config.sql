-- X10 controller configuration.
-- X10_MULTIPLIER: arbitrary numeric input as text (parsed natively to
-- double, range 0..100, 0 = Off). Default 10 (Classic X10). Convenient
-- presets that remain fully arbitrary-compatible: 2, 3, 5, 10, 20, 50, 100.
-- Module toggles are INTEGER 0/1 (bool domains have no proven native reader;
-- int variants are proven). Supported modules default ON; unsupported ones
-- default OFF and are ignored loudly by the native layer if enabled.
-- SHARED-DEFINITION RULE (Release 1): 25 modifier definitions are owned by
-- both Policies and Governments. A definition-level mutation is globally
-- shared, so exact independent toggles are impossible: a shared definition
-- is transformed ONLY if ALL owning supported modules are enabled.
-- Disabling Policies (or Governments) therefore never leaves an X10 mutation
-- active through the other owner. Per-entry owners bitmask lives in the
-- generated registry (1=traits 2=policies 4=governments 8=pantheons).
INSERT OR IGNORE INTO Parameters
  (ParameterId, Name, Description, Domain, DefaultValue,
   ConfigurationGroup, ConfigurationId, GroupId, Visible, SupportsSinglePlayer)
VALUES
  ('X10_MULTIPLIER', 'X10 multiplier', 'Semantic multiplier, e.g. 7.3 (0 = Off).',
   'text', '10',
   'Game', 'X10_MULTIPLIER', 'GameOptions', 1, 1),
  ('X10_MODULE_TRAITS', 'X10: Traits', 'Apply to civilization/leader traits.',
   'int', '1',
   'Game', 'X10_MODULE_TRAITS', 'GameOptions', 1, 1),
  ('X10_MODULE_POLICIES', 'X10: Policies', 'Apply to policy cards.',
   'int', '1',
   'Game', 'X10_MODULE_POLICIES', 'GameOptions', 1, 1),
  ('X10_MODULE_GOVERNMENTS', 'X10: Governments', 'Apply numeric government effects (slots stay structural).',
   'int', '1',
   'Game', 'X10_MODULE_GOVERNMENTS', 'GameOptions', 1, 1),
  ('X10_MODULE_PANTHEONS', 'X10: Pantheons', 'Apply to founded-pantheon belief effects.',
   'int', '1',
   'Game', 'X10_MODULE_PANTHEONS', 'GameOptions', 1, 1),
  ('X10_MODULE_GOVERNORS', 'X10: Governors (unsupported)', 'Not yet implemented; ignored.',
   'int', '0',
   'Game', 'X10_MODULE_GOVERNORS', 'GameOptions', 1, 1),
  ('X10_MODULE_WONDERS', 'X10: Wonders (unsupported)', 'Not yet implemented; ignored.',
   'int', '0',
   'Game', 'X10_MODULE_WONDERS', 'GameOptions', 1, 1),
  ('X10_MODULE_SUZERAIN', 'X10: City-states (unsupported)', 'Not yet implemented; ignored.',
   'int', '0',
   'Game', 'X10_MODULE_SUZERAIN', 'GameOptions', 1, 1);
