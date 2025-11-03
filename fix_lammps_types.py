#!/usr/bin/env python3
"""
Reorder atom types in LAMMPS data file by atomic number.
This ensures consistent type ordering across different configurations.
Usage: python fix_lammps_types.py input.lmp output.lmp
"""

import sys

# Atomic masses and numbers for common elements
ELEMENT_DATA = {
    'H': (1.008, 1),
    'He': (4.003, 2),
    'C': (12.011, 6),
    'N': (14.007, 7),
    'O': (15.999, 8),
    'Al': (26.982, 13),
    'Ti': (47.867, 22),
    'Cr': (51.996, 24),
    'Fe': (55.845, 26),
    'Ni': (58.693, 28),
    'Cu': (63.546, 29),
    'Mo': (95.95, 42),
    'W': (183.84, 74),
}

def identify_element(mass):
    """Identify element from mass (with tolerance)"""
    mass = float(mass)
    for element, (ref_mass, z) in ELEMENT_DATA.items():
        if abs(mass - ref_mass) < 1.0:  # 1 amu tolerance
            return element
    raise ValueError(f"Unknown mass: {mass}")

def get_atomic_number(element):
    """Get atomic number for element"""
    return ELEMENT_DATA[element][1]

def fix_lammps_types(input_file, output_file):
    with open(input_file, 'r') as f:
        lines = f.readlines()
    
    # Find section boundaries
    masses_start = -1
    atoms_start = -1
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        # Check for exact match or line starting with keyword
        if line_stripped == 'Masses' or (line_stripped.startswith('Masses') and len(line_stripped.split()) == 1):
            masses_start = i
            print(f"Found Masses at line {i}: {repr(line)}")
        elif line_stripped.startswith('Atoms'):
            atoms_start = i
            print(f"Found Atoms at line {i}: {repr(line)}")
            break
    
    if masses_start == -1 or atoms_start == -1:
        print(f"Error: Could not find Masses or Atoms sections")
        print(f"masses_start = {masses_start}, atoms_start = {atoms_start}")
        print(f"\nSearching through file ({len(lines)} lines):")
        for i, line in enumerate(lines[:50]):  # Show first 50 lines
            if 'Mass' in line or 'Atom' in line:
                print(f"  Line {i}: {repr(line)}")
        return
    
    # Parse masses section to identify elements and their current types
    current_type_to_element = {}
    
    print(f"Parsing masses from line {masses_start+1} to {atoms_start}:")
    
    for i in range(masses_start + 1, atoms_start):
        line = lines[i].strip()
        if not line or line.startswith('#'):
            continue
        
        # Parse line: type_id mass # element
        parts = line.split('#')[0].split()
        
        if len(parts) >= 2:
            try:
                type_id = int(parts[0])
                mass = float(parts[1])
                element = identify_element(mass)
                current_type_to_element[type_id] = element
                print(f"  Type {type_id}: {element} (Z={get_atomic_number(element)}, mass={mass})")
            except (ValueError, IndexError) as e:
                print(f"  Warning: Could not parse line {i}: {line} ({e})")
    
    if not current_type_to_element:
        print("Error: No element types found!")
        return
    
    # Create new type ordering based on atomic number
    elements_sorted = sorted(current_type_to_element.items(), 
                            key=lambda x: get_atomic_number(x[1]))
    
    # Create mapping: old_type -> new_type
    type_mapping = {}
    new_type_to_element = {}
    
    for new_type, (old_type, element) in enumerate(elements_sorted, start=1):
        type_mapping[old_type] = new_type
        new_type_to_element[new_type] = element
    
    print(f"\nNew ordering by atomic number:")
    for new_type, element in sorted(new_type_to_element.items()):
        print(f"  Type {new_type}: {element} (Z={get_atomic_number(element)})")
    
    print(f"\nType remapping: {type_mapping}")
    
    # Write output file
    with open(output_file, 'w') as f:
        # Write everything before Masses section
        for i in range(masses_start + 1):
            f.write(lines[i])
        
        # Write blank line after "Masses" header
        f.write('\n')
        
        # Write new Masses section ordered by atomic number
        for new_type in sorted(new_type_to_element.keys()):
            element = new_type_to_element[new_type]
            mass = ELEMENT_DATA[element][0]
            # Use atomsk-style formatting
            f.write(f"            {new_type}   {mass:.8f}             # {element}\n")
        
        # Write blank line after masses
        f.write('\n')
        
        # Write Atoms section header
        f.write(lines[atoms_start])
        
        # Write blank line after "Atoms" header  
        f.write('\n')
        
        # Process atoms with remapped types
        for i in range(atoms_start + 1, len(lines)):
            line = lines[i]
            
            # Skip comments and blank lines
            if not line.strip() or line.strip().startswith('#'):
                continue
            
            # Check if this looks like an atom line
            parts = line.split()
            if len(parts) >= 4:  # atom_id type x y z ...
                try:
                    atom_id = int(parts[0])
                    old_type = int(parts[1])
                    
                    # Remap type
                    if old_type in type_mapping:
                        new_type = type_mapping[old_type]
                        # Format coordinates
                        coords = parts[2:]
                        # Match atomsk's formatting
                        f.write(f"      {atom_id:6d}    {new_type}        {coords[0]:>20}       {coords[1]:>20}       {coords[2]:>20}")
                        # Add any extra columns (charges, etc.)
                        if len(coords) > 3:
                            f.write('       ' + '       '.join(coords[3:]))
                        f.write('\n')
                    else:
                        print(f"Warning: Type {old_type} not in mapping")
                        f.write(line)
                except (ValueError, IndexError) as e:
                    # Not an atom line or parse error
                    pass
    
    print(f"\nSuccessfully reordered: {input_file} -> {output_file}")

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python fix_lammps_types.py input.lmp output.lmp")
        print("\nThis script reorders atom types by atomic number (Z).")
        print("Elements are sorted: lowest Z -> highest Z")
        sys.exit(1)
    
    fix_lammps_types(sys.argv[1], sys.argv[2])
