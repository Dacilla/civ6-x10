-- X10 native probe: real Advanced Setup parameter (no silent fallback).
INSERT OR IGNORE INTO Parameters
  (ParameterId, Name, Description, Domain, DefaultValue,
   ConfigurationGroup, ConfigurationId, GroupId, Visible, SupportsSinglePlayer)
VALUES
  ('X10_PROBE_K', 'X10 probe multiplier', 'Disposable spike parameter.',
   'text', '7.3',
   'Game', 'X10_PROBE_K', 'GameOptions', 1, 1);
