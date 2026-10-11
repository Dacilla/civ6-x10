"""Phase 8A.1: definition-level projection + mode numeric split + figures.

Reads support_frontier.yml (root occurrences) + modes.json triples.
Appends: definition_projection, cross_root_duplicates, per-mode numeric
splits, verdict meanings, roadmap_figures. Writes
spike/8a-frontier/generated_tables.md (verbatim-tested into
docs/SUPPORT_FRONTIER.md).
"""
import json
import os
import sys
from collections import Counter, defaultdict

REPO = r'C:\Users\alex\Desktop\Code\civ6-x10'
OUT = os.path.join(REPO, 'spike', '8a-frontier')
sys.path.insert(0, REPO)
import yaml  # noqa: E402
from civ6x10.bridge import collect_registry_rows  # noqa: E402
from civ6x10.production import build_production_registry  # noqa: E402

YML = os.path.join(REPO, 'civ6x10', 'rules', 'support_frontier.yml')
doc = yaml.safe_load(open(YML, encoding='utf-8'))

# ---- collect root occurrences ----
occ = []  # (modifier, argument, root, disposition, system, value, effect)
for r in doc['modifier_roots']:
    for p in r['pairs']:
        occ.append((p['modifier'], p['argument'], r['table'],
                    p['disposition'], p['system'], p.get('value', ''),
                    p.get('effect', '')))
print('root occurrences:', len(occ))

by_def = defaultdict(list)
for o in occ:
    by_def[(o[0], o[1])].append(o)

RESTRICTIVE = ['EXISTING_AUDIT_EXCLUDED', 'GLOBAL_OR_CROSS_PLAYER_LEAKAGE',
               'NO_MEANINGFUL_MULTIPLIER_TARGET', 'STRUCTURAL_OR_FILTER',
               'COST_OR_PRICE', 'TIMER_OR_DURATION', 'BASE_STAT_NOT_BONUS',
               'MODE_SYSTEM_MECHANIC']


def mod_of_system(system, table):
    s = system or ''
    if s.startswith('production:'):
        return 'production'
    if s.startswith('audit:'):
        return 'audit:' + table.lower()
    if s.startswith('system:'):
        return s[7:]
    return s


projection = []
for (mid, arg), rows in sorted(by_def.items()):
    roots = sorted({r[2] for r in rows})
    disps = sorted({r[3] for r in rows})
    systems = sorted({r[4] for r in rows})
    values = sorted({str(r[5]) for r in rows})
    modules = sorted({mod_of_system(r[4], r[2]) for r in rows})
    agree = len(disps) == 1
    shared = len(roots) > 1
    if agree:
        final, why = disps[0], 'all roots agree'
    elif 'ALREADY_SUPPORTED' in disps:
        final = 'ALREADY_SUPPORTED'
        why = ('in production registry; also reachable from ' +
               ','.join(r for r in roots) + ' (shared definition, '
               'existing all-owners semantics apply)')
    elif 'EXISTING_AUDIT_EXCLUDED' in disps:
        final = 'EXISTING_AUDIT_EXCLUDED'
        why = 'at least one root carries a recorded prior exclusion; ' \
              'exclusion wins over candidacy'
    elif 'GLOBAL_OR_CROSS_PLAYER_LEAKAGE' in disps:
        final = 'GLOBAL_OR_CROSS_PLAYER_LEAKAGE'
        why = 'at least one root is cross-player/global in scope'
    elif 'NO_MEANINGFUL_MULTIPLIER_TARGET' in disps:
        final = 'NO_MEANINGFUL_MULTIPLIER_TARGET'
        why = 'at least one root finds no meaningful target'
    else:
        rest = [d for d in RESTRICTIVE if d in disps]
        if rest:
            final = rest[0]
            why = 'restrictive root disposition wins: ' + rest[0]
        elif 'NEEDS_PRODUCT_DECISION' in disps:
            final = 'NEEDS_PRODUCT_DECISION'
            why = ('conflicting roots (e.g. actionable in one root, '
                   'unresolved in another); fail closed to an explicit '
                   'product decision')
        elif 'NEEDS_SEMANTIC_RESEARCH' in disps:
            final = 'NEEDS_SEMANTIC_RESEARCH'
            why = 'conflicting roots; research wins over candidacy'
        else:
            final = 'NEEDS_PRODUCT_DECISION'
            why = 'actionable-path conflict (e.g. STRONG vs COUNT_LIKE); ' \
                  'transform path needs an integration decision'
    projection.append({
        'modifier': mid, 'argument': arg, 'roots': roots,
        'systems': systems, 'values': values, 'dispositions': disps,
        'modules': modules, 'roots_agree': agree, 'shared': shared,
        'final_disposition': final, 'rationale': why,
    })

