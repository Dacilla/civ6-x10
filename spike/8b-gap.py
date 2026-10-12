import csv, re

cov = list(csv.DictReader(open('build/X10ProductionRegistry.inc.conflicts.csv', encoding='utf-8')))
reg_effects = sorted(set(r['effect_type'] for r in cov if r.get('resolution') == 'certified'))
print('certified registry effect types:', len(reg_effects))

rma = open('C:/Program Files (x86)/Steam/steamapps/workshop/content/289070/1312585482/RealModifierAnalysis.lua', encoding='utf-8').read()
rma_effects = set(re.findall(r'EFFECT_[A-Z_]+', rma))
gap = [e for e in reg_effects if e not in rma_effects]
print('gap (in registry, not named in RMA):', len(gap))
for e in gap:
    n = sum(1 for r in cov if r.get('effect_type') == e and r.get('resolution') == 'certified')
    print('  ', e, n)
