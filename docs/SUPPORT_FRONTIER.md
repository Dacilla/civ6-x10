# Phase 8A — Support Frontier Discovery (closed-world audit + roadmap)

Status: RESEARCH ONLY. No production change. Production remains the
live-validated 1010 build (1010 entries / 1006 definitions / 25 shared /
788 unconditional / 222 count-like; CE `0655190`; DLL
`3b6dc3d26c3eab51fa5be4272252b926deaf10b6d4e7bedb094c2c6c8272ab14`).

Method: mechanical, closed-world. The installed game + DLC is the
authoritative source for modes/overlays; the baseline merged DB snapshot
(`data/local/DebugGameplay_official.sqlite`, sha256
`8d8149338398195dda727318ab168ce420419d60e04ea9ad9ad4c133786c27a1`,
10,207,232 bytes, 428 tables) is the authoritative source for
standard-game pairs. Nothing was guessed from filenames: conditional
files were resolved from official modinfo actions/criteria, and every
modifier-root table was derived from schema (case-insensitive
`ModifierId`-column scan: 28 tables = 25 association roots + `Modifiers`
+ `ModifierArguments` + `ModifierStrings`). Nested attached modifiers
were traversed with cycle detection (304 `ModifierId`-argument edges, 0
cycles; 1 dangling reference, a unit-ability id, not a modifier).
Numeric rule: strict value-float parse, no name denylist (comma-lists,
text ids and empties rejected). An independent re-enumeration reproduced
every per-table count exactly. Full pair-level data:
`civ6x10/rules/support_frontier.yml` (25 roots, 2958 pairs, 8 modes,
508 direct fields). Scanner scratch outputs: `spike/8a-frontier/`.

Pair universe: 2958 distinct numeric (root-table, ModifierId, argument)
pairs = 2002 uncovered + 956 in-registry occurrences (931 distinct
production pairs located in the DB; 79 missing, all explained: 57
synthetic `X10_*` wonder-direct bridge helpers that exist only in the
generated registry by design, plus 22 secret-society governor/promotion
modifiers from mode overlays absent from the no-overlay snapshot).

## 1. Baseline sanity numbers (spec §4)

Reproduced mechanically against the baseline DB (nested-closure,
numeric-only). 20/21 exact; sole diff explained, no coverage missing.
Nesting was required: direct-only counts fall short in 8 tables.

| root table | expected raw uncovered | actual | verdict |
|---|---|---|---|
| UnitAbilityModifiers | 210 | 210 | match |
| UnitPromotionModifiers | 198 | 198 | match |
| GreatPersonIndividualActionModifiers | 176 | 176 | match |
| BuildingModifiers | 115 | 115 | match (strict rule excludes 2 comma-list amounts) |
| BeliefModifiers | 56 | 56 | match |
| EmergencyRewards | 54 | 54 | match |
| ImprovementModifiers | 48 | 48 | match |
| CommemorationModifiers | 46 | 46 | match |
| ResolutionEffects | 37 | 36 | explained diff (see below) |
| GoodyHutSubTypes | 30 | 30 | match |
| AllianceEffects | 28 | 28 | match |
| GameModifiers | 23 | 23 | match |
| DistrictModifiers | 21 | 21 | match |
| CivicModifiers | 18 | 18 | match |
| EmergencyBuffs | 15 | 15 | match |
| ProjectCompletionModifiers | 14 | 14 | match |
| TechnologyModifiers | 13 | 13 | match |
| GreatPersonIndividualBirthModifiers | 2 | 2 | match |
| TraitModifiers | 815 | 815 | match (strict rule excludes 8 multi-yield lists) |
| PolicyModifiers | 56 | 56 | match |
| GovernorPromotionModifiers | 27 | 27 | match |

ResolutionEffects 36 vs 37: the only remaining numeric-named candidate,
`(APPLY_RES_UNIT_COMBAT_DEBUFF, Amount)`, holds the text
`WC_RES_UNIT_COMBAT_DEBUFF` (official-data quirk; the id is absent from
`Modifiers`), uncountable under any value-based rule. The baseline 37
implies a one-pair name leniency or a one-row snapshot difference.

GovernmentModifiers closed as a bonus finding: 47 rows, 44 numeric pairs,
43 in-registry (= 18 governments + 25 shared definitions), 1 uncovered
(`FASCISM_WAR_WEARINESS`/`Overall`, a scope flag). Empty association
roots in the snapshot: ComplimentModifiers, GovernorModifiers,
GreatWorkModifiers. `GreatPersonIndividualIconModifiers` is not a
modifier root (no ModifierId column).

## 2. Support-frontier matrix (spec §19)

