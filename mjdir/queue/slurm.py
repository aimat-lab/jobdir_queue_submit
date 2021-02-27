import subprocess
import os


SLURM_DEFUALT_PROPS = {
    'time' : "1:00:00",
    'nodes' : "1",
    'tasks' : "1"
    }


def make_slurm_script(dirmain,slurm_name,asyn = 0,
                      name_list=[],
                      pathlist=[],
                      commands=[],
                      header="\n",
                      slurm_variables = SLURM_DEFUALT_PROPS):
    """Make bash script for unix for name,path and command list"""
    
    scriptpath = os.path.join(dirmain,slurm_name)
    slurmout = os.path.join(dirmain,"slurm_%j.output")
    bash_variables = {}
    bash_variables.update(SLURM_DEFUALT_PROPS)
    bash_variables.update(slurm_variables)
    
    with open(scriptpath, 'w') as rsh:
        rsh.write('#! /bin/bash\n')
        rsh.write('#SBATCH --job-name=%s\n'%slurm_name)
        rsh.write('#SBATCH --output=%s\n'%slurmout)
        
        for keys,values in bash_variables.items():
            rsh.write('#SBATCH --{key}={value}\n'.format(key=keys,value=values))
        
        rsh.write('\n')
        rsh.write(header)
        rsh.write('\n')
        for i,path in enumerate(pathlist):
            rsh.write(commands[i].format(**path))
            if(asyn > 0):
                 rsh.write(' &\n')  
            else:
                rsh.write('\n')   
            rsh.write('echo "info: submitted {path}" \n'.format(path=path)) 
            if(asyn>0 and (i+1)%asyn ==0):
                rsh.write('wait\n')  


def make_slurm_sub(dirmain,slurm_submit,bash_submit={}):
    """ make submission command for slurm via sbatch"""
    sbatch_cmd = ['sbatch']
    for keys,values in bash_submit.items():
        sbatch_cmd = sbatch_cmd + [keys,values]
    sbatch_cmd = sbatch_cmd + [os.path.join(dirmain,slurm_submit)]
    proc = subprocess.run(sbatch_cmd,capture_output=True)
    id_sub = proc.stdout.decode('utf8').strip().split(" ")[-1]
    return id_sub


def make_slurm_queue(dirmain,print_level = 0):
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



# def _get_jobs_from_slurmlog(dirmain,logfile,full_path=False):
#     """check a possible log file for individual commands"""
#     scr_path = os.path.join(dirmain,logfile)
#     output = []
#     if(os.path.exists(scr_path)==True):
#         with open(scr_path,"r") as file:
#             for line in file:
#                 if(line.split(":")[0] != ''):
#                     out = line.split(":")[0]
#                     if(full_path == True):
#                         output.append(os.path.join(dirmain,out))
#                     else:
#                         output.append(out)
#     else:
#         print("Warning: Could not find log")
#     return output