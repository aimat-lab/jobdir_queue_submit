import os

# import ase


# Example Commands
TURBOMOLE_SLURM_HEADERS = {"int-nano": ''.join(['module purge\n',
                                                # 'export PARA_ARCH=SMP\n',
                                                'export PARNODES=$SLURM_NPROCS\n',
                                                'module load turbomole/7.4.1\n',
                                                'cd $SLURM_SUBMIT_DIR\n'
                                                # 'export TURBODIR=/shared/software/chem/TURBOMOLE/TURBOMOLE-V7.4.1\n',
                                                # 'export PATH=$TURBODIR/scripts:$PATH\n',
                                                # 'export PATH=$TURBODIR/bin/`sysname`:$PATH\n',
                                                # 'export OMP_NUM_THREADS=$SLURM_NPROCS\n'
                                                ]),
                           "for-hlr": ''.join(['module purge\n',
                                               # 'export PARA_ARCH=SMP\n',
                                               'export PARNODES=$SLURM_NPROCS\n'
                                               'module load chem/turbomole/7.3\n',
                                               'cd $SLURM_SUBMIT_DIR\n'
                                               # 'export TURBODIR=/shared/software/chem/TURBOMOLE/TURBOMOLE-V7.4.1\n',
                                               # 'export PATH=$TURBODIR/scripts:$PATH\n',
                                               # 'export PATH=$TURBODIR/bin/`sysname`:$PATH\n',
                                               # 'export OMP_NUM_THREADS=$SLURM_NPROCS\n'
                                               ])
                           }

TURBOMOLE_SLURM_COMMANDS = {"energy": 'cd {path} && ridft > ridft.out',
                            "eiger": 'cd {path} && eiger > atomic.levels.dat',
                            "gradient": "",
                            "optimize": "cd {path} && jobex -ri > add_jobex.out",
                            "frequencies": ""
                            }


def write_turbomole_input(filepath, calc, at):
    """
    Write input files for turbomole

    Args:
        filepath (str,path): File path to destination folder.
        calc (TYPE): ASE Turbomole object.
        at (TYPE): ASE atoms object.

    Returns:
        None.

    """
    workdir = os.getcwd()
    os.chdir(filepath)
    try:
        calc.set_atoms(at)
        calc.initialize()
    except:
        print("Error: cant make input for: ", filepath)
        os.chdir(workdir)
    else:
        os.chdir(workdir)


def read_turbomole_output(filepath, calc):
    """
    Read turbomole output in ASE turbomole object.

    Args:
        filepath (str,path): File path to destination folder.
        calc (TYPE): ASE Turbomole object.

    Returns:
        calc (TYPE): ASE Turbomole object.

    """
    workdir = os.getcwd()
    os.chdir(filepath)
    try:
        calc.read_results()
    except:
        print("Error: cant read input for: ", filepath)
        os.chdir(workdir)
    else:
        os.chdir(workdir)
        return calc


def read_turbomole_eiger_file(path):
    """
    Read the ouput of eiger files.

    Args:
        path (str,path): File path to destination folder.

    Returns:
        tuple: homo,lumo,toteng.

    """
    homo = None
    lumo = None
    toteng = None
    with open(os.path.join(path, "atomic.levels.dat"), "r") as f:
        for line in f.readlines():
            if line.find('HOMO:') > 0:
                line_list = line.split(' ')
                homo = line_list[-2]
            if line.find('LUMO:') > 0:
                line_list = line.split(' ')
                lumo = line_list[-2]
            if line.find('Total energy') >= 0:
                line_list = line.split(' ')
                toteng = line_list[-2]
    return float(homo), float(lumo), float(toteng)
