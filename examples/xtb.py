# -*- coding: utf-8 -*-
"""
Created on Sat Apr 18 12:44:37 2020

@author: Patrick
"""
import os
import numpy as np
from mjdir.MultiJobDirectory import MultiJobDirectory
from mjdir.commands.JOBDIRxtb import XTB_SLURM_HEADER,XTB_HOMEPATH_TARBALL_DIRECTORY,XTB_SLURM_COMMANDS,exportXYZ,read_homo_lumo

print("Set to Dir of XTB at: ",XTB_HOMEPATH_TARBALL_DIRECTORY)

jd = MultiJobDirectory("XTB_Example")
jd.slurm_header = XTB_SLURM_HEADER["default"]
jd.slurm_tasks = "1"
jd.slurm_time = "01:00:00"
#jobdir.slurm_partition = 'normal'  # For for-hlr need partition to run slurm

jlist = ["H2","N2"]
cord = [[[0.0,0.0,0.0],[0.0,0.0,0.8]],[[0.0,0.0,0.0],[0.0,0.0,1.4]]]
elem = [["H","H"],["N","N"]]

for i in range(0,len(jlist)):
    jd.add(jlist[i])
    exportXYZ(os.path.join(jd.get(jlist[i]),'mol.xyz'),cord[i],elem[i])
    

runnjobs = jd.run(procs=2,command=XTB_SLURM_COMMANDS["default"]["singlepoint"]%'mol.xyz',ignore_running=True)
jd.check()
jd.wait()

homos = []
lumos = []
for i in range(0,len(jlist)):
    hm,lm = read_homo_lumo(jd.get(jlist[i]))
    homos.append(hm)
    lumos.append(lm)

np.save("HOMO_"+jd.dirname+".npy",np.array(homos))
np.save("LUMO_"+jd.dirname+".npy",np.array(lumos))
