import os
import numpy as np
import time
from mjdir.MultiJobDirectory import MultiJobDirectory
from mjdir.commands.turbomole import TURBOMOLE_SLURM_HEADERS,TURBOMOLE_SLURM_COMMANDS,write_turbomole_input,read_turbomole_output,read_turbomole_eiger_file

from ase import Atoms
from ase.calculators.turbomole import Turbomole

# Important for this python module turbomole module has to be loaded externally                
print("Turbomole must be available by module load chem/turbomole for ase input")


jobs = ["H2","N2"]
cord = [[[0.0,0.0,0.0],[0.0,0.0,0.8]],[[0.0,0.0,0.0],[0.0,0.0,1.4]]]
elem = [["H","H"],["N","N"]]

params = {
    'use resolution of identity': True,   
    'total charge': 0,
    'multiplicity': 1,
    'basis set name': 'def2-SV(P)',
    'density functional': 'b3-lyp'
}


jd = MultiJobDirectory("Turbo_Example")


slurm_params = { 'tasks' : "10",
                # "ntasks-per-node" : "10",
                'time' : "30:00:00",
                'nodes' : "1"
}


submit_properties = {'-p':'normal'} # For for-hlr need partition to run slurm


for i in range(0,len(jobs)):
    jd.add(jobs[i])
    at = Atoms(elem[i],cord[i])
    calc = Turbomole(**params)
    write_turbomole_input(jd.get()[jobs[i]]['path'],calc,at)

jd.save()

print("submit ridft")
runnjobs = jd.run(procs=1,
                  asyn=2,
                  command= TURBOMOLE_SLURM_COMMANDS["energy"],
                  header = TURBOMOLE_SLURM_HEADERS["int-nano"],
                  queue_properties = slurm_params,
                  submit_properties = {}, # for int-nano
                  prepare_only=False)

print("Waiting 10s ...")
time.sleep(10)

print("submit readout")
runnjobs = jd.run(procs=2,
                  command= TURBOMOLE_SLURM_COMMANDS["eiger"],
                  header = TURBOMOLE_SLURM_HEADERS["int-nano"],
                  queue_properties = slurm_params,
                  submit_properties = {}, # for int-nano
                  prepare_only=False)

print("Waiting 10s ...")
time.sleep(10)

# Check readout    
homos = []
lumos = []
for i in range(0,len(jobs)):
    try:
        hm,lm,eng = read_turbomole_eiger_file(jd.get()[jobs[i]]['path'])
        homos.append(hm)
        lumos.append(lm)
    except:
        print("jobs not finished yet or output bad.")

print("homos:", homos)
print("lumos:", lumos)
