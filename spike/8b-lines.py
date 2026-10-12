lines = open('civ6x10/bridge.py', encoding='utf-8').readlines()
for i in range(0, 23):
    print(i + 1, repr(lines[i]))
