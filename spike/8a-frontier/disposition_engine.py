"""Phase 8A frontier disposition engine (disposable research script).

Reads: spike/8a-frontier/frontier_pairs.json (uncovered numeric pairs),
  in_registry_pairs.json, modes.json, direct_tables.json, db_scan.json,
  production manifests + ledger, audit/backlog exclusion records.
Writes: civ6x10/rules/support_frontier.yml
Rule order is first-match-wins; every pair gets (disposition, system, note).
"""
import json
import os
import sys
from collections import Counter

REPO = r'C:\Users\alex\Desktop\Code\civ6-x10'
OUT = os.path.join(REPO, 'spike', '8a-frontier')
sys.path.insert(0, REPO)
import yaml  # noqa: E402
from civ6x10.bridge import collect_registry_rows  # noqa: E402
from civ6x10.production import build_production_registry  # noqa: E402

pairs = json.load(open(os.path.join(OUT, 'frontier_pairs.json')))
inreg = json.load(open(os.path.join(OUT, 'in_registry_pairs.json')))
modes_doc = json.load(open(os.path.join(OUT, 'modes.json')))
direct_doc = json.load(open(os.path.join(OUT, 'direct_tables.json')))
db_doc = json.load(open(os.path.join(OUT, 'db_scan.json')))

entries, _report = build_production_registry(collect_registry_rows(REPO))
PROD = {(e['modifier_id'], e['argument']) for e in entries}
assert len(PROD) == 1010, len(PROD)

# ---- exclusion records ----
LEDGER = { (r['modifier_id'], r['argument']): r['resolution']
           for r in json.load(open(
               r'C:\Users\alex\AppData\Local\Temp\opencode\ledger.json'))}
MAN_REFUSED = set()
for mod in ['traits', 'policies', 'governments', 'pantheons', 'wonders',
            'governors', 'suzerain']:
    try:
        m = yaml.safe_load(open(f'{REPO}/manifests/{mod}.yml'))
    except FileNotFoundError:
        continue
    for x in m[mod]:
        if x.get('status') != 'ok' and str(
                x.get('transformation', '')).startswith('refused'):
            MAN_REFUSED.add((x['modifier_id'], x['argument_name']))

GOV_EXCL = set()
gov = yaml.safe_load(open(f'{REPO}/civ6x10/rules/governor_audit.yml'))
for r in gov.get('engine_integral_rows', []):
    if r.get('disposition') == 'EXCLUDED' and r.get('modifier_id'):
        GOV_EXCL.add((r['modifier_id'], r.get('argument')))

BACKLOG = {}
blog = yaml.safe_load(open(f'{REPO}/civ6x10/rules/semantic_backlog.yml'))
for r in blog.get('rows', []):
    if r.get('modifier_id'):
        BACKLOG[(r['modifier_id'], r.get('argument'))] = r

# ---- rule sets ----
FLAG_ARGS = {'Ignore', 'UniqueOverride', 'KeepOverflow', 'Origin',
             'Destination', 'CityStatesOnly', 'HiddenAgenda', 'Offensive',
             'AffectDestination', 'AffectOrigin', 'Domestic',
             'InternationalMajors', 'InternationalMinors', 'IsWonder',
             'IncludeWonder', 'IncludeCivilian', 'Intercontinental',
             'MustReplaceImprovement', 'YieldBasedOnAppeal',
             'OnlyWhenDefeatedEarlierEraUnit', 'ForeignCities',
             'DomesticCities', 'OncePerCity', 'Foreign', 'Disabled',
             'Disable', 'NoDamage', 'NoSpread', 'Converts', 'CanCapture',
             'CanMove', 'CanAttack', 'CanSee', 'CanDrop', 'CanRaid',
             'CanFight', 'Bypass', 'Enable', 'Enter', 'Exert',
             'EscortMobility', 'NoReduction', 'Valid', 'RemoveOthers',
             'OtherPlayers', 'TechBoost', 'IgnoreDefensible', 'EntireCity',
             'GrantTechIfBoosted', 'CanPurchase', 'Protected', 'Prevent',
             'Enabled', 'UseAdvancedPillaging', 'UseAdvancedCoastalRaid',
             'Scale', 'Favored', 'Accumulates', 'Corps', 'Defense',
             'Offense', 'VictoryResolution', 'WhichEffect', 'NoTourism',
             'TargetOnly', 'NoRemove', 'BanDistrictBuildings',
             'LandVictorySpread', 'Convert', 'NoForeignSpread',
             'AlwaysLoyal', 'Religious', 'BoostsWonders', 'Hidden',
             'SeeHidden', 'DeltaWithOpponent', 'Score', 'Turns',
             'PerXLevels', 'MinScore', 'Range', 'ConvertCity',
             'NoSpread', 'CanAttack', 'CanMove', 'Member',
             'ForceRetreat', 'Overall', 'CaptureOwnedTerritory',
             'ConvertsCity'}
