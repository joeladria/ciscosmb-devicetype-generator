#!/usr/bin/env python3

import csv
import re
import os

try:
    import yaml
except ImportError:
    print("Please install PyYAML (e.g., pip install pyyaml).")
    raise SystemExit

class IndentDumper(yaml.Dumper):
    def increase_indent(self, flow=False, indentless=False):
        return super(IndentDumper, self).increase_indent(flow, False)

def slugify(s):
    """
    Convert a string to a slug safe for filenames and YAML 'slug' fields:
      - Lowercase
      - Replace non-alphanumeric characters with '-'
      - Collapse multiple dashes
      - Strip leading/trailing dashes
    """
    s = s.lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    s = re.sub(r'-+', '-', s)
    return s.strip('-')

def create_interfaces(row):
    """
    Build a list of interface definitions from the counts in the CSV row,
    using different naming conventions depending on whether 'Stacking' is true or false.
    """

    # Determine if stacking is enabled
    stacking_str = row.get('Stacking', '').strip().lower()
    is_stacking = (stacking_str == 'true')

    # If stacking, use e.g. "GigabitEthernet1/0/#"; if not, just "GigabitEthernet#".
    if is_stacking:
        base_name_1g = "GigabitEthernet1/0/"
        base_name_10g = "TenGigabitEthernet1/0/"
    else:
        base_name_1g = "GigabitEthernet"
        base_name_10g = "TenGigabitEthernet"

    interfaces = []
    int_index_1g = 1   # For 1G (and multi-gig) ports
    int_index_10g = 1  # For 10G ports

    # A simple PoE detection: if the Model has 'P-' or 'FP-' in its name, assume PoE.
    model_name = row['Model'].upper()
    is_poe = ('P-' in model_name or 'FP-' in model_name)

    # 1) GigabitEthernet Copper
    num_gi_copper = int(row['GigabitEthernet Copper'])
    for _ in range(num_gi_copper):
        iface = {
            'name': f"{base_name_1g}{int_index_1g}",
            'type': '1000base-t',
            'enabled': True
        }
        if is_poe:
            iface['poe_mode'] = 'pse'
            iface['poe_type'] = 'type2-ieee802.3at'
        interfaces.append(iface)
        int_index_1g += 1

    #
    # 2) GigabitEthernet SFP (dedicated 1G fiber ports)
    #
    num_gi_sfp = int(row['GigabitEthernet SFP'])
    for _ in range(num_gi_sfp):
        iface = {
            'name': f"{base_name_1g}{int_index_1g}",
            'type': '1000base-x-sfp',
            'enabled': True
        }
        interfaces.append(iface)
        int_index_1g += 1

    #
    # 3) GigabitEthernet Combo (RJ-45/SFP 1G combo ports)
    #
    num_gi_combo = int(row['GigabitEthernet Combo'])
    for _ in range(num_gi_combo):
        iface = {
            'name': f"{base_name_1g}{int_index_1g}",
            # Custom type to indicate 1G copper/SFP combo in one port:
            'type': '1000base-x-sfp',
            'description': 'SFP/RJ45 Combo',
            'enabled': True
        }
        interfaces.append(iface)
        int_index_1g += 1

    #
    # 4) TwoGigabitEthernet (2.5G, etc.) - multi-gig
    #
    num_two_gi = int(row['TwoGigabitEthernet'])
    for _ in range(num_two_gi):
        # We'll name them as part of the same 1G numbering, but with type 2.5gbase-t
        iface = {
            'name': f"{base_name_1g}{int_index_1g}",
            'type': '2.5gbase-t',
            'enabled': True
        }
        interfaces.append(iface)
        int_index_1g += 1

    #
    # 5) TenGigabitEthernet Copper
    #
    num_ten_gi_copper = int(row['TenGigabitEthernet Copper'])
    for _ in range(num_ten_gi_copper):
        iface = {
            'name': f"{base_name_10g}{int_index_10g}",
            'type': '10gbase-t',
            'enabled': True
        }
        interfaces.append(iface)
        int_index_10g += 1

    #
    # 6) TenGigabitEthernet SFP+
    #
    num_ten_gi_sfp = int(row['TenGigabitEthernet SFP+'])
    for _ in range(num_ten_gi_sfp):
        iface = {
            'name': f"{base_name_10g}{int_index_10g}",
            'type': '10gbase-x-sfpp',
            'enabled': True
        }
        interfaces.append(iface)
        int_index_10g += 1

    #
    # 7) TenGigabitEthernet Combo (10G copper/SFP+ combo)
    #
    num_ten_gi_combo = int(row['TenGigabitEthernet Combo'])
    for _ in range(num_ten_gi_combo):
        iface = {
            'name': f"{base_name_10g}{int_index_10g}",
            'type': '10gbase-x-sfpp',
            'description': 'SFP+/RJ45 Combo',            
            'enabled': True
        }
        interfaces.append(iface)
        int_index_10g += 1

    #
    # 8) OOB interface (if any)
    #
    if row['OOB'] and row['OOB'].isdigit() and int(row['OOB']) > 0:
        iface = {
            'name': 'OOB',
            'type': '1000base-t',
            'enabled': True,
            'mgmt_only': True
        }
        interfaces.append(iface)

    #
    # 9) Add a default VLAN interface for management (like Vlan1).
    #
    interfaces.append({
        'name': 'Vlan1',
        'type': 'virtual',
        'enabled': True,
        'mgmt_only': False
    })

    return interfaces