Columns: raw numeric | already supported | strong | count-like |
unresolved (semantic-research + product-decision) | excluded (prior
audit/floor + structural + cost + timer + base-stat + no-target) |
global/leakage | new-transform-needed | owner-safe | proposed module.
Mode rows carry overlay pairs + in-registry overlap. Full overlay file
lists with SHA-256 live in the yml (`game_modes[].overlay_files`) and
`spike/8a-frontier/modes.json`; short SHAs per gameplay file in §3.

| system | source/root | raw | sup | strong | clike | unres | excl | glob | new-tr | owner-safe | proposed module |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Beliefs (non-Pantheon) | BeliefModifiers | 87 | 31 | 30 | 0 | 6 | 20 | 0 | 0 | yes | Religion |
| Great People | GPIAction 176 + GPIBirth 2 | 178 | 0 | 77 | 40 | 10 | 51 | 0 | 0 | yes | Great People |
| Unit Promotions | UnitPromotionModifiers | 199 | 1 | 90 | 27 | 37 | 44 | 0 | 0 | yes | Promotions |
| Unit Abilities | UnitAbilityModifiers | 210 | 0 | 115 | 26 | 15 | 53 | 1 | 0 | mixed | Promotions & Abilities |
| Eras / Dedications | CommemorationModifiers | 46 | 0 | 13 | 25 | 6 | 2 | 0 | 0 | yes | Eras & Diplomacy |
| Tech / Civic unlocks | Civic 18 + Tech 13 | 31 | 0 | 11 | 12 | 2 | 5 | 1 | 0 | yes | Eras & Diplomacy |
| Projects | ProjectCompletionModifiers | 14 | 0 | 7 | 0 | 1 | 0 | 1 | 0 | yes | Projects |
| Goody Huts | GoodyHutSubTypes | 30 | 0 | 8 | 14 | 1 | 7 | 0 | 0 | yes | Tribal Villages |
| Alliances | AllianceEffects | 28 | 0 | 0 | 0 | 20 | 8 | 0 | 0 | shared | Eras & Diplomacy |
| Emergencies | EmergencyBuffs 15 + Rewards 54 | 69 | 0 | 34 | 15 | 3 | 9 | 8 | 0 | mixed | Eras & Diplomacy |
| World Congress | ResolutionEffects | 36 | 0 | 1 | 1 | 1 | 6 | 21 | 0 | no | Eras & Diplomacy (favor/slots only) |
| Infrastructure mods | Building 115 + District 21 + Improvement 48 | 184 | 94 | 0 | 0 | 147 | 37 | 0 | 0 | n/a | Infrastructure (scope-B only) |
| Traits remainder | TraitModifiers | 827 | 427 | 38 | 5 | 26 | 295 | 0 | 0 | yes | existing Traits module (no new toggle) |
| Policies remainder | PolicyModifiers | 364 | 308 | 5 | 1 | 8 | 42 | 0 | 0 | yes | existing Policies module |
| Governments remainder | GovernmentModifiers | 44 | 43 | 0 | 0 | 0 | 1 | 0 | 0 | yes | existing Governments module |
| Governors remainder | GovernorPromotionModifiers | 75 | 48 | 1 | 1 | 8 | 16 | 1 | 0 | mixed | existing Governors module |
| Minor-civ traits | TraitModifiers (MINOR_CIV_*) | 93 | 0 | 0 | 0 | 93 | 0 | 0 | 0 |? | Suzerain module or City-States (decision) |
| Diplomacy agendas | TraitModifiers (EFFECT_DIPLOMACY_*) | 319 | 0 | 0 | 0 | 0 | 0 | 319 | 0 | no | none (never scale AI opinion) |
| Natural wonders / game | GameModifiers | 23 | 0 | 8 | 11 | 3 | 1 | 0 | 0 | yes | Wonders module (wonder-adjacent) |
| Victory / WMD | mixed tables | 23 | 4 | 0 | 0 | 15 | 4 | 0 | 0 | no | none without explicit product call |
| Difficulty handicaps | TraitModifiers | 3 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | no | none (never scale handicaps) |
| Direct numeric fields | 508 schema fields | 508 | n/a | 0 | 0 | 272 | 221 | ~15 | 0 | mixed | Infrastructure-direct (scope-B only) |

`unres` = NEEDS_SEMANTIC_RESEARCH + NEEDS_PRODUCT_DECISION. `excl` =
EXISTING_AUDIT_EXCLUDED + STRUCTURAL_OR_FILTER + COST_OR_PRICE +
TIMER_OR_DURATION + BASE_STAT_NOT_BONUS + NO_MEANINGFUL_MULTIPLIER_TARGET.
New transforms needed: none (see §7). Congress participant magnitudes
beyond favor/slots stay out: 21 global/targeted pairs.

