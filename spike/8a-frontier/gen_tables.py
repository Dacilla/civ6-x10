"""Phase 8A.1: generate spike/8a-frontier/generated_tables.md from the YAML.

These tables are pasted VERBATIM into docs/SUPPORT_FRONTIER.md; tests
assert verbatim presence, so prose totals always derive from the
artifact. Units are labeled per table; never mix units in one total.
"""
import sys
from collections import Counter, defaultdict

sys.path.insert(0, r'C:\Users\alex\Desktop\Code\civ6-x10')
import yaml

YML = 'C:/Users/alex/Desktop/Code/civ6-x10/civ6x10/rules/support_frontier.yml'
OUT = ('C:/Users/alex/Desktop/Code/civ6-x10/spike/8a-frontier/'
       'generated_tables.md')
doc = yaml.safe_load(open(YML, encoding='utf-8'))
fig = doc['roadmap_figures']

L = []


def emit(s=''):
    L.append(s)


ROOT_ORDER = ['STRONG_CANDIDATE', 'CANDIDATE_COUNT_LIKE',
              'NEEDS_SEMANTIC_RESEARCH', 'NEEDS_PRODUCT_DECISION',
              'GLOBAL_OR_CROSS_PLAYER_LEAKAGE', 'EXISTING_AUDIT_EXCLUDED',
              'STRUCTURAL_OR_FILTER', 'COST_OR_PRICE', 'TIMER_OR_DURATION',
              'BASE_STAT_NOT_BONUS', 'MODE_SYSTEM_MECHANIC',
              'NO_MEANINGFUL_MULTIPLIER_TARGET', 'ALREADY_SUPPORTED']

emit('<!-- GENERATED from civ6x10/rules/support_frontier.yml by '
     'spike/8a-frontier/projection.py; do not hand-edit. '
     'Pasted verbatim into docs/SUPPORT_FRONTIER.md. -->')
emit()
emit('### Table N1 — disposition totals in ROOT_OCCURRENCES '
     '(root table, ModifierId, argument)')
emit()
emit('| disposition | root occurrences |')
emit('|---|---|')
for k in ROOT_ORDER:
    emit(f'| {k} | {fig["root_occurrence_totals"].get(k, 0)} |')
emit(f'| TOTAL | '
     f'{sum(fig["root_occurrence_totals"].values())} |')
emit()
emit('### Table N2 — disposition totals in UNIQUE_DEFINITIONS '
     '(ModifierId, argument, cross-root deduplicated)')
emit()
emit('| disposition | unique definitions |')
emit('|---|---|')
for k in ROOT_ORDER:
    emit(f'| {k} | {fig["unique_definition_totals"].get(k, 0)} |')
emit(f'| TOTAL | {sum(fig["unique_definition_totals"].values())} |')
emit()
emit('### Table N3 — definition-level actionable count '
     '(PROPOSED_PRODUCTION_PAIRS)')
emit()
emit(f'ACTIONABLE_UNIQUE_DEFINITIONS = {fig["actionable_definitions"]}')
COVER_PCT = None
emit(f'COVERAGE_DENOMINATOR = {fig["coverage_denominator"]}')
emit()

# per-system definition-level rollup (final dispositions)
SYS_MOD = {
    'religion_beliefs': 'Religion',
    'great_people': 'Great People',
    'promotions': 'Promotions',
    'abilities': 'Abilities',
    'eras': 'Eras',
    'tech_civic': 'Tech/Civic',
    'projects': 'Projects',
    'goody_huts': 'Tribal Villages',
    'alliances': 'Eras & Diplomacy',
    'emergencies': 'Eras & Diplomacy',
    'world_congress': 'Eras & Diplomacy',
    'infrastructure_building': 'Infrastructure',
    'infrastructure_district': 'Infrastructure',
    'infrastructure_improvement': 'Infrastructure',
    'traits': 'Existing Traits module',
    'policies': 'Existing Policies module',
    'governments': 'Existing Governments module',
    'governors_remaining': 'Existing Governors module',
    'minor_civ_traits': 'Minor City-States',
    'diplomacy_agendas': 'None (never)',
    'diplomacy_allies': 'None (never)',
    'difficulty': 'None (never)',
    'natural_game': 'Wonders module',
    'victory_points': 'None (product call)',
    'wmd': 'None (product call)',
    'research:percent': 'Research pool',
    'research:probability': 'Research pool',
    'research:healing': 'Research pool',
    'research:mitigation': 'Research pool',
    'research:boosts': 'Research pool',
    'research:rates': 'Research pool',
    'global_systems': 'None (global)',
    'none': 'None',
}