def create_console_ports(row):
    """
    Build a list of console port definitions from con0, con1, con2 columns if they are non-empty.
    """
    console_ports = []
    for c in ['con0', 'con1', 'con2']:
        ctype = row.get(c, '').strip()
        if ctype:
            console_ports.append({
                'name': c,
                'type': ctype
            })
    return console_ports

def main(csv_filename='models.csv'):
    with open(csv_filename, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            model = row['Model']
            part_number = model
            # Build the slug from the model name
            device_slug = f"cisco-{slugify(model)}"

            filename = model.upper()

            # this is the convention used in other cisco catalyst models on device type library for the name only
            model = model.replace("C1300", "Catalyst 1300")

            weight_lbs = float(row['Weight (pounds)'])

            # Draw is in watts
            max_draw = int(round(float(row['Draw'])))

            # Build the device dictionary
            device_dict = {
                'manufacturer': 'Cisco',
                'model': model,
                'slug': device_slug,
                'part_number': part_number,
                'u_height': 1.0,
                'is_full_depth': False,
                'front_image': False,
                'rear_image': False,
                'comments': '[Catalyst 1300 Datasheet](https://www.cisco.com/c/en/us/products/collateral/switches/catalyst-1300-series-switches/nb-06-cat1300-ser-data-sheet-cte-en.html)',
                'weight': weight_lbs,
                'weight_unit': 'lb',
                'interfaces': create_interfaces(row),
                'console-ports': create_console_ports(row),
                'power-ports': [
                    {
                        'name': 'PSU0',
                        'type': row['psu0'],
                        'maximum_draw': max_draw
                    }
                ],
            }

            # Check for front and rear images named using the device slug
            front_path = os.path.join("elevation-images", f"{device_slug.lower()}.front.png")
            rear_path  = os.path.join("elevation-images", f"{device_slug.lower()}.rear.png")

            front_exists = os.path.isfile(front_path)
            rear_exists = os.path.isfile(rear_path)

            if front_exists:
                device_dict['front_image'] = True
            if rear_exists:
                device_dict['rear_image'] = True

            # Dump to YAML
            yaml_string = yaml.dump(device_dict, sort_keys=False, Dumper=IndentDumper, allow_unicode=True)

            out_filename = "Cisco/" + filename + f".yaml"
            with open(out_filename, 'w', encoding='utf-8') as out_f:
                out_f.write("---\n")
                out_f.write(yaml_string)

            print(f"Generated {out_filename}")

if __name__ == "__main__":
    main()