Direct-field roles (508): bonus_magnitude 102, cap 69, base_stat 54,
cost 36, duration_timer 27, requirement_filter 20, chance 16,
global_intensity 15, ai_weight 7, progression_threshold 5, selector 6,
structural_internal 151. Bonus-magnitude fields are overwhelmingly
ordinary infrastructure yields (adjacency ±1–4, GPP/turn 1–5, plot
yields), costs are true prices (Buildings.Cost 1–1850, Civics.Cost
20–3500), chances are selection weights (GoodyHut Weight 0–100).
All four `*_MODE` tables exist in the snapshot with 0 rows (overlays
absent), as do `HeroClassProgressions` et al. outcome tables.

## 3. Game-mode audits (spec §7)

All 8 modes derived mechanically from 42 official modinfos (5 Base +
37 DLC) + setup parameters; count matches 8==8 with no extras.
`GAMEMODE_RANDOM` is a visibility-gating pseudo-config, not a mode;
`GAMEMODE_BARBARIANCLANS` (no underscore) is an icon string only. Two
overlay files referenced by modinfos are absent on disk (BarbarianClans
`Translations_Text_MODE.xml`, TreeRandomizer `Translations_Text.xml`;
flagged missing). SHAs below are short (16 hex); full SHAs + criteria in
the yml. Pair counts are unique overlay (ModifierId, argument) pairs and
their production overlap.

### Apocalypse — GAMEMODE_APOCALYPSE, bool default 0, DLC GranColombia_Maya (GS only)
14 overlays / 10 gameplay (`GranColombiaMaya_Mode_Expansion2`;
`..._Vikings` for the RandomEvents_Vikings file). Gameplay files:
`GranColombia_Maya_AI_MODE.xml` c1cd6e922be42bb4,
`..._Civilopedia_MODE.xml` fdeaac5ef67eaf51,
`..._Emergencies_MODE.xml` f394acc5a9e8269e,
`..._Features_MODE.xml` 3c29229b6a6c6514,
`..._GameCapabilities.xml` 28c7a3f880b5618f,
`..._RandomEvents_MODE.xml` a40201859a3de219,
`..._UnitOperations_MODE.xml` c1547306ce6f912d,
`..._UnitPromotions_MODE.xml` e8cbc42a19c6d965,
`..._Units_MODE.xml` aa8edca5ab2bb213,
`..._RandomEvents_Vikings_MODE.xml` 94db6c5ce57fba96.
24 overlay pairs, 0 in production. Soothsayer promotions/charges and
Appease-the-Gods rewards are clean participant magnitudes; disaster and
climate globals (intensity, frequency, RandomEvents weights) must never
scale with the multiplier. Verdict: NEEDS_PRODUCT_DECISION on the
bonus-vs-disaster-system boundary. Bonus the player receives and turning
the whole disaster system up are different products.

### Secret Societies — GAMEMODE_SECRETSOCIETIES, bool default 0, DLC Ethiopia (XP1/XP2)
21 overlays / 8 gameplay (Ethiopia + joint Babylon/Byzantium/Portugal
overlays; `Ethiopia_Mode_Expansion1/2`, joint
`Heroes_SecretSocieties_Mode`, `TowerDefense_SecretSocietyMode`).
Key files: `Ethiopia_SecretSocieties_MODE.xml` 0199ba145c0ad41d,
`..._Expansion1_MODE.xml` 8b61d9cf2a4f58c0,
`..._Expansion2_MODE.xml` f1ec83a344a5c356,
`..._GranColombia_Maya_MODE.xml` 601c6e524637c1ce,
`Babylon_Heroes_SecretSocieties_MODE.xml` 7d59382522a95e89,
`Byzantium_Gaul_SecretSocieties_MODE.xml` fe854f12571668dd,
`Portugal_Improvements_Secret_MODE.xml` 2481d4f39e1673cb.
136 overlay pairs, 22 in production (Owls/Voidsingers/Hermetic/Vampire
governor pairs via the governors module). Honest remainder: 114 pairs
covering society units, Ley-Line yields, buildings, improvements, city
projects, resource effects, Vampire builds. Current coverage of the mode
is promotion-magnitude-complete but system-partial. Verdict:
STRONG_CANDIDATE for the non-promotion remainder. The 22 known pairs
prove mode disablement removes definitions from the DB (absent from the
no-overlay snapshot entirely, not even in `Modifiers`).

