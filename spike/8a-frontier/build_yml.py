"""Phase 8A: build civ6x10/rules/support_frontier.yml (disposable script).

Assembles the committed discovery artifact from scanner outputs +
disposition engine results. Run from repo root.
"""
import hashlib
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

disp = json.load(open(os.path.join(OUT, 'dispositioned.json')))
inreg = json.load(open(os.path.join(OUT, 'in_registry_pairs.json')))
modes_doc = json.load(open(os.path.join(OUT, 'modes.json')))
direct_doc = json.load(open(os.path.join(OUT, 'direct_tables.json')))
db_doc = json.load(open(os.path.join(OUT, 'db_scan.json')))

entries, _ = build_production_registry(collect_registry_rows(REPO))
PROD = {(e['modifier_id'], e['argument']) for e in entries}
assert len(PROD) == 1010

DLL = '3b6dc3d26c3eab51fa5be4272252b926deaf10b6d4e7bedb094c2c6c8272ab14'

db_path = os.path.join(REPO, 'data', 'local',
                       'DebugGameplay_official.sqlite')
h = hashlib.sha256()
with open(db_path, 'rb') as fh:
    for chunk in iter(lambda: fh.read(1 << 20), b''):
        h.update(chunk)

# ---- modifier roots ----
by_table = {}
for p in disp:
    by_table.setdefault(p['root_table'], []).append(p)
inreg_by_table = {}
for t, rows in inreg.items():
    inreg_by_table[t] = rows

TABLE_ROLES = {
    'TraitModifiers': 'association: civilization/leader traits',
    'PolicyModifiers': 'association: policy cards',
    'GovernmentModifiers': 'association: governments',
    'GovernorPromotionModifiers': 'association: governor promotions',
    'BeliefModifiers': 'association: religious beliefs',
    'BuildingModifiers': 'association: buildings',
    'DistrictModifiers': 'association: districts',
    'ImprovementModifiers': 'association: improvements',
    'CivicModifiers': 'association: civics',
    'TechnologyModifiers': 'association: technologies',
    'UnitPromotionModifiers': 'association: unit promotions',
    'UnitAbilityModifiers': 'association: unit abilities',
    'GreatPersonIndividualActionModifiers':
        'association: great-person actions',
    'GreatPersonIndividualBirthModifiers':
        'association: great-person birth effects',
    'CommemorationModifiers': 'association: era dedications/commemorations',
    'AllianceEffects': 'association: alliance levels',
    'EmergencyBuffs': 'association: emergency participant buffs',
    'EmergencyRewards': 'association: emergency/competition rewards',
    'ResolutionEffects': 'association: world-congress resolutions',
    'ProjectCompletionModifiers': 'association: project completion',
    'GameModifiers': 'association: global/game effects',
    'GoodyHutSubTypes': 'association: goody-hut rewards',
    'GreatWorkModifiers': 'association: great works (empty in snapshot)',
    'ComplimentModifiers': 'association: diplomacy compliments '
                           '(empty in snapshot)',
    'GovernorModifiers': 'association: governors (empty in snapshot)',
}
EMPTY_TABLES = ['GreatWorkModifiers', 'ComplimentModifiers',
                'GovernorModifiers']

roots = []
for t in sorted(set(list(by_table) + EMPTY_TABLES)):
    pairs = []
    for p in by_table.get(t, []):
        pairs.append({'modifier': p['modifier'], 'argument': p['argument'],
                      'value': p['value'], 'effect': p['effect'],
                      'root_table': t, 'disposition': p['disposition'],
                      'system': p['system'], 'note': p['note']})
    for r in inreg_by_table.get(t, []):
        pairs.append({'modifier': r['modifier'], 'argument': r['argument'],
                      'value': r['value'], 'effect': r['effect'],
                      'root_table': t,
                      'disposition': 'ALREADY_SUPPORTED',
                      'system': 'production:' + t.lower(),
                      'note': 'in production registry'})
    pairs.sort(key=lambda x: (x['modifier'], x['argument']))
    n_in = sum(1 for x in pairs
               if x['disposition'] == 'ALREADY_SUPPORTED')
    roots.append({'table': t, 'role': TABLE_ROLES[t],
                  'numeric_pairs': len(pairs), 'in_registry': n_in,
                  'uncovered': len(pairs) - n_in, 'pairs': pairs})

