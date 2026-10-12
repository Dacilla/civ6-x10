import io
p = 'civ6x10/rules/certified_overrides.yml'
t = io.open(p, encoding='utf-8').read()
assert 'certified_effect_args:' not in t
block = '''
# Curated (effect, argument[, modifier_type]) certification (Phase 8B).
# Positive human evidence for carriers whose floor row is heuristic-only
# (AUTO_PATTERN / NEEDS_REVIEW) or absent entirely (promotion/ability and
# game-mode carriers missing from the clean-DB floor). Same trust class as
# combat_effects. Excluded EffectTypes keep precedence; unlisted tuples
# fall through to the ordinary conflict path. These entries only ever match
# rows the pre-8B gate refused or conflicted on, so existing certified rows
# are unaffected (proven by the unchanged-1010 suite + the 8B growth diff).
certified_effect_args:
  - effect: EFFECT_ADJUST_UNIT_SPY_OPERATION_CHANCE
    argument: Amount
    kind: PROBABILITY
    family: PROBABILITY
    rationale: "mission success chance percents (spy promotions +2);
      repeated-trial compounding, same as all certified probabilities"
  - effect: EFFECT_ADJUST_UNIT_SPY_OPERATION_TIME
    argument: ReductionPercent
    kind: DISCOUNT
    family: DISCOUNT
    rationale: "percent-scale operation-time reduction (25); compound discount"
  - effect: EFFECT_ADJUST_UNIT_SPY_ESTABLISH_TIME
    argument: ReductionPercent
    kind: DISCOUNT
    family: DISCOUNT
    rationale: "percent-scale establish-time reduction (100); compound discount"
  - effect: EFFECT_ADJUST_UNIT_SPY_OFFENSIVE_OPERATION_TIME
    argument: ReductionPercent
    kind: DISCOUNT
    family: DISCOUNT
    rationale: "percent-scale offensive-operation-time reduction (25);
      compound discount"
'''
if not t.endswith('\n'):
    t += '\n'
t += block
io.open(p, 'w', encoding='utf-8', newline='\n').write(t)
print('ok')