### Tech and Civic Shuffle — GAMEMODE_TREE_RANDOMIZER, bool default 0, DLC TreeRandomizer (all rulesets)
14 overlays / 5 gameplay (`TreeRandomizer_Mode[_Expansion2]`):
`TreeRandomizer_Civics_MODE.xml` 123c4abbd70a4818,
`..._Technologies_MODE.xml` 636d5c9553e51dab,
`..._Expansion2_MODE.xml` bd419b3faa18c9fd, plus capabilities/civilopedia.
0 modifier pairs. Verdict: NO_MEANINGFUL_MULTIPLIER_TARGET. Randomized
prerequisites, placement, costs and visibility are not bonuses.

### Dramatic Ages — GAMEMODE_DRAMATICAGES, bool default 0, DLC Byzantium_Gaul (XP1/XP2)
19 overlays / 7 gameplay (`DramaticAges_[Expansion1|Expansion2_]Mode`,
Georgia variant): `..._DramaticAges_Expansion1_MODE.xml`
3fa2da139e70fac1, `..._DramaticAges_MODE.xml` cce5c81011490901 (shared
XP1/XP2 bytes), `..._DramaticAges_Expansion2_MODE.xml` 2bede7036c53b775,
`..._DramaticAges_Georgia_MODE.xml` a84c4654f3b6ccaf, remove-data +
capabilities. 149 overlay pairs, 8 already in production (golden/dark
policy cards reachable through the policies module — the overlay was
absent from the baseline production audit, and exactly this overlap was
missed). Remainder: 141 pairs of age-card, loyalty and era-score
magnitudes. Verdict: STRONG_CANDIDATE.

### Heroes & Legends — GAMEMODE_HEROES, bool default 0, DLC Babylon (all rulesets + civ overlays)
33 overlays / 10 gameplay (`Heroes_Mode[_Expansion1|2]`,
`Heroes_Mode_IndonesiaKhmer[_XP1|_XP2]`, `Heroes_Mode_Poland`,
`Heroes_SecretSocieties_Mode`): `Babylon_Heroes_MODE.xml`
300cd257e39bead7, `..._XP1_MODE.xml` dcd40d337d9b35b1,
`..._XP2_MODE.xml` 54e4637b4981132b, plus 13 units, 14 abilities,
13 projects, HeroClassProgressions direct fields. 176 overlay pairs, 0
in production. Hero ability magnitudes are strong; Hero base combat-stat
progression, charges, recall costs/discounts, lifespan and project
effects must be separated first — base Hero CombatStrength must not be
multiplied implicitly. Verdict: NEEDS_PRODUCT_DECISION on the
base-stat/charges/cost separation.

### Monopolies and Corporations — GAMEMODE_MONOPOLIES, bool default 0, DLC KublaiKhan_Vietnam (all rulesets)
26 overlays / 5 gameplay (`Monopolies_Mode[_Base|_Expansion1|_Expansion2|_GranColombiaMaya]`):
`..._Monopolies_MODE.xml` 84d828f3f28c37e6,
`..._Monopolies_XP1_MODE.xml` 0f71cfeb32ddd0de,
`..._Monopolies_XP2_MODE.xml` 5a179ab2144a0acc,
`..._Monopolies_GranColombiaMaya_MODE.xml` a459af1f128b7525.
125 overlay pairs (28 projects incl. corporations, ResourceCorporations
definitions, Product great works, industry/corporation bonuses, monopoly
tourism, improvement yields), 0 in production. Highest-density clean
magnitude set of any mode. Verdict: STRONG_CANDIDATE.

### Barbarian Clans — GAMEMODE_BARBARIAN_CLANS, bool default 0, DLC BarbarianClansMode (GS only)
28 overlays / 3 gameplay (`BarbarianClansMode`,
`BarbarianClansMode_Expansion2`, joint `TowerDefense_BarbarianClansMode`
via Portugal): `BarbarianClansMode_GameplayData.xml` 0a4f24cf64a9b2ab,
`..._RemoveData.xml` c57b39eb2a306c85,
`Portugal_Barbarians_MODE.xml` e05e52242b8fa49d. 0 modifier pairs:
tribe tables + 9 global parameters (clan progress, immunity durations,
hire/ransom/bribe values as direct fields). Raid/disperse/hire rewards
are clean player bonuses; prices paid, progress thresholds and timers
stay out by rule (direct-field classification). Verdict:
STRONG_CANDIDATE for the reward slice.

