import io, sys
marker = sys.argv[1]
srcfile = sys.argv[2]
src = io.open(srcfile, encoding='utf-8').read()
assert src.count(marker) == 1, (srcfile, marker)
body = src.split(marker, 1)[1]
with io.open('civ6x10/eight_b.py', 'a', encoding='utf-8', newline='\n') as fh:
    fh.write('\n\n')
    fh.write(body.lstrip('\n'))
print('appended', srcfile)