TIMER_ARGS = {'Turns', 'Turn', 'TurnsActive', 'IncrementTurns',
              'ReductionTurns', 'Timer', 'Duration', 'Time'}
CAP_ARGS = {'MaxValue', 'MaxEffectMagnitude', 'MaxDiploModifierMagnitude'}
THRESH_ARGS = {'TilesRequired', 'RequiredAppeal', 'PerXItems',
               'HighScoreThreshold', 'LowScoreThreshold',
               'TileImprovementHighThreshold', 'TileImprovementLowThreshold',
               'TileImprovementPreferenceValue', 'PlotFeatureRemovalValue',
               'NationalParkConstructionValue', 'MessageThrottle',
               'CityGainLowerBound', 'CityGainUpperBound', 'ScorePerCity',
               'BottomPercentage', 'TopPercentage'}
PERCENT_ARGS = {'ScalingFactor', 'ReductionPercent', 'Multiplier',
                'Percent', 'SpreadMultiplier', 'TechEnabledSpreadMultiplier',
                'UnitProductionPercent', 'BuildingProductionPercent',
                'UnitCostPercent', 'PercentDefeatedStrength', 'Modifier'}
SPATIAL_ARGS = {'Range'}
ZERO_MEANING = set()  # filled below by value==0 special cases

INFRA_TABLES = {'BuildingModifiers', 'DistrictModifiers',
                'ImprovementModifiers'}


def fnum(v):
    try:
        return float(str(v).strip())
    except (ValueError, TypeError):
        return None