### Zombie Defense — GAMEMODE_TOWERDEFENSE, bool default 0, DLC Portugal (XP1/XP2)
17 overlays / 9 gameplay (`TowerDefense_Mode[_Expansion2]`, joint
BarbarianClans/SecretSociety criteria): `Portugal_Units_MODE.xml`
c1f487f5add88c94, `..._Improvements_MODE.xml` ca9bb83e5d114efd,
`..._Projects_MODE.xml` f13f2783d3941061,
`..._GameEffects_MODE.xml` 5139e3fcc24bb42f,
`..._Barbarians_MODE.xml` e05e52242b8fa49d,
`VikingsLandmarks_TowerDefense_MODE.xml` 8848ca6e1747e34d. 44 overlay
pairs (mutation strength, traps, barricades, movement penalties,
damage, projects, control duration, spawn counts/chances, spy outbreak
effects), 0 in production. Verdict: NEEDS_PRODUCT_DECISION — player
benefit (traps/barricades/damage/duration) cannot be separated from
making Zombies themselves stronger without an explicit product boundary.

## 4. Standard-system audits (spec §8)

Religious Beliefs: 56 uncovered BeliefModifiers (Pantheons already
supported; 31 belief pairs already in the registry via overlap).
Follower/founder/enhancer/worship classes all represented; 30 strong
(yields, combat, housing, amenity, pressure, trade), 15 structural
(flags/thresholds), 6 percent-family (religious spread strength,
reliquaries scaling, monastic reduction), 5 prior exclusions. Verdict:
highest-value standard system; no new transform needed.

Great People: 178 pairs, 0 in production. 77 strong (one-off yields
60–3000, production grants, happiness, loyalty, tourism, trade-route
gold, GPP), 40 count-like (tech/civic boosts, relics, envoys, titles,
trade capacity, air/district slots, population, governor points, era
score), 10 research (war-weariness mitigation, percent tourism/scaling,
heal rates), 51 structural (grant flags, sentinels, spatial ranges,
diplo/trade direction flags). Comandante Generals retire effects split
the same way (heal/kill magnitudes research; titles count-like).
Verdict: second-highest standard value; needs the grant-semantics
pass at integration, not new transforms.

Unit Promotions: 199 pairs (1 in production). 90 strong (all combat
strengths incl. vs-domain/class, XP, plunder, GPP-per-kill, AA 40,
initiation gold, escape? no — escape is chance-research), 27 count-like
(movement, sight, range, attacks, air slots, rock-band levels, apostle
charges, spy levels), 37 research (spy chance/time, flanking/support
percents, evict, healing, tourism-bomb scaling, post-combat percent),
44 structural (capability flags: move-after-attack, ignore-terrain,
paradrop, conversions, stealth), 4 prior exclusions. Promotions and
abilities must not be conflated (separate roots, separate trees), but
one player-facing module can carry both.

Unit Abilities: 210 pairs, 0 in production. 115 strong (76 combat
strengths, 23 XP sources, plunder, holy-city/friendly-territory/
luxury/ally scalers, GPP-per-kill), 26 count-like, 15 research
(flanking/support/WMD percents, post-combat percent, healing), 46
structural (bypass/capture/convert/stealth/paradrop/ZOC/ignore flags),
5 prior exclusions, 1 global (FINEST_HOUR friendly-buff hits allied
units too). Many abilities are intrinsic unit rules; the audit already
separates them (flags stay out). A broad abilities module makes sense
only with that curation — the pair list is the curation input.

Eras / Dedications / Commemorations: 46 pairs. 13 strong (yields,
movement, XP, GPP, production, trade), 25 count-like (era-score
counters, charges, slots), 6 research (boost percents, spy-time and
purchase percents, tourism scaling), 2 structural. Dramatic Ages adds
its 141 overlay pairs on top (ordinary vs dramatic handled by mode
gating, not by effect).

Alliances: 28 pairs. 20 need the product decision (shared symmetric
definitions: both sides scale together by construction — trade yields,
combat, sharing, research agreement), 8 structural (direction flags).
Owner-scoped in the "all owners enabled" sense only if symmetric
scaling is declared desired. Safely gated behind one checkbox either
way; the decision is desirability, not safety.

Emergencies / Competitions: 69 pairs. 34 strong participant magnitudes
(favor 50–200, combat, tourism, GPT, rock-band sales, space-race... no:
space-race rates are research), 15 count-like (great-person classes,
boosts, envoys... ), 3 research, 8 global (TARGET-side effects scale
another player: war-weariness, GPT-to-target, envoy gold, identity,
pressure), 5 structural. Mechanical rule that generalizes: TARGET-side
modifiers are cross-player; MEMBER-side are participant bonuses.
Victory-point rewards (diplo/science VP) need an explicit product call.

World Congress: 36 pairs. Only favor (condemn 25) and trade capacity
(+1 slot) are safe participant magnitudes; victory ±2, government slots
±1 (count-like but global-rule), and 21 global/targeted magnitudes
(growth/loyalty/grievance/production/chop/trade/spy/strength) stay out
or need product calls. Selectable bonuses vs penalties vs global rule
changes are separated per effect in the yml.