print('unique definitions:', len(projection))
multi = [p for p in projection if p['shared']]
print('multi-root definitions:', len(multi))
conf = [p for p in multi if not p['roots_agree']]
print('conflicting definitions:', len(conf))
for p in conf:
    print('  CONFLICT', p['modifier'], p['argument'], p['dispositions'],
          '->', p['final_disposition'])

# ---- cross-root duplicate inventory (uncovered pairs only) ----
dupes = []
for p in multi:
    uncovered_roots = []
    for r in doc['modifier_roots']:
        for q in r['pairs']:
            if q['modifier'] == p['modifier'] and \
                    q['argument'] == p['argument'] and \
                    q['disposition'] != 'ALREADY_SUPPORTED':
                uncovered_roots.append((r['table'], q['disposition'],
                                        q['system']))
    if not uncovered_roots:
        continue
    tables = sorted({t for t, _d, _s in uncovered_roots})
    disps = sorted({d for _t, d, _s in uncovered_roots})
    mods = sorted({mod_of_system(s, t) for t, _d, s in uncovered_roots})
    dupes.append({'modifier': p['modifier'], 'argument': p['argument'],
                  'roots': tables, 'dispositions': disps,
                  'same_disposition': len(disps) == 1,
                  'modules': mods,
                  'cross_module': len(mods) > 1,
                  'final_disposition': p['final_disposition'],
                  'all_owner_semantics': 'shared definition: future '
                  'all-owners-enabled semantics required if actioned'})
dupes.sort(key=lambda x: (x['modifier'], x['argument']))
print('cross-root uncovered duplicates:', len(dupes))
for d in dupes:
    print('  ', d['modifier'], d['argument'], d['roots'], d['dispositions'],
          '->', d['final_disposition'])

# ---- mode numeric split (heuristic: Amount/Delta/percent-family args
# are numeric-scalar magnitudes; everything else is structural/selector.
# Overlay triples carry no values, so candidate counts stay PENDING.) ----
NUMERIC_ARGS = {'Amount', 'Delta', 'Percent', 'Multiplier', 'ScalingFactor',
                'ReductionPercent', 'SpreadMultiplier',
                'TechEnabledSpreadMultiplier', 'UnitProductionPercent',
                'BuildingProductionPercent', 'UnitCostPercent',
                'PercentDefeatedStrength'}
modes_doc = json.load(open(os.path.join(OUT, 'modes.json')))
CANON = {'GAMEMODE_APOCALYPSE': 'apocalypse',
         'GAMEMODE_BARBARIAN_CLANS': 'barbarian_clans',
         'GAMEMODE_DRAMATICAGES': 'dramatic_ages',
         'GAMEMODE_HEROES': 'heroes_legends',
         'GAMEMODE_MONOPOLIES': 'monopolies_corporations',
         'GAMEMODE_SECRETSOCIETIES': 'secret_societies',
         'GAMEMODE_TOWERDEFENSE': 'zombie_defense',
         'GAMEMODE_TREE_RANDOMIZER': 'tech_civic_shuffle'}
