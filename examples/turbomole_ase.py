# -*- coding: utf-8 -*-
"""
Created on Sat Mar 14 11:38:49 2020

@author: Patrick
"""
import os
import numpy as np
from mjdir.MultiJobDirectory import MultiJobDirectory
from mjdir.commands.JOBDIRturbomole import TURBOMOLE_SLURM_HEADERS,TURBOMOLE_SLURM_COMMANDS,write_turbomole_input,read_turbomole_output,read_turbomole_eiger_file

from ase import Atoms
from ase.calculators.turbomole import Turbomole

# Important for this python module turbomole module has to be loaded externally                
print("Turbomole must be available by module load chem/turbomole for ase input")


params = {
    'use resolution of identity': True,   
    'total charge': 0,
    'multiplicity': 1,
    'basis set name': 'def2-SV(P)',
    'density functional': 'b3-lyp'
}


jd = MultiJobDirectory("Turbo_Example")
jd.slurm_header = TURBOMOLE_SLURM_HEADERS["int-nano"]
jd.slurm_tasks = "10"
jd.slurm_time = "30:00:00"
#jobdir.slurm_partition = 'normal'  # For for-hlr need partition to run slurm

jlist = ["H2","N2"]
cord = [[[0.0,0.0,0.0],[0.0,0.0,0.8]],[[0.0,0.0,0.0],[0.0,0.0,1.4]]]
elem = [["H","H"],["N","N"]]

for i in range(0,len(jlist)):
    jd.add(jlist[i])
    at = Atoms(elem[i],cord[i])
    calc = Turbomole(**params)
    write_turbomole_input(jd.get(jlist[i]),calc,at)

runnjobs = jd.run(procs=2,command=TURBOMOLE_SLURM_COMMANDS["int-nano"]["energy"],ignore_running=True)
jd.check()
jd.wait()
    
homos = []
lumos = []
for i in range(0,len(jlist)):
    hm,lm = read_turbomole_eiger_file(jd.get(jlist[i]))
    homos.append(hm)
    lumos.append(lm)

np.save("HOMO_"+jd.dirname+".npy",np.array(homos))
np.save("LUMO_"+jd.dirname+".npy",np.array(lumos))