Technologies / Civics: 31 pairs. 11 strong (embarked movement, tourism,
project production... no: project rate is research; strong = movement,
visibility, favor, tourism-district, GPP... ), 12 count-like (tokens,
spies, titles, routes, boosts), 2 research (tourism percents), 3
structural, 1 global (CO2 reduction — shared climate pool). Costs and
prerequisites are direct fields, never modifiers: not scaled unless
explicitly intended.

Buildings / Districts / Improvements: 184 uncovered modifier pairs (94
already supported via wonders/suzerain overlap) + ~150 direct
bonus-magnitude fields. THIS IS THE PRODUCT-SCOPE QUESTION. Scope A
(special systems/choices only): all 142 stay out. Scope B (ordinary
infrastructure yields/stats too): 142 + the direct adjacency/GPP/plot
fields come in. The audit quantifies both scopes and takes no implicit
position: every pair is NEEDS_PRODUCT_DECISION with its effect noted.
Recommendation: decide scope B explicitly or not at all; do not let it
in through the back door one effect at a time.

Projects: 14 pairs. 7 strong (aid gold, favor, loyalty), 1 research
(luxury-rate scaling), 1 global (sequestered carbon — climate pool),
5 victory/WMD (product call). Space-race VP-per-turn and nuke creation
are the sharp edges; everything else is ordinary reward magnitude.

Goody Huts: 30 pairs. 8 strong (yields 20–120, favor, XP), 14
count-like (units, boosts, relic, envoy, title, population, strategic
stockpile, upgrade, tech), 1 research (full heal), 7 structural
(scale/ignore flags). Reward quantities separate cleanly from reward
selection (Weight 0–100 stays out as chance/product).

Great Works / Products: standard GreatWorkModifiers root is empty in
the snapshot; mode Products (Monopolies) carry discount/product-yield
triples in the overlay. Standard great-work yields via buildings are
covered under infrastructure; no separate standard-game module needed.

## 5. DISCOVERED_BEYOND_REQUEST (spec §9)

Systems found that the prompt did not name:
- Natural-wonder magnitudes (GameModifiers: Eyesahara/Paititi plot
  yields, Pamukkale amenity, Zhangye GPP, Ikkil production rates,
  Dead Sea heal rate, Lysefjorden XP sentinel) + governor-title
  economy (11 game-wide title grants) in the same table.
- GovernmentModifiers closure (47 rows; 43 in-registry = 18
  governments + 25 shared; the table is done, not a frontier).
- Difficulty handicaps (HIGH_/LOW_DIFFICULTY scaling triads) — global
  by nature; must never scale.
- Minor-civ (city-state) traits: 93 MINOR_CIV_* magnitudes (yields,
  production, trade, GPP) with a genuine ownership question against
  the narrow suzerain-ownership precedent.
- The espionage system as a cross-cutting family (spy chance/time/
  levels/establish spread over promotions, policies, buildings,
  commemorations) — chance/time args need probability research as a
  family, not one effect at a time.
- Religious-unit subsystems (apostle charges/debater/evict/spread,
  rock-band levels/tourism-bombs, GDR abilities) inside promotions/
  abilities with their own count-like/percentage splits.
- Loyalty/identity pressure as a cross-cutting family (governor,
  trait, emergency, commemoration, great-person sources) with
  domestic/foreign scoping per pair.
- Era-score counters as a countable family (25 commemoration pairs).
- The trade-route yield family (origin/destination/others/domestic/
  international direction flags + amounts) spanning alliances,
  traits, policies, emergencies, great people — direction flags are
  structural everywhere; amounts need the shared-route ownership call.
- WMD/Sequestration/Victory-point awards as a needs-product-call
  family across emergencies, resolutions, projects, techs, civics.
- `GameEffects` (1158 rows) + `GameEffectArguments` (150) as the
  effect-definition catalog behind EffectType metadata (useful for
  future transform research, not player content).
- Mode-infrastructure facts: `GAMEMODE_RANDOM` pseudo-config,
  icon-only `GAMEMODE_BARBARIANCLANS`, two missing overlay files,
  joint-mode criteria (Heroes↔SecretSocieties, TowerDefense↔
  BarbarianClans/SecretSocieties), Heroes `AddUserInterfaces`
  precedent (supports the Part B channel analysis).

## 6. Overlap analysis (spec §10)

- 931/1010 production pairs located in the baseline DB; 79 missing,
  all explained (57 synthetic `X10_*` bridge helpers by design; 22
  secret-society overlay modifiers absent from the snapshot).