total_pairs = sum(r['numeric_pairs'] for r in roots)
disp_totals = dict(Counter(x['disposition'] for r in roots for x in
                           r['pairs']))
assert sum(disp_totals.values()) == total_pairs, (
    sum(disp_totals.values()), total_pairs)

# ---- game modes ----
CANON = {'GAMEMODE_APOCALYPSE': 'apocalypse',
         'GAMEMODE_BARBARIAN_CLANS': 'barbarian_clans',
         'GAMEMODE_DRAMATICAGES': 'dramatic_ages',
         'GAMEMODE_HEROES': 'heroes_legends',
         'GAMEMODE_MONOPOLIES': 'monopolies_corporations',
         'GAMEMODE_SECRETSOCIETIES': 'secret_societies',
         'GAMEMODE_TOWERDEFENSE': 'zombie_defense',
         'GAMEMODE_TREE_RANDOMIZER': 'tech_civic_shuffle'}
MODE_VERDICT = {
    'apocalypse': ('NEEDS_PRODUCT_DECISION',
                   'Soothsayer charges and Appease-the-Gods rewards are '
                   'clean magnitudes, but disaster/climate globals must '
                   'never scale with the multiplier; needs an explicit '
                   'bonus-vs-disaster-system product boundary.'),
    'barbarian_clans': ('STRONG_CANDIDATE',
                        'Raid/disperse/hire/ransom reward magnitudes are '
                        'clean player bonuses; prices, progress thresholds '
                        'and immunity timers stay out by rule.'),
    'dramatic_ages': ('STRONG_CANDIDATE',
                      '8 overlay pairs already reachable via the policies '
                      'module; the remaining 141 overlay pairs are golden/'
                      'dark-age card and loyalty/era-score magnitudes, '
                      'partly missed because the overlay was absent from '
                      'the baseline production audit.'),
    'heroes_legends': ('NEEDS_PRODUCT_DECISION',
                       'Hero ability magnitudes are strong, but Hero base '
                       'combat-stat progression, charges, recall costs and '
                       'lifespans must be separated first; base stats must '
                       'not be multiplied implicitly.'),
    'monopolies_corporations': ('STRONG_CANDIDATE',
                                'Industry/Corporation bonuses, product '
                                'yields, monopoly tourism and project '
                                'bonuses form the highest-density clean '
                                'magnitude set of any mode.'),
    'secret_societies': ('STRONG_CANDIDATE',
                         '22 overlay pairs already in the registry via the '
                         'governors module; remaining society units, '
                         'buildings, improvements, city projects and '
                         'resource effects are the honest remainder.'),
    'zombie_defense': ('NEEDS_PRODUCT_DECISION',
                       'Player-benefit magnitudes (traps, barricades, '
                       'damage, control duration) cannot be separated from '
                       'zombie-side scaling without an explicit '
                       'player-vs-enemy product boundary.'),
    'tech_civic_shuffle': ('NO_MEANINGFUL_MULTIPLIER_TARGET',
                           'Randomized prerequisites, placement, costs and '
                           'visibility are not bonus magnitudes.'),
}
mode_entries = []
for m in modes_doc['modes']:
    mid = m['mode_id']
    cid = CANON[mid]
    triples = m['content_inventory'].get('modifier_triples', [])
    skipped = sum(1 for t in triples
                  if len(t) < 3 or not t[1] or not t[2])
    mpairs = sorted({(t[1], t[2]) for t in triples
                     if len(t) >= 3 and t[1] and t[2]})
    in_prod = sorted([list(p) for p in mpairs if p in PROD])
    only = sorted([mm for (mm, _a) in mpairs if (mm, _a) not in PROD])
    setup = m.get('setup_parameter', [])
    config_id = ''
    for row in setup:
        if isinstance(row, dict) and row.get('table') == 'Parameters':
            config_id = row.get('row', {}).get('ConfigurationId', '')
    overlays = [{'path': f['dlc_dir'] + '/' + f['relpath'],
                 'sha256': f.get('sha256', ''),
                 'criterion': str(f.get('criterion', ''))[:200],
                 'missing': bool(f.get('missing', False))}
                for f in m.get('overlay_files', [])]
    verdict, why = MODE_VERDICT[cid]
    mode_entries.append({
        'id': cid, 'mode_id': mid,
        'name': m.get('friendly_name', ''), 'configuration_id': config_id,
        'dlc': m.get('owning_dlc_dir', ''),
        'requirements': m.get('requirements', {}),
        'overlay_files': overlays,
        'overlay_modifier_pairs': len(mpairs),
        'overlay_pairs': [list(p) for p in mpairs],
        'overlay_triples_skipped_null': skipped,
        'in_registry': len(in_prod),
        'mode_only_modifiers': only,
        'disposition': verdict, 'verdict_note': why,
    })
