import json

file1 = 'link_test_configs/WEDGE800BACT/optics_link_two.json'
file2 = 'Topology/WEDGE800BACT/optics_link_two.json'

with open(file1, 'r', encoding='utf-8') as f:
    data1 = json.load(f)

with open(file2, 'r', encoding='utf-8') as f:
    data2 = json.load(f)

print('Comparing two optics_link_two.json files:')
print('=' * 70)
print(f'File 1: {file1}')
print(f'File 2: {file2}')
print()

# Check File 1
if 'sw' in data1 and 'ports' in data1['sw']:
    ports1 = data1['sw']['ports']
    print(f'File 1: FBOSS config format with {len(ports1)} ports')
    for p in ports1:
        name = p.get('name')
        if name in ['eth1/17/1', 'eth1/18/1']:
            profile = p.get('profileID')
            print(f'  {name}: profileID = {profile}')
else:
    print('File 1: Other format')
    if 'interfaces' in data1:
        print(f'  Has "interfaces" key')
    if 'pimInfo' in data1:
        print(f'  Has "pimInfo" key')

print()

# Check File 2
if 'sw' in data2 and 'ports' in data2['sw']:
    ports2 = data2['sw']['ports']
    print(f'File 2: FBOSS config format with {len(ports2)} ports')
    for p in ports2:
        name = p.get('name')
        if name in ['eth1/17/1', 'eth1/18/1']:
            profile = p.get('profileID')
            print(f'  {name}: profileID = {profile}')
else:
    print('File 2: Topology format')
    if 'interfaces' in data2:
        ifaces = data2.get('interfaces', {})
        if isinstance(ifaces, dict):
            print(f'  Has "interfaces" dict with {len(ifaces)} entries')
            if 'eth1/17/1' in ifaces:
                info = ifaces['eth1/17/1']
                print(f'  eth1/17/1:', info)
            if 'eth1/18/1' in ifaces:
                info = ifaces['eth1/18/1']
                print(f'  eth1/18/1:', info)
    if 'pimInfo' in data2:
        print(f'  Has "pimInfo" key')