- Mode overlap with the registry: Dramatic Ages 8/149 (missed golden/
  dark cards now identified), Secret Societies 22/136, all other modes
  0 (Apocalypse 0/24, Heroes 0/176, Monopolies 0/125, Zombie 0/44,
  Barbarian/Shuffle 0/0). No mode content is secretly already scaled.
- Intra-frontier overlap: pairs reachable from multiple roots are
  recorded per root (2958 rows vs 2933 distinct); 25 shared
  definitions already have the "all owners enabled" treatment in
  production — the same semantics extends to alliance/emergency
  symmetric definitions if desired.
- Mode disablement removes definitions from the DB entirely (proven by
  the 22 SS pairs missing from `Modifiers` itself, not just from
  association tables). Owner boundaries for overlay content therefore
  hold by construction when the mode is off; the remaining question
  is in-mode scoping (participant vs target vs global), recorded per
  pair.
- No proposed module has unrepresentable owner boundaries: alliances
  and emergencies need the symmetric/participant verdicts above, which
  are product calls, not engine changes. No engine change is proposed
  in 8A.

## 7. Grouping, scores, order (spec §11–12)

Strategy evaluation: (A) one checkbox per DB system — precise but
~20 controls, fails understandability. (B) larger player concepts —
recommended, below. (C) per-mode checkboxes only for high-impact modes
— adopted inside Game Modes. (D) parent Game Modes + child toggles —
recommended for modes. (E) no new toggle where content belongs to an
existing category — adopted for traits/policies/governments/governors
remainders (fold into current modules, no UI change), minor-civ traits
(into Suzerain, pending ownership decision), natural-wonder magnitudes
(into Wonders as wonder-adjacent), tech/civic boosts (into Eras).

Recommended checkboxes (8 new max, conditional ones marked *):
Religion (beliefs) | Great People | Promotions & Abilities (one box,
curated) | Eras & Diplomacy (commemorations, tech/civic unlocks,
alliances participant, emergencies participant, congress favor/slots) |
Tribal Villages (goody) | Projects | Game Modes (parent + Monopolies,
Heroes, Dramatic Ages, Secret Societies remainder, Barbarian Clans,
Apocalypse participant slice, Zombie*) | Infrastructure* (scope-B only)
| Minor City-States* (into Suzerain, pending decision).

Scores (FUN / COVERAGE / SEM-CONF / OWN-SAFE / IMPL-ease / NO-NEWTR /
LIVE-cost-ease / UI-ease, 1–5):
- Religion: 4/4/4/5/4/5/4/4 — smallest, safest, proves the pipeline.
- Great People: 5/5/3/4/3/5/3/4 — biggest standard count, mixed grant
  semantics need the integration pass.
- Promotions & Abilities: 5/5/4/4/3/4/3/3 — every unit interaction goes
  absurd; intrinsic curation is done, one FINEST_HOUR-type exception
  documented.
- Eras & Diplomacy: 3/4/4/3/3/5/3/3 — bundle value, ownership calls
  contained to alliances/congress edges.
- Monopolies slice: 5/4/4/5/3/5/3/4 — densest clean set, mode-gated
  (zero standard-game risk).
- Heroes slice: 4/4/3/4/2/4/2/3 — base-stat separation is the work.
- Goody/Projects: 3/2/4/5/4/5/5/4 — cheap, safe, small.
- Infrastructure: 4/5/3/2/2/5/2/2 — huge but gating on scope-B.
- Zombie/Apocalypse participant slices: 3/2/2/2/2/5/2/3 — boundary
  questions dominate.

Recommended implementation order:
- 8B: Religion + Promotions & Abilities + Great People (core fun,
  owner-safe, no new transforms; ~370 strong/count-like magnitudes;
  validates the special-systems reading and the overlay-aware audit
  method on Dramatic-Ages cards).
- 8C: Monopolies + Heroes ability slices (mode-gated), Eras &
  Diplomacy bundle, Goody + Projects, remainder folds into existing
  modules (no UI change).
- Later: Dramatic Ages remainder, Barbarian Clans, Apocalypse/Zombie
  participant slices (pending boundaries), Secret Societies remainder,
  minor-civ traits (pending ownership), Infrastructure (pending scope-B).
- Never: agendas, difficulty, victory points, WMD, disaster globals,
  shuffle, costs, timers, base stats.

Top 3: (1) Promotions & Abilities — 90+115 strong plus ~50 count-like;
every unit interaction becomes absurd; promotion owners are unit
owners. (2) Great People — 77+40; GP strategies become builds; grant
semantics need the integration pass. (3) Monopolies & Corporations —
125 overlay pairs, densest clean set, mode-gated to zero
standard-game risk. (Heroes is fourth: 176 pairs but base-stat
separation + 13 units/projects make it heavier than its count
suggests — this is where the audit deliberately diverges from raw
row-count sorting.)