def dispose(p):
    t, mid, arg = p['root_table'], p['modifier'], p['argument']
    val = p['value']
    eff = p.get('effect', '')
    fv = fnum(val)
    key = (mid, arg)

    def S(sys, note, disp):
        return disp, sys, note

    # R1: recorded production-gate / manifest exclusions
    if key in LEDGER and LEDGER[key] != 'certified':
        res = LEDGER[key]
        return S('audit:' + t.lower(), 'sem-floor/curated exclusion '
                 + res + ' despite manifest-ok; floor stands',
                 'EXISTING_AUDIT_EXCLUDED')
    if key in MAN_REFUSED:
        return S('audit:' + t.lower(), 'manifest refused_no_multiplier',
                 'EXISTING_AUDIT_EXCLUDED')
    if key in GOV_EXCL:
        return S('governors_remaining', 'governor audit EXCLUDED',
                 'EXISTING_AUDIT_EXCLUDED')
    if key in BACKLOG:
        b = BACKLOG[key]
        if b.get('resolution') == 'RESOLVED_EXCLUDED':
            return S('audit:' + t.lower(), 'backlog RESOLVED_EXCLUDED: ' +
                     str(b.get('resolution_rationale', ''))[:160],
                     'EXISTING_AUDIT_EXCLUDED')
        if b.get('resolution') == 'STILL_SEMANTICALLY_UNRESOLVED':
            return S('system:' + t.lower(), 'backlog still unresolved: ' +
                     str(b.get('group', ''))[:120],
                     'NEEDS_SEMANTIC_RESEARCH')
    # R2: zero magnitudes do nothing
    if fv == 0 and arg in ('Amount', 'Modifier', 'Delta'):
        return S('none', 'zero magnitude; nothing to multiply',
                 'NO_MEANINGFUL_MULTIPLIER_TARGET')
    # R3: flags / selectors
    if arg in FLAG_ARGS and fv in (0, 1):
        return S('none', 'boolean/selector flag, not a bonus magnitude',
                 'STRUCTURAL_OR_FILTER')
    # R3b: spatial/distance parameters are not bonus magnitudes
    if arg in SPATIAL_ARGS:
        return S('none', 'spatial/distance parameter, not a bonus magnitude',
                 'STRUCTURAL_OR_FILTER')
    # R3d: base-stat unlock values and power/requirement thresholds
    if arg in ('DefenseValue',) or eff in (
            'EFFECT_ADJUST_CITIES_HAS_URBAN_DEFENSES',
            'EFFECT_ADJUST_CITY_REQUIRED_POWER'):
        return S('none', 'base stat / requirement threshold, not a bonus',
                 'STRUCTURAL_OR_FILTER')
    # R3c: cosmetic naming/level markers
    if eff == 'EFFECT_ADJUST_UNIT_EXPERIENCE_LEVEL':
        return S('none', 'cosmetic naming/level marker, not a magnitude',
                 'STRUCTURAL_OR_FILTER')
    # R4: timers
    if arg in TIMER_ARGS:
        return S('none', 'duration/timer parameter',
                 'TIMER_OR_DURATION')
    # R5: caps and thresholds
    if arg in CAP_ARGS or arg in THRESH_ARGS:
        return S('none', 'cap/threshold/AI-scoring parameter',
                 'STRUCTURAL_OR_FILTER')
    # R5b: price-discount percents belong to the certified discount
    # family (not the excluded percent-scaling precedent)
    if arg in PERCENT_ARGS and ('DISCOUNT' in eff or 'LEVY' in eff or
                                'PURCHASE' in eff or 'COST' in eff):
        return S('system:' + t.lower(),
                 'price-discount percent; discount family exists, '
                 'per-effect certification at integration',
                 'STRONG_CANDIDATE')
    # R5c: global tourism percent scalings need research
    if eff in ('EFFECT_ADJUST_PLAYER_TOURISM',):
        return S('research:percent',
                 'global tourism percent scaling; per-effect scaling '
                 'semantics need research',
                 'NEEDS_SEMANTIC_RESEARCH')
    # R6: percent / scaling family
    if arg in PERCENT_ARGS:
        return S('research:percent',
                 'percent/scaling magnitude; percentage-factor and '
                 'discount semantics need per-effect research',
                 'NEEDS_SEMANTIC_RESEARCH')
    # R6b: percent-like rate effects (yield modifiers, per-bomb yields,
    # foreign-spread strength) need scaling-semantics research
    if eff in ('EFFECT_ADJUST_BUILDING_YIELD_MODIFIER',
               'EFFECT_ADJUST_UNIT_YIELD_PER_TOURISM_BOMB',
               'EFFECT_ADJUST_UNIT_FOREIGN_SPREAD_MODIFIER'):
        return S('research:percent',
                 'percent/rate-scaling magnitude; per-effect scaling '
                 'semantics need research',
                 'NEEDS_SEMANTIC_RESEARCH')
    # R6c: buffs that also strengthen allied units leak cross-player
    if 'FRIENDLY_BUFF' in mid:
        return S('diplomacy_allies',
                 'combat buff also applies to allied units, not only '
                 'your own',
                 'GLOBAL_OR_CROSS_PLAYER_LEAKAGE')
    # R7: chance / probability
    if '_CHANCE' in eff or 'PROBABILITY' in eff or arg == 'Chance':
        return S('research:probability',
                 'chance/probability magnitude; probability-transform '
                 'certification needed per effect',
                 'NEEDS_SEMANTIC_RESEARCH')
    # R8: diplomacy/agenda opinion mechanics are cross-player by nature
    if eff.startswith('EFFECT_DIPLOMACY_'):
        return S('diplomacy_agendas',
                 'AI relationship-opinion mechanic; tunes how other '
                 'players evaluate you',
                 'GLOBAL_OR_CROSS_PLAYER_LEAKAGE')
    # R9: difficulty handicaps
    if mid.startswith('HIGH_DIFFICULTY_') or mid.startswith(
            'LOW_DIFFICULTY_'):
        return S('difficulty', 'difficulty-handicap scaling; global',
                 'GLOBAL_OR_CROSS_PLAYER_LEAKAGE')
    # R10: minor-civ (city-state) traits: ownership question
    if mid.startswith('MINOR_CIV_'):
        return S('minor_civ_traits',
                 'city-state-owned trait magnitude; belongs to suzerain '
                 'module or a city-state system only by product decision '
                 '(cf. narrow suzerain-ownership precedent)',
                 'NEEDS_PRODUCT_DECISION')
    # R11: infrastructure tables: scope-A-vs-B product question
    if t in INFRA_TABLES:
        return S('infrastructure_' + t.lower().replace('modifiers', ''),
                 'ordinary infrastructure magnitude; in scope only if '
                 'Overpowered Bonuses means scope B (yields/stats), '
                 'not scope A (special systems/choices)',
                 'NEEDS_PRODUCT_DECISION')
    # R12: alliance system: shared symmetric definitions
    if t == 'AllianceEffects':
        return S('alliances',
                 'shared symmetric definition; both sides scale together '
                 'by construction - product call whether desired',
                 'NEEDS_PRODUCT_DECISION')
    # R13: emergency TARGET effects hit another player
    if 'TARGET' in mid and t in ('EmergencyRewards', 'EmergencyBuffs'):
        return S('emergencies',
                 'scales an effect applied to the emergency TARGET '
                 '(another player)',
                 'GLOBAL_OR_CROSS_PLAYER_LEAKAGE')
    # R14: victory points change win conditions
    if 'VICTORY_POINTS' in eff:
        return S('victory_points',
                 'scales victory-point awards; changes win conditions - '
                 'explicit product call required',
                 'NEEDS_PRODUCT_DECISION')
    # R15: WMD stockpiles are global weapons
    if 'WMD' in eff or 'WMD' in mid:
        return S('wmd',
                 'nuclear-weapon stockpile/grant; global weapon - product '
                 'call required',
                 'NEEDS_PRODUCT_DECISION')
    # R15b: shared climate system (CO2, carbon sequestration)
    if 'CO2' in eff or 'CO2' in mid or 'SEQUESTER' in eff or \
            'CARBON' in eff:
        return S('global_systems',
                 'shared global climate pool/mechanic, not an owner-scoped '
                 'bonus',
                 'GLOBAL_OR_CROSS_PLAYER_LEAKAGE')
    # R15c: percent-like production/grievance/theming rates
    if eff in ('EFFECT_ADJUST_UNIT_PRODUCTION',
               'EFFECT_ADJUST_SPACE_RACE_PROJECTS_PRODUCTION',
               'EFFECT_ADJUST_CITY_ALL_MILITARY_UNITS_PRODUCTION',
               'EFFECT_ADJUST_UNIT_DOMAIN_PRODUCTION',
               'EFFECT_ADJUST_PLAYER_GRIEVANCE_DECAY',
               'EFFECT_ADJUST_AUTO_THEMED_BUILDINGS_WITH_X_SLOTS',
               'EFFECT_ADJUST_DISTRICT_ADJACENT_NATURAL_WONDER_PRODUCTION',
               'EFFECT_ADJUST_WONDER_ADJACENT_NATURAL_WONDER_PRODUCTION',
               'EFFECT_ADJUST_ALL_PROJECTS_PRODUCTION'):
        return S('research:rates',
                 'rate/percent production or progress mechanic; per-effect '
                 'scaling semantics need research',
                 'NEEDS_SEMANTIC_RESEARCH')
    # R15d: price-discount family (certified in production for percentage
    # discounts; new effects need per-effect certification, not research)
    if 'PURCHASE_COST' in eff or 'DISCOUNT' in eff or 'LEVY' in eff:
        return S('system:' + t.lower(),
                 'price-discount magnitude; discount family exists, '
                 'per-effect certification at integration',
                 'STRONG_CANDIDATE')
    # R16: war-weariness mitigation (negative scaling semantics)
    if 'WAR_WEARINESS' in eff:
        return S('research:mitigation',
                 'weariness-mitigation magnitude; negative-scaling '
                 'semantics need research',
                 'NEEDS_SEMANTIC_RESEARCH')
    # R17: healing rates (healing-caps precedent)
    if 'HEALING' in eff or eff in ('EFFECT_ADJUST_UNIT_HEAL',
                                   'EFFECT_ADJUST_UNIT_POST_COMBAT_HEAL'):
        return S('research:healing',
                 'healing-rate magnitude; cf. excluded healing-caps '
                 'precedent',
                 'NEEDS_SEMANTIC_RESEARCH')
    # R18: damage mitigation / protection (saturation)
    if ('DAMAGE' in eff and ('REDUCTION' in eff or 'PROTECTION' in eff
                             or eff == 'EFFECT_ADJUST_UNIT_DAMAGE')):
        return S('research:mitigation',
                 'damage-mitigation magnitude; saturation semantics need '
                 'research',
                 'NEEDS_SEMANTIC_RESEARCH')
    # R19: whole-unit grants / counts / slots / titles / scores
    COUNT_EFFECTS = ('EFFECT_GRANT_UNIT_IN_CITY',
                     'EFFECT_GRANT_UNIT_WITH_EXPERIENCE',
                     'EFFECT_GRANT_UNIT_IN_EACH_DISTRICT',
                     'EFFECT_GRANT_GREAT_PERSON_CLASS_IN_CITY',
                     'EFFECT_GRANT_RELIC',
                     'EFFECT_GRANT_SPY',
                     'EFFECT_GRANT_FREE_ENVOYS_HERE',
                     'EFFECT_GRANT_INFLUENCE_TOKEN',
                     'EFFECT_GRANT_PLAYER_RANDOM_TECHNOLOGY',
                     'EFFECT_GRANT_PLAYER_RANDOM_CIVIC',
                     'EFFECT_ADJUST_PLAYER_RANDOM_TECHNOLOGY_BOOST_GOODY_HUT',
                     'EFFECT_ADJUST_PLAYER_RANDOM_CIVIC_BOOST_GOODY_HUT',
                     'EFFECT_GRANT_RANDOM_TECHNOLOGY_BOOST_BY_ERA',
                     'EFFECT_GRANT_RANDOM_CIVIC_BOOST_BY_ERA',
                     'EFFECT_GRANT_FREE_RESOURCE_EXTRACTED',
                     'EFFECT_GRANT_PLAYER_FREE_RESOURCE_EXTRACTED',
                     'EFFECT_GRANT_FREE_RESOURCE_IN_CITY',
                     'EFFECT_GRANT_FREE_RESOURCE_FROM_UNIT_PLOT',
                     'EFFECT_ADJUST_PLAYER_GOVERNOR_POINTS',
                     'EFFECT_ADJUST_TRADE_ROUTE_CAPACITY',
                     'EFFECT_ADJUST_PLAYER_DISTRICT_AIR_SLOTS',
                     'EFFECT_ADJUST_CITY_EXTRA_DISTRICTS',
                     'EFFECT_ADJUST_EXTRA_GREAT_WORK_SLOTS',
                     'EFFECT_ADJUST_EXTRA_STARTING_POPULATION',
                     'EFFECT_ADJUST_CITY_POPULATION',
                     'EFFECT_ADJUST_UNIT_SPREAD_CHARGES',
                     'EFFECT_ADJUST_BUILDING_SPREAD_CHARGES',
                     'EFFECT_ADJUST_UNIT_NATURAL_WONDER_DEFERRED_CHARGES',
                     'EFFECT_ADJUST_UNIT_NUM_ATTACKS',
                     'EFFECT_ADJUST_PLAYER_ERA_SCORE',
                     'EFFECT_ADD_DIPLO_VISIBILITY',
                     'EFFECT_GRANT_AIR_SLOTS',
                     'EFFECT_ADJUST_UNIT_UPGRADE_GOODY_HUT',
                     'EFFECT_ADJUST_MOST_ADVANCED_STRATEGIC_RESOURCE_COUNT',
                     'EFFECT_GRANT_UNIT_YIELD_ADJACENT',
                     'EFFECT_ADJUST_UNIT_MOVEMENT',
                     'EFFECT_ADJUST_UNIT_SEA_MOVEMENT',
                     'EFFECT_ADJUST_UNIT_CLEAR_TERRAIN_START_MOVEMENT',
                     'EFFECT_ADJUST_UNIT_FRIENDLY_TERRITORY_START_MOVEMENT',
                     'EFFECT_ADJUST_UNIT_ENEMY_TERRITORY_START_MOVEMENT',
                     'EFFECT_ADJUST_PLAYER_EMBARKED_UNIT_MOVEMENT',
                     'EFFECT_ADJUST_UNIT_SIGHT',
                     'EFFECT_ADJUST_UNIT_ATTACK_RANGE')
    if (eff in COUNT_EFFECTS and arg in ('Amount', 'Delta')) or (
            eff.startswith('EFFECT_ADJUST_PLAYER_ERA_SCORE') and
            arg == 'Amount'):
        if 'GRANT_UNIT_YIELD_ADJACENT' in eff:
            return S('great_people',
                     'one-off adjacent-terrain yield blast; whole-unit '
                     'conditional applies',
                     'CANDIDATE_COUNT_LIKE')
        if 'MOVEMENT' in eff or 'SIGHT' in eff or 'RANGE' in eff:
            return S('system:' + t.lower(),
                     'whole movement/sight/range points; spatial-budget '
                     'review at integration (cf. sem-floor precedent)',
                     'CANDIDATE_COUNT_LIKE')
        return S('system:' + t.lower(),
                 'one-off grant/count/slot/score; whole-unit '
                 'conditional applies',
                 'CANDIDATE_COUNT_LIKE')
    # R20: XP magnitudes
    if 'EXPERIENCE' in eff and arg == 'Amount' and fv not in (-1, 0):
        return S('system:' + t.lower(), 'XP-gain magnitude',
                 'STRONG_CANDIDATE')
    if 'EXPERIENCE' in eff:
        return S('none', 'XP sentinel/flag value',
                 'STRUCTURAL_OR_FILTER')
    # R21: belief system (non-pantheon)
    if t == 'BeliefModifiers':
        return S('religion_beliefs',
                 'non-pantheon belief magnitude (follower/founder/'
                 'enhancer/worship)',
                 'STRONG_CANDIDATE')
    # R22: commemoration system (eras)
    if t == 'CommemorationModifiers':
        if 'ERA_SCORE' in eff:
            return S('eras', 'era-score counter; whole-number score',
                     'CANDIDATE_COUNT_LIKE')
        if 'BOOST' in eff:
            return S('research:boosts',
                     'tech/civic-boost progress percent; boost semantics '
                     'need research',
                     'NEEDS_SEMANTIC_RESEARCH')
        if 'PURCHASE' in eff or 'REDUCTION' in eff or 'SPY' in eff:
            return S('research:percent',
                     'discount/time-reduction percent; per-effect research',
                     'NEEDS_SEMANTIC_RESEARCH')
        return S('eras', 'golden/dark-age dedication bonus magnitude',
                 'STRONG_CANDIDATE')
    # R23: tech/civic unlock magnitudes
    if t in ('CivicModifiers', 'TechnologyModifiers'):
        return S('tech_civic',
                 'unlocked bonus magnitude (costs/prereqs are direct '
                 'fields, not modifiers)',
                 'STRONG_CANDIDATE')
    # R24: project rewards
    if t == 'ProjectCompletionModifiers':
        return S('projects', 'project-completion reward magnitude',
                 'STRONG_CANDIDATE')
    # R25: goody-hut rewards
    if t == 'GoodyHutSubTypes':
        return S('goody_huts', 'goody-hut reward quantity',
                 'STRONG_CANDIDATE')
    # R26: great-person action/birth magnitudes
    if t in ('GreatPersonIndividualActionModifiers',
             'GreatPersonIndividualBirthModifiers'):
        return S('great_people', 'great-person action/birth magnitude',
                 'STRONG_CANDIDATE')
    # R27: promotion/ability combat + yield magnitudes
    if t in ('UnitPromotionModifiers', 'UnitAbilityModifiers'):
        return S('system:' + t.lower(),
                 'promotion/ability bonus magnitude',
                 'STRONG_CANDIDATE')
    # R28: trait/policy/government remainder on merit
    if t in ('TraitModifiers', 'PolicyModifiers', 'GovernmentModifiers'):
        return S('system:' + t.lower(),
                 'unaudited trait/policy/government bonus magnitude; '
                 'needs per-effect certification at integration',
                 'STRONG_CANDIDATE')
    # R28b: governor promotion remainder (identity pressure, envoy grants)
    if t == 'GovernorPromotionModifiers':
        if 'IDENTITY_PRESSURE' in eff:
            if 'FOREIGN' in mid or 'ForeignCities' in str(
                    p.get('argument')):
                return S('governors_remaining',
                         'loyalty pressure exerted on FOREIGN cities '
                         '(another player)',
                         'GLOBAL_OR_CROSS_PLAYER_LEAKAGE')
            return S('governors_remaining',
                     'domestic loyalty-pressure magnitude; loyalty-scope '
                     'precedent must be reviewed at integration',
                     'STRONG_CANDIDATE')
        if 'TOKENS_GRANTED' in eff:
            return S('governors_remaining',
                     'whole envoy grants from a promotion',
                     'CANDIDATE_COUNT_LIKE')
        return S('governors_remaining',
                 'unaudited governor-promotion magnitude',
                 'STRONG_CANDIDATE')
    # R28c: emergency participant rewards (TARGET effects already
    # returned GLOBAL above; victory/weariness/heal handled above)
    if t in ('EmergencyRewards', 'EmergencyBuffs'):
        return S('emergencies',
                 'participant-scoped temporary competition bonus',
                 'STRONG_CANDIDATE')
    # R28d: natural-wonder magnitudes in the global table
    if t == 'GameModifiers':
        return S('natural_game',
                 'natural-wonder bonus magnitude (plot yields, GPP, '
                 'amenity, production)',
                 'STRONG_CANDIDATE')
    # R28e: world-congress favor rewards are owner-scoped magnitudes
    if t == 'ResolutionEffects' and 'FAVOR' in eff:
        return S('world_congress',
                 'favor reward magnitude for a resolution action',
                 'STRONG_CANDIDATE')
    if t in ('GameModifiers', 'ResolutionEffects', 'EmergencyRewards',
             'EmergencyBuffs'):
        return S('system:' + t.lower(),
                 'global/cross-player or shared-scope magnitude; owner '
                 'boundary must be proven at integration',
                 'GLOBAL_OR_CROSS_PLAYER_LEAKAGE')
    return S('unclassified', 'no rule matched; manual review required',
             'NEEDS_SEMANTIC_RESEARCH')


results = []
rule_hits = Counter()
for p in pairs:
    disp, sys, note = dispose(p)
    results.append({'modifier': p['modifier'], 'argument': p['argument'],
                    'value': p['value'], 'root_table': p['root_table'],
                    'effect': p.get('effect', ''), 'disposition': disp,
                    'system': sys, 'note': note})
    rule_hits[disp] += 1

print('uncovered dispositions:')
for k, n in rule_hits.most_common():
    print(f'  {n:5d} {k}')
uncl = [r for r in results if r['system'] == 'unclassified']
print('unclassified:', len(uncl))
for r in uncl[:40]:
    print('  ', r['root_table'], r['effect'], r['argument'], r['value'],
          r['modifier'])
json.dump(results, open(os.path.join(OUT, 'dispositioned.json'), 'w'),
          indent=1)