mode_entries.sort(key=lambda x: x['id'])

# ---- direct tables ----
ROLE_DISP = {'bonus_magnitude': 'NEEDS_PRODUCT_DECISION',
             'base_stat': 'BASE_STAT_NOT_BONUS', 'cost': 'COST_OR_PRICE',
             'duration_timer': 'TIMER_OR_DURATION',
             'chance': 'NEEDS_PRODUCT_DECISION', 'cap': 'NEEDS_PRODUCT_DECISION',
             'requirement_filter': 'STRUCTURAL_OR_FILTER',
             'selector': 'STRUCTURAL_OR_FILTER',
             'ai_weight': 'STRUCTURAL_OR_FILTER',
             'progression_threshold': 'STRUCTURAL_OR_FILTER',
             'global_intensity': 'GLOBAL_OR_CROSS_PLAYER_LEAKAGE',
             'structural_internal': 'STRUCTURAL_OR_FILTER'}


def direct_system(table):
    t = table.upper()
    if 'GLOBAL' in t or 'CLIMATE' in t or 'DISASTER' in t:
        return 'global_systems'
    if 'YIELD' in t or 'ADJACENCY' in t or 'BUILDING' in t or \
            'DISTRICT' in t or 'IMPROVEMENT' in t:
        return 'infrastructure_direct'
    if 'SPEED' in t or 'ERA' in t or 'GAME_' in t:
        return 'game_pace'
    if 'GOODY' in t or 'RANDOMEVENT' in t or 'TRIBE' in t or 'BARBARIAN' in t:
        return 'goody_events'
    if 'UNIT' in t or 'PROMOTION' in t or 'ABILITY' in t:
        return 'units_direct'
    if 'GREAT' in t or 'HERO' in t:
        return 'great_people_direct'
    if 'GOVERN' in t or 'LOYALTY' in t or 'IDENTITY' in t:
        return 'governments_direct'
    if 'FAITH' in t or 'RELIGION' in t or 'BELIEF' in t:
        return 'religion_direct'
    if 'TRADE' in t or 'ROUTE' in t:
        return 'trade_direct'
    if 'TOURISM' in t or 'CULTURE' in t:
        return 'culture_direct'
    if 'RESOURCE' in t or 'CORPORATION' in t or 'INDUSTR' in t or \
            'PRODUCT' in t:
        return 'corporations_direct'
    if 'COST' in t or 'PRICE' in t:
        return 'costs_direct'
    return 'direct_other'


direct_entries = []
for f in direct_doc.get('fields', []):
    table = f.get('table', '')
    role = f.get('role', 'structural_internal')
    disp = ROLE_DISP.get(role, 'STRUCTURAL_OR_FILTER')
    note = 'direct numeric field: ' + role
    if table.upper() == 'GLOBALPARAMETERS' and \
            role == 'bonus_magnitude':
        disp = 'GLOBAL_OR_CROSS_PLAYER_LEAKAGE'
        note = 'global tunable magnitude; shared-system scope'
    if role == 'bonus_magnitude':
        note += '; direct-yield scope-B question applies'
    if role == 'chance':
        note += '; scaling randomness is a product call'
    if role == 'cap':
        note += '; limit parameter, scaling is a product call'
    direct_entries.append({
        'table': table, 'field': f.get('field', ''),
        'role': role, 'rows': f.get('rows', 0),
        'value_min': f.get('min', ''),
        'value_max': f.get('max', ''),
        'disposition': disp, 'system': direct_system(table),
        'note': note})
