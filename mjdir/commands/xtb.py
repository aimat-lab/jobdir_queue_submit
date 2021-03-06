import os

XTB_HOMEPATH_TARBALL_DIRECTORY = '"~/xtb_6.2.3"'

XTB_SLURM_HEADER = {'default': ''.join([
    'ulimit -s unlimited\n',
    'export OMP_STACKSIZE=1G\n',
    'export OMP_NUM_THREADS=$SLURM_NPROCS,1\n',
    'export OMP_MAX_ACTIVE_LEVELS=1\n',
    'export MKL_NUM_THREADS=$SLURM_NPROCS\n',
    # requirements: $XTBHOME is set to `xtb` root directory
    # otherwise the script will find the location of itself here:
    'XTBHOME=' + XTB_HOMEPATH_TARBALL_DIRECTORY + '\n',
    'echo "Manually set home path to $XTBHOME"\n',
    # set up path for xtb, using the xtb directory and the users home directory
    'XTBPATH=${XTBHOME}/share/xtb:${XTBHOME}:${HOME}\n',
    # to include the documentation we include our man pages in the users manpath
    'MANPATH=${MANPATH}:${XTBHOME}/share/man\n',
    # finally we have to make the binaries and scripts accessable
    'PATH=${PATH}:${XTBHOME}/bin\n',
    'LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:${XTBHOME}/lib\n',
    'PYTHONPATH=${PYTHONPATH}:${XTBHOME}/python\n',
    'export XTBHOME PATH XTBPATH MANPATH LD_LIBRARY_PATH PYTHONPATH\n',
    '\n'
])
}

# Use %input coordinates here
XTB_SLURM_COMMANDS = {'singlepoint': 'cd {path} && xtb --scc {input} > output.txt',
                      'vIPEA': 'cd {path} && xtb --vipea {input} > output.txt'
                      }


def read_homo_lumo(path):
    """
    Read hom lumo from output

    Args:
        path (str): Filepath to destination folder.

    Returns:
        tuple: homo,lumo

    """
    homo = None
    lumo = None
    with open(os.path.join(path, "output.txt"), "r") as f:
        for line in f.readlines():
            if line.find('(HOMO)') > 0:
                line_list = line.strip().split(' ')
                line_list = [x for x in line_list if x != '']
                homo = line_list[-2]
            if line.find('(LUMO)') > 0:
                line_list = line.strip().split(' ')
                line_list = [x for x in line_list if x != '']
                lumo = line_list[-2]
    return float(homo), float(lumo)


# xtb can have xyz input file
def export_xyz(filename, coords, elements, mask=[]):
    """
    Export a XYZ file

    Args:
        filename (str): filepath of target file.
        coords (list): list of coordinates.
        elements (list): list of elements.
        mask (list, optional): Mask. Defaults to [].

    Returns:
        None.

    """
    outfile = open(filename, "w")
    if len(mask) == 0:
        outfile.write("%i\n\n" % (len(elements)))
        for atomidx, atom in enumerate(coords):
            outfile.write("%s %f %f %f\n" % (elements[atomidx].capitalize(), atom[0], atom[1], atom[2]))
    else:
        outfile.write("%i\n\n" % (len(mask)))
        for atomidx in mask:
            atom = coords[atomidx]
            outfile.write("%s %f %f %f\n" % (elements[atomidx].capitalize(), atom[0], atom[1], atom[2]))
    outfile.close()


# xtb can have turbomole inputfile
def write_turbomole(filename, atoms):
    """Method to write turbomole coord file
    
    Args:
        filename (str): Filepath of filename.
        atoms (TYPE): Atoms
    """
    from ase.constraints import FixAtoms
    from ase.units import Bohr

    if isinstance(filename, str):
        f = open(filename, 'w')
    else:  # Assume it's a 'file-like object'
        f = filename

    coord = atoms.get_positions()
    symbols = atoms.get_chemical_symbols()
    printfixed = False

    if atoms.constraints:
        for constr in atoms.constraints:
            if isinstance(constr, FixAtoms):
                fix_index = constr.index
                printfixed = True
    # print sflags

    if printfixed:
        fix_str = []
        for i in fix_index:
            if i == 1:
                fix_str.append("f")
            else:
                fix_str.append(" ")

    f.write("$coord\n")
    if printfixed:
        for (x, y, z), s, fix in zip(coord, symbols, fix_str):
            f.write('%20.14f  %20.14f  %20.14f      %2s  %2s \n'
                    % (x / Bohr, y / Bohr, z / Bohr, s.lower(), fix))

    else:
        for (x, y, z), s in zip(coord, symbols):
            f.write('%20.14f  %20.14f  %20.14f      %2s \n'
                    % (x / Bohr, y / Bohr, z / Bohr, s.lower()))
    f.write("$end\n")