entries, _rep = build_production_registry(collect_registry_rows(REPO))
PRODSET = {(e['modifier_id'], e['argument']) for e in entries}
mode_splits = {}
for m in modes_doc['modes']:
    triples = m['content_inventory'].get('modifier_triples', [])
    vals = [(t[1], t[2]) for t in triples
            if len(t) >= 3 and t[1] and t[2]]
    uniq = sorted(set(vals))
    num = sorted([p for p in uniq if p[1] in NUMERIC_ARGS])
    sel = sorted([p for p in uniq if p[1] not in NUMERIC_ARGS])
    in_prod = sorted([list(p) for p in uniq if p in PRODSET])
    mode_splits[CANON[m['mode_id']]] = {
        'total_triples': len(triples), 'unique_pairs': len(uniq),
        'numeric_scalar_pairs': len(num),
        'structural_selector_pairs': len(sel),
        'in_registry': len(in_prod),
        'mode_only': len(uniq) - len(in_prod)}

for k, v in mode_splits.items():
    print(k, v)

# apply splits + verdict meanings to the doc's game_modes
MEANING = ('mode-level STRONG_CANDIDATE means this mode is worth a '
           'dedicated Phase-8 audit; overlay pair counts are discovery '
           'rows, not production candidates. Candidate counts per mode '
           'are UNKNOWN/PENDING until that audit classifies every '
           'numeric overlay pair.')
for g in doc['game_modes']:
    s = mode_splits[g['id']]
    g['total_triples'] = s['total_triples']
    g['unique_pairs'] = s['unique_pairs']
    g['numeric_scalar_pairs'] = s['numeric_scalar_pairs']
    g['structural_selector_pairs'] = s['structural_selector_pairs']
    g['candidate_status'] = 'PENDING'
    g['verdict_meaning'] = MEANING
    if g['id'] == 'tech_civic_shuffle':
        g['candidate_status'] = 'NONE_NO_TARGET'
        g['verdict_meaning'] = ('NO_MEANINGFUL_MULTIPLIER_TARGET: the '
                                'mode contains no bonus magnitudes.')

doc['definition_projection'] = projection
doc['cross_root_duplicates'] = dupes
doc['mode_numeric_method'] = ('overlay triples carry no values; '
    'numeric-scalar vs structural split is by argument-name heuristic '
    '(Amount/Delta/percent-family = numeric); per-mode candidate counts '
    'are PENDING a dedicated audit')

# ---- roadmap figures ----
fin = Counter(p['final_disposition'] for p in projection)
actionable = sorted([[p['modifier'], p['argument']] for p in projection
                     if p['final_disposition'] in ('STRONG_CANDIDATE',
                                                   'CANDIDATE_COUNT_LIKE')])
doc['roadmap_figures'] = {
    'units': 'see units_* keys; never mix units in one total',
    'units_root_occurrences': 'one row per (root table, ModifierId, '
                              'argument); cross-root pairs counted per root',
    'units_unique_definitions': 'one row per (ModifierId, argument) after '
                                'cross-root deduplication',
    'units_proposed_production': 'unique definitions actionable only '
        'after shared-root conflicts resolve (fail closed)',
    'root_occurrence_totals': dict(Counter(
        q['disposition'] for r in doc['modifier_roots'] for q in r['pairs'])),
    'unique_definition_totals': dict(fin),
    'actionable_definitions': len(actionable),
    'coverage_denominator': '1010 production pairs',
    'coverage_numerator': 'actionable unique definitions',
    'mode_note': 'mode overlay pair counts are discovery rows, not '
                 'candidate counts; mode candidacy is PENDING',
}

with open(YML, 'w', encoding='utf-8', newline='\n') as fh:
    yaml.safe_dump(doc, fh, sort_keys=False, allow_unicode=True)
print('wrote', YML)
print('final totals:', dict(fin))
print('actionable unique definitions:', len(actionable))