direct_entries.sort(key=lambda x: (x['table'], x['field']))

doc = {
    'version': 1,
    'phase': '8A',
    'baseline_db': {'bytes': db_doc['baseline_db']['bytes'],
                    'sha256': db_doc['baseline_db']['sha256'],
                    'tables': db_doc['baseline_db']['tables']},
    'production': {'entries': 1010, 'unique': 1006, 'shared': 25,
                   'unconditional': 788, 'count_like': 222,
                   'ce_commit': '0655190', 'dll_sha256': DLL},
    'taxonomy': ['ALREADY_SUPPORTED', 'EXISTING_AUDIT_EXCLUDED',
                 'STRONG_CANDIDATE', 'CANDIDATE_COUNT_LIKE',
                 'CANDIDATE_NEEDS_NEW_TRANSFORM',
                 'NEEDS_SEMANTIC_RESEARCH', 'NEEDS_PRODUCT_DECISION',
                 'GLOBAL_OR_CROSS_PLAYER_LEAKAGE', 'STRUCTURAL_OR_FILTER',
                 'COST_OR_PRICE', 'TIMER_OR_DURATION',
                 'BASE_STAT_NOT_BONUS', 'MODE_SYSTEM_MECHANIC',
                 'NO_MEANINGFUL_MULTIPLIER_TARGET'],
    'discovery': {
        'method': 'schema-derived ModifierId-column scan (case-insensitive '
                  'exact match) over a read-only temp copy of the '
                  'baseline DB; nested attached-modifier traversal with '
                  'cycle detection; strict value-float numeric rule '
                  '(no name denylist); independent re-enumeration '
                  'reproduced all scanner counts exactly',
        'modifier_tables_examined': len(roots),
        'total_numeric_pairs': total_pairs,
        'non_root_modifier_columns':
            db_doc.get('non_root_modif_columns', []),
        'beyond_request_method': 'schema-wide INTEGER/REAL field sweep '
            'for gameplay magnitudes outside the supplied category lists, '
            'plus review of every modifier-root table for systems the '
            'prompt did not name',
    },
    'pair_overlap': {
        'production_pairs_total': 1010,
        'production_pairs_found_in_db': 931,
        'production_pairs_missing_explained': [
            {'kind': 'synthetic_bridge_helpers', 'count': 57,
             'note': 'X10_ wonder-direct bridge helpers exist only in the '
                     'generated registry, by design'},
            {'kind': 'mode_overlay_absent_from_snapshot', 'count': 22,
             'note': 'secret-society governor/promotion modifiers from '
                     'mode overlays not present in the no-overlay baseline '
                     'snapshot (Owls/Voidsingers/Hermetic/Vampire)'}],
    },
    'mode_sanity_check': {
        'expected_8': ['apocalypse', 'barbarian_clans', 'dramatic_ages',
                       'heroes_legends', 'monopolies_corporations',
                       'secret_societies', 'tech_civic_shuffle',
                       'zombie_defense'],
        'discovered': [e['id'] for e in mode_entries],
        'discrepancies': 'none in count (8==8); only ID-to-familiar-name '
            'mapping was needed (GAMEMODE_TREE_RANDOMIZER = Tech and '
            'Civic Shuffle, GAMEMODE_TOWERDEFENSE = Zombie Defense); '
            'GAMEMODE_RANDOM is a visibility-gating pseudo-config, not '
            'a mode; GAMEMODE_BARBARIANCLANS (no underscore) is an icon '
            'string only; two overlay files referenced by modinfos are '
            'absent on disk (flagged missing in overlay_files)',
    },
    'game_modes': mode_entries,
    'modifier_roots': roots,
    'direct_tables': direct_entries,
    'beyond_request': db_doc.get('beyond_request', []),
    'disposition_totals': disp_totals,
}

with open(os.path.join(REPO, 'civ6x10', 'rules', 'support_frontier.yml'),
          'w', encoding='utf-8', newline='\n') as fh:
    yaml.safe_dump(doc, fh, sort_keys=False, allow_unicode=True)
print('roots:', len(roots), 'total pairs:', total_pairs)
print('modes:', len(mode_entries), 'direct fields:', len(direct_entries))
print('beyond:', len(doc['beyond_request']))