RELEASE-NOW VS EXPAND-FIRST: release now. v1.0 already delivers the
absurd-build fantasy across 7 systems with a live-validated 1010 core.
The top-3 expansions add ~370 candidate magnitudes (~37% more pair
coverage) but each needs its own audit/certification/live-validation
campaign plus new module bits and UI; 8B alone is another full
validation cycle. Delaying first publication front-loads risk and
postpones user feedback for breadth that is cleanly additive later.
All expansion work is v1.1 material with no breaking changes. The one
thing worth doing pre-1.0 is the custom-label range clarification
(`Custom Multiplier (0 to 100)`, Part B), which is display-text-only.

New transforms needed: none. Every magnitude candidate fits an
existing family (canonical, combat, discount, count-like whole-unit)
pending per-effect certification; percent/chance/mitigation families
need research, not new transforms. That negative result is load-bearing:
expansion is audit + validation work, not engine work.

## 8. Custom Multiplier UX (Part B summary)

Range label: `Custom Multiplier (0 to 100)` — word form per the only
official style evidence (`LOC_GAME_REALISM_DESCRIPTION`: "Choose from
a setting of 0 … to 4"; 115 `(N-N)` hits are all date ranges; hyphen
risks misreading as a minus). Tooltip stays
`Enter a value from 0 to 100. ...` (already production text).
Architectures: (A) engine-impossible (no float domain; `IntRange` is
integer-slider-only; `text` has zero validation —
`SetupParameters.lua:1030-1035,1043-1049`; `AdvancedSetup.lua:952-979`).
(B)/(D) no supported load channel (zero `AddUserInterfaces`/
`ReplaceUIScript`/Lua `ImportFiles` in 42 modinfos' FrontEndActions;
all 8 modes extend setup through config-database rows). (C) requires
replacing shared setup files — guaranteed conflicts with CQUI/YnAMP-
style setup overrides for a veto the native error model cannot express
for text params. (E) feasible via `AddGameplayScripts` but post-commit
only — informational complement at best. (F) recommended: visible
range + tooltip + fail-closed + lifecycle log, zero compatibility cost.
No frontend Lua prototype was built, deliberately: any pre-game
enforcement prototype must replace `AdvancedSetup.lua`, prejudging the
rejected architecture (C), and the safety property is already
measured-live. Safest pre-game invalid UX: the `(0 to 100)` label +
tooltip + README/FAQ fail-closed table; Start Game stays available
(the framework cannot gate text params), invalid input resolves to
`writes DISABLED` with an explicit log reason.

Invalid-input matrix (preset = Custom(101) except where noted):
blank → INT32 0 → off-equivalent disarmed (measured-live; bit-identical
to explicit 0 — blank is indistinguishable from 0 at the native layer);
whitespace → raw string, no trim → fail-closed (inferred);
`abc` → string variant → fail-closed, undecodable-variant (measured);
`7,3` → string variant (period-only materialization) → fail-closed
(source-derived + log hint; no live comma run); `-1`/`101` → INT32
out-of-range → fail-closed (measured); `100.1` → FLOAT32 out-of-range →
fail-closed (source-derived, same check); `0` → in-range k=0 →
disarmed, Off-equivalent (measured pattern); `0.1`/`0.5` → arm
(source-derived, same accept path as measured); `7.3` → arms,
801/209 (measured); `100` → arms (source-derived). 0 == Off in net
effect (log reason differs). Exponential/`NaN`/`Inf` strings: the
reader never parses strings (only engine-materialized INT32/FLOAT32;
`VariantToDouble` rejects non-finite floats with `f == f` and range
checks), so any such input fails closed unless the engine itself
materializes it — and even a materialized non-finite float is
rejected. Production policy stands: never clamp, never round, never
malformed-to-zero; invalid Custom disables transforms; no fallback to
×10 or the legacy key. Full table:
`spike/8a-frontier/invalid_input_matrix.md`.

## 9. Files and freeze

New/changed this phase (research only): `civ6x10/rules/support_frontier.yml`
(new), `docs/SUPPORT_FRONTIER.md` (new), `spike/8a-frontier/` (scanner
outputs + disposable scripts), `tests/test_support_frontier.py` (new),
`civ6x10/release_surface.py` (inventory entries only). Production
untouched: registry 1010, CE `0655190`, DLL `3b6dc3d2...ab14`, setup/
config/branding identical, no publication actions, no prototype mod
files, no game/Steam launches (all vandalism-free: install and DB were
opened read-only; the DB was scanned via a temp copy).
