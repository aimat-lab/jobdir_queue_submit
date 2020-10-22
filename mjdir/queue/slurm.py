"""
Slurm functions.

@author: Patrick
"""

import subprocess
import os

def _get_jobs_from_slurmlog(dirmain,logfile,full_path=False):
    """check a possible log file for individual commands"""
    scr_path = os.path.join(dirmain,logfile)
    output = []
    if(os.path.exists(scr_path)==True):
        with open(scr_path,"r") as file:
            for line in file:
                if(line.split(":")[0] != ''):
                    out = line.split(":")[0]
                    if(full_path == True):
                        output.append(os.path.join(dirmain,out))
                    else:
                        output.append(out)
    else:
        print("Warning: Could not find log")
    return output


###########################################################################
# Functions for queue io
###########################################################################    

def _make_slurm_script(dirmain,slurm_name,name_list=[],pathlist=[],commands=[],header="\n",sl_time="10:00:00",sl_nodes = "1",sl_tasks = "10"):
    """Make bash script for unix for name,path and command list"""
    scriptpath = os.path.join(dirmain,slurm_name)
    slurmout = os.path.join(dirmain,"slurm_%j.output")
    with open(scriptpath, 'w') as rsh:
        rsh.write('#! /bin/bash\n')
        rsh.write('#SBATCH --time=%s\n'%sl_time)
        rsh.write('#SBATCH --job-name=%s\n'%slurm_name)
        rsh.write('#SBATCH --nodes=%s\n'%sl_nodes)
        rsh.write('#SBATCH --ntasks-per-node=%s\n'%sl_tasks)
        rsh.write('#SBATCH --output=%s\n'%slurmout)
        rsh.write('\n')
        rsh.write(header)
        rsh.write('\n')
        for i,path in enumerate(pathlist):
            rsh.write('cd %s\n'%path)
            rsh.write(commands[i])
            rsh.write('\n')   
            rsh.write('cd %s\n'%dirmain)
            rsh.write('echo "%s:ended in script %s" >> log_%s.txt\n'%(name_list[i],slurm_name, os.path.splitext(slurm_name)[0]))
            rsh.write('\n')    

def _make_slurm_sub(dirmain,slurm_submit,slurm_partition=None):
    """ make submission command for slurm via sbatch"""
    sbatch_cmd = ['sbatch']
    if(slurm_partition != None):
        sbatch_cmd = sbatch_cmd + ['-p',slurm_partition]
    sbatch_cmd = sbatch_cmd + [os.path.join(dirmain,slurm_submit)]
    proc = subprocess.run(sbatch_cmd,capture_output=True)
    id_sub = proc.stdout.decode('utf8').strip().split(" ")[-1]
    return id_sub


def _make_slurm_queue(dirmain,print_level = 0):
    """get queue list from slurm """
    #Check slurm
    list_ids = []
    list_scripts = []
    usr = os.environ.get('USER')
    proc = subprocess.run(['squeue',"-u",usr,"-O","jobid:.50,name:.150,stdout:.200"],capture_output=True)
    all_info_user = proc.stdout.decode('utf-8').split('\n')
    all_info_user = [x for x in all_info_user if x != '']
    if(print_level == 2):
        print("Number of Slurm tasks running:", len(all_info_user)-1)
    for i in range(1,len(all_info_user)):
        line_id = all_info_user[i][:50].strip()
        line_bashname = all_info_user[i][50:200].strip()
        line_jobdir = all_info_user[i][200:].strip()
        line_jobdir = os.path.realpath(line_jobdir)
        #Check bash name plus directory via slurm output (requires slurm submit as above)
        if(os.path.exists(os.path.join(dirmain,line_bashname)) and os.path.basename(dirmain) == os.path.basename(os.path.dirname(line_jobdir))):
            list_ids.append(line_id)
            list_scripts.append(line_bashname)
            if(print_level >= 3):
                print("ID: ", line_id,", Script: " ,line_bashname)
    if(print_level == 2):
        print("Number of Slurms tasks running for this directory:" , len(list_scripts))  
    return list_ids,list_scripts