def primo(system, table):
    if system in SYS_MOD:
        return SYS_MOD[system]
    if system.startswith('production:'):
        return 'Already supported'
    if system.startswith('audit:'):
        return 'Prior exclusions'
    if system.startswith('system:'):
        t = system[7:]
        base = {'beliefmodifiers': 'Religion',
                'governorpromotionmodifiers': 'Existing Governors module',
                'civicmodifiers': 'Tech/Civic',
                'technologymodifiers': 'Tech/Civic',
                'commemorationmodifiers': 'Eras',
                'emergencybuffs': 'Eras & Diplomacy',
                'emergencyrewards': 'Eras & Diplomacy',
                'resolutioneffects': 'Eras & Diplomacy',
                'gamemodifiers': 'Wonders module',
                'goodyhutsubtypes': 'Tribal Villages',
                'greatpersonindividualactionmodifiers': 'Great People',
                'greatpersonindividualbirthmodifiers': 'Great People',
                'policymodifiers': 'Existing Policies module',
                'traitmodifiers': 'Existing Traits module',
                'unitabilitymodifiers': 'Promotions & Abilities',
                'unitpromotionmodifiers': 'Promotions & Abilities'}.get(t)
        if base:
            return base
    return 'Other:' + system


agg = defaultdict(Counter)
shared_n = 0
for p in doc['definition_projection']:
    ms = sorted({primo(s, '') for s in p['systems']})
    key = ms[0] if len(ms) == 1 else 'Cross-module:' + '+'.join(ms)
    agg[key][p['final_disposition']] += 1
    if p['shared']:
        shared_n += 1

emit('### Table N4 — definition-level dispositions by proposed module '
     '(UNIQUE_DEFINITIONS)')
emit()
emit('| proposed module | unique defs | strong | count-like | research | '
     'product-dec | global | prior-excl | structural+other | supported |')
emit('|---|---|---|---|---|---|---|---|---|---|---|')
for mod in sorted(agg):
    c = agg[mod]
    n = sum(c.values())
    other = (c.get('STRUCTURAL_OR_FILTER', 0) +
             c.get('COST_OR_PRICE', 0) + c.get('TIMER_OR_DURATION', 0) +
             c.get('BASE_STAT_NOT_BONUS', 0) +
             c.get('MODE_SYSTEM_MECHANIC', 0) +
             c.get('NO_MEANINGFUL_MULTIPLIER_TARGET', 0))
    emit(f'| {mod} | {n} | {c.get("STRONG_CANDIDATE", 0)} | '
         f'{c.get("CANDIDATE_COUNT_LIKE", 0)} | '
         f'{c.get("NEEDS_SEMANTIC_RESEARCH", 0)} | '
         f'{c.get("NEEDS_PRODUCT_DECISION", 0)} | '
         f'{c.get("GLOBAL_OR_CROSS_PLAYER_LEAKAGE", 0)} | '
         f'{c.get("EXISTING_AUDIT_EXCLUDED", 0)} | {other} | '
         f'{c.get("ALREADY_SUPPORTED", 0)} |')
emit()
emit(f'SHARED_DEFINITIONS (multi-root) = {shared_n}')
emit()
emit('### Table N5 — per-mode discovery split (DISCOVERY ROWS, not '
     'candidates)')
emit()
emit('| mode | triples | unique pairs | numeric-scalar | '
     'structural/selector | in-registry | mode-only | candidates |')
emit('|---|---|---|---|---|---|---|---|---|')
for g in doc['game_modes']:
    emit(f'| {g["id"]} | {g["total_triples"]} | {g["unique_pairs"]} | '
         f'{g["numeric_scalar_pairs"]} | '
         f'{g["structural_selector_pairs"]} | {g["in_registry"]} | '
         f'{len(g["mode_only_modifiers"])} | {g["candidate_status"]} |')
emit()
emit('Mode-level STRONG_CANDIDATE means the mode is worth a dedicated '
     'Phase-8 audit; overlay pair counts are discovery rows, not '
     'production candidates.')

open(OUT, 'w', encoding='utf-8', newline='\n').write('\n'.join(L) + '\n')
print('wrote', OUT)
