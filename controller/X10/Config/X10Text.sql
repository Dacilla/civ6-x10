-- Overpowered Bonuses production front-end text (Phase 7C.2a.2 brand).
-- Loaded via <UpdateText> in FrontEnd context. LOC keys are frozen
-- internal identifiers (see docs/UX_COPY_STYLE.md); only display values
-- use player-facing wording. Setup labels are product-name neutral;
-- category labels use the "Affects: ..." pattern. Preset descriptions
-- use one parallel settings-menu pattern.
INSERT OR IGNORE INTO LocalizedText (Language, Tag, Text) VALUES
('en_US', 'LOC_X10_PRESET_NAME', 'Bonus Multiplier'),
('en_US', 'LOC_X10_PRESET_DESC', 'Sets the multiplier for affected bonuses. ×10 is the default. Bonuses that use whole numbers are unchanged if the multiplier would produce a fraction.'),
('en_US', 'LOC_X10_CUSTOM_NAME', 'Custom Multiplier (0 to 100)'),
('en_US', 'LOC_X10_CUSTOM_DESC', 'Enter a value from 0 to 100. Use a period for decimals, for example 7.3. Blank, 0, or invalid values leave affected bonuses unchanged.'),
('en_US', 'LOC_X10_MOD_TRAITS_NAME', 'Affects: Civilization & Leader Traits'),
('en_US', 'LOC_X10_MOD_TRAITS_DESC', 'Civilization and Leader Trait bonuses use the selected multiplier.'),
('en_US', 'LOC_X10_MOD_POLICIES_NAME', 'Affects: Policy Cards'),
('en_US', 'LOC_X10_MOD_POLICIES_DESC', 'Policy Card bonuses use the selected multiplier. Bonuses shared with Governments require both options.'),
('en_US', 'LOC_X10_MOD_GOVERNMENTS_NAME', 'Affects: Governments'),
('en_US', 'LOC_X10_MOD_GOVERNMENTS_DESC', 'Government bonuses use the selected multiplier. Policy slots are unchanged. Bonuses shared with Policy Cards require both options.'),
('en_US', 'LOC_X10_MOD_PANTHEONS_NAME', 'Affects: Pantheons'),
('en_US', 'LOC_X10_MOD_PANTHEONS_DESC', 'Pantheon bonuses use the selected multiplier. Does not affect other Beliefs.'),
('en_US', 'LOC_X10_MOD_WONDERS_NAME', 'Affects: Wonders'),
('en_US', 'LOC_X10_MOD_WONDERS_DESC', 'World Wonder bonuses use the selected multiplier. Does not affect slots, unlocks, or one-time rewards.'),
('en_US', 'LOC_X10_MOD_GOVERNORS_NAME', 'Affects: Governors & Secret Societies'),
('en_US', 'LOC_X10_MOD_GOVERNORS_DESC', 'Governor and Secret Society promotion bonuses use the selected multiplier. Secret Society bonuses require Secret Societies mode.'),
('en_US', 'LOC_X10_MOD_SUZERAIN_NAME', 'Affects: City-State Suzerain Bonuses'),
('en_US', 'LOC_X10_MOD_SUZERAIN_DESC', 'City-State Suzerain bonuses use the selected multiplier. Does not change Unique Units or Improvements.'),
('en_US', 'LOC_X10_PRESET_OFF', 'Off'),
('en_US', 'LOC_X10_PRESET_OFF_DESC', 'Disables the multiplier.'),
('en_US', 'LOC_X10_PRESET_2', '×2'),
('en_US', 'LOC_X10_PRESET_2_DESC', 'Sets the multiplier to ×2.'),
('en_US', 'LOC_X10_PRESET_3', '×3'),
('en_US', 'LOC_X10_PRESET_3_DESC', 'Sets the multiplier to ×3.'),
('en_US', 'LOC_X10_PRESET_5', '×5'),
('en_US', 'LOC_X10_PRESET_5_DESC', 'Sets the multiplier to ×5.'),
('en_US', 'LOC_X10_PRESET_10', '×10 Classic'),
('en_US', 'LOC_X10_PRESET_10_DESC', 'Sets the multiplier to ×10. Default setting.'),
('en_US', 'LOC_X10_PRESET_20', '×20'),
('en_US', 'LOC_X10_PRESET_20_DESC', 'Sets the multiplier to ×20.'),
('en_US', 'LOC_X10_PRESET_50', '×50'),
('en_US', 'LOC_X10_PRESET_50_DESC', 'Sets the multiplier to ×50.'),
('en_US', 'LOC_X10_PRESET_100', '×100'),
('en_US', 'LOC_X10_PRESET_100_DESC', 'Sets the multiplier to ×100.'),
('en_US', 'LOC_X10_PRESET_CUSTOM', 'Custom...'),
('en_US', 'LOC_X10_PRESET_CUSTOM_DESC', 'Uses the custom multiplier below.');
