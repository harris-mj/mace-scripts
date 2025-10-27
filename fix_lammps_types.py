#!/usr/bin/env python3
"""
Reorder atom types in LAMMPS data file to ensure consistent type IDs.
Usage: python fix_lammps_types.py input.lmp output.lmp
"""

import sys
import re

# Define desired element to type ID mapping
ELEMENT_ORDER = {
    'Al': 1,
    'Ti': 2,
    'Cr': 3,
    'Mo': 4,
    'W': 5,
    'N': 6
}

# Atomic masses for identification
MASSES = {
    'Al': 26.982,
    'Ti': 47.867,
    'Cr': 51.996,
    'Mo': 95.95,
    'W': 183.84,
    'N': 14.007
}

def identify_element(mass):
    """Identify element from mass (with small tolerance)"""
    mass = float(mass)
    for element, ref_mass in MASSES.items():
        if abs(mass - ref_mass) < 0.5:
            return element
    raise ValueError(f"Unknown mass: {mass}")

def fix_lammps_types(input_file, output_file):
    with open(input_file, 'r') as f:
        lines = f.readlines()
    
    # Find section boundaries
    masses_start = -1
    masses_end = -1
    atoms_start = -1
    
    for i, line in enumerate(lines):
        if 'Masses' in line.strip():
            masses_start = i
        elif 'Atoms' in line.strip():
            atoms_start = i
            if masses_end == -1:
                masses_end = i
            break
    
    # If masses_end wasn't set, find the first blank line after masses
    if masses_end == -1:
        for i in range(masses_start + 1, len(lines)):
            if lines[i].strip() == '':
                masses_end = i
                break
    
    if masses_start == -1 or atoms_start == -1:
        print("Error: Could not find Masses or Atoms sections")
        return
    
    # Parse masses section to find current type->element mapping
    # We need to parse ALL mass entries, even the indented ones from atomsk
    current_type_to_element = {}
    
    print(f"Parsing masses from line {masses_start+1} to {atoms_start}")
    
    for i in range(masses_start + 1, atoms_start):
        line = lines[i].strip()
        if not line or line.startswith('#'):
            continue
        
        # Remove comments and parse
        parts = line.split('#')[0].split()
        
        if len(parts) >= 2:
            try:
                type_id = int(parts[0])
                mass = float(parts[1])
                element = identify_element(mass)
                # Only store if we haven't seen this type yet
                # This prioritizes the first occurrence
                if type_id not in current_type_to_element:
                    current_type_to_element[type_id] = element
                    print(f"  Type {type_id}: {element} (mass {mass})")
            except (ValueError, IndexError) as e:
                print(f"  Warning: Could not parse line {i}: {line} ({e})")
    
    if not current_type_to_element:
        print("Error: No masses found!")
        return
    
    # Create mapping: old_type -> new_type
    type_mapping = {}
    for old_type, element in current_type_to_element.items():
        new_type = ELEMENT_ORDER[element]
        type_mapping[old_type] = new_type
    
    print(f"\nType mapping: {type_mapping}")
    print(f"Element mapping: {current_type_to_element}")
    
    # Write output file
    with open(output_file, 'w') as f:
        # Write everything before Masses section
        for i in range(masses_start + 1):
            f.write(lines[i])
        
        # Write blank line after "Masses" header
        f.write('\n')
        
        # Write new Masses section with atomsk-style formatting
        for element, new_type in sorted(ELEMENT_ORDER.items(), key=lambda x: x[1]):
            # Match atomsk's formatting: lots of spaces, more decimal places
            f.write(f"            {new_type}   {MASSES[element]:.8f}             # {element}\n")
        
        # Write blank line after masses
        f.write('\n')
        
        # Write Atoms section header
        f.write(lines[atoms_start])
        
        # Write blank line after "Atoms" header  
        f.write('\n')
        
        # Process atoms with remapped types and atomsk-style formatting
        for i in range(atoms_start + 1, len(lines)):
            line = lines[i]
            
            # Skip comments and blank lines
            if not line.strip() or line.strip().startswith('#'):
                continue
            
            # Check if this looks like an atom line (starts with atom ID)
            parts = line.split()
            if len(parts) >= 2:
                try:
                    atom_id = int(parts[0])
                    old_type = int(parts[1])
                    
                    # Remap type
                    if old_type in type_mapping:
                        new_type = type_mapping[old_type]
                        # Match atomsk's atom formatting: right-aligned IDs, proper spacing
                        coords = '       '.join(parts[2:5]) if len(parts) >= 5 else ' '.join(parts[2:])
                        f.write(f"      {atom_id:4d}    {new_type}        {coords}\n")
                    else:
                        # Type not in mapping, write as-is
                        f.write(line)
                except (ValueError, IndexError):
                    # Not an atom line, skip
                    pass
    
    print(f"\nFixed types: {input_file} -> {output_file}")

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python fix_lammps_types.py input.lmp output.lmp")
        sys.exit(1)
    
    fix_lammps_types(sys.argv[1], sys.argv[2])
