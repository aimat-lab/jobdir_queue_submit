"""The concept of this pyhton class is to have a neat interface to manage a folder with multiple jobdirectories.
Having a managed directory, jobs can be submitted from there via a queueing system like slurm.
The goal is to be able to submit array-jobs via python, providing functions like run,check,wait,cancel etc. for this jobdirectory.
Ideally, also workflows could be realised, by creating a python module that can be called from comandline.
In commands, modules should be collected that are used to generate and read input for specific task and programs.
They will use python libraries like ase or pymatgen. The main class is sought to have as little dependencies as possible, ideally none.
A ssh version could be realised but for now, the python functions have to be run on the cluster, i.e. where a queueing system is available.
The directory management should be os-independent. 

@author: Patrick Reiser
"""

import os
import shutil
import json
import subprocess
import time


class MultiJobDirectory(object):
    """Class to manage jobs and submit array of task with queue system eg. slurm.
    Concept is job "=" a directory from wich the commands are run
    The function run() basically makes script that goes to jobdirectory and execute a given command.
    """
    
    def __init__(self,name,dirpath=os.path.join(os.path.expanduser("~"),"MultiJobDirectory")):
        """Creates a new or "loads" an existing directory and initializes class.
        
        Args:
            name (str): Name of the directory 
            dirpath (str) : Path where to make/find the main jobdirectory on the operating system
                            Default is user path/MultiJobDirectory
        """
        
        self.submit_type = "SLURM" # Only possible queue system supported
        
        #Slurm settings
        self.slurm_header = None
        self.slurm_time = "10:00:00"
        self.slurm_nodes = "1"
        self.slurm_tasks = "10"
        self.slurm_partition = None

        
        #File Management
        self.maindirpath = dirpath
        if(os.path.exists(self.maindirpath)==False):
            os.mkdir(self.maindirpath)
        self.dirname = name
        self.dirmain = os.path.join(dirpath,name)
        self.commandlist_name = "JOBDIR_Commands.json"
        self.command_list = {}

        
        if(os.path.exists(self.dirmain)==False):
            os.mkdir(self.dirmain)
        if(os.path.exists(os.path.join(self.dirmain, self.commandlist_name))== False):
            self._write_commands(self.command_list)
        else:
            self.command_list = self._get_commands()
        
    ###########################################################################
    # General File IO functions by full os.path
    # They are not connected to class memebers and are written in a general form
    ###########################################################################
            
    def _write_json_to_file(self,out_dict,filename):
        """private function to save dictionary to json in main directory
        
        Args:
            out_dict (dict): Python dictionary with standard python objects
            filename (str): Filename or -path to write dictionary to
        """
        with open(filename, 'w') as json_file:
            json.dump(out_dict, json_file) 
            
    def _read_json_from_file(self,filename):
        """private function to read dictionary from json in main directory"""
        file_read = None
        if(os.path.exists(filename)==True):
            with open(filename) as json_file:
                file_read = json.load(json_file)
        return file_read
           
    def _copy_files_to_dir(self,directory,filelist):
        """function to copy files from a list of files to a directory"""
        
        copied = []
        if isinstance(directory,str):
            if(os.path.exists(directory)==True):
                for file in filelist:
                    if(os.path.exists(file)==True):
                        shutil.copy(file,directory)
                        copied.append(file)
        return copied
    
    def _copy_files_from_dir(self,directory,destination,ending):
        """function to copy files from job directory to destination"""
        copied = []
        if isinstance(directory,str):
            search_path = directory
            if(os.path.exists(search_path)==True):
                if ending != "":
                    flist = [f for f in os.scandir(search_path) if f.name.endswith(ending)]
                else:
                    flist = [f for f in os.scandir(search_path) ]
                for file in flist:
                   shutil.copy(file,destination)
                   copied.append(file)
        return copied
    
    def _get_file_list(self,search_path,ending=""):
        """private function to read all files in searchpath, ignores directiories"""
        files = []
        if(os.path.exists(search_path)==True):
            if(ending != ""):
                files =  [f for f in os.listdir(search_path) if os.path.isfile(os.path.join(search_path, f)) and f.endswith(ending)]
            else:
                files =  [f for f in os.listdir(search_path) if os.path.isfile(os.path.join(search_path, f))]
        return files
    
    
    def _remove_all_files(self,searchpath,ending):
        """clean up all files"""
        list_remove = self._get_file_list(searchpath,ending=ending)
        outlist = []
        for scr in list_remove:
            try:
                os.remove(os.path.join(searchpath,scr))
            except:
                print("Warning cant delete: ",scr)
            else:
                outlist.append(scr)
        return outlist

    def _get_directory_list(self,searchpath,full_path = False):
        """lists all current drectories in directory"""
        dirlist = []
        if(os.path.exists(searchpath)):
            if(full_path == False):
                dirlist = [ f.name for f in os.scandir(searchpath) if f.is_dir() ]
            else:
                dirlist = [ f.path for f in os.scandir(searchpath) if f.is_dir() ]
        return dirlist
    
    ###########################################################################
    # Functions for jobs by name
    ###########################################################################
    
    def _get_commands(self):     
        """ read command dictionary"""
        return self._read_json_from_file(os.path.join(self.dirmain,self.commandlist_name))
    
    def _write_commands(self,command_list):
        """ write out command dictionary"""
        self._write_json_to_file(command_list,os.path.join(self.dirmain,self.commandlist_name))
    
    def _get_free_bash_index(self):
        """sarches for highest number of submitted .sh in main directory"""
        #Find bashs
        list_bsh = self._get_file_list(self.dirmain,ending=".sh" )
        max_num = 0
        for x in list_bsh:
            x = x.replace(".sh","")
            x = x.split('_')
            if(len(x)>1):
                max_num = max(int(x[-1]),max_num)
        return max_num+1    
    
    def _get_jobs_from_script(self,scriptname,full_path=False):
        """check which jobs are run in script"""
        scr_path = os.path.join(self.dirmain,scriptname)
        output = []
        if(os.path.exists(scr_path)==True):
            with open(scr_path,"r") as file:
                for line in file:
                    if(line[:3] == 'cd '):
                        dirline = line[3:].strip()
                        if(dirline[:len(self.dirmain)].strip() == self.dirmain and len(dirline) >len(self.dirmain)):
                            if(full_path == False):
                                output.append(os.path.basename(dirline))
                            else:
                                output.append(dirline)
        else:
            print("Warning: Could not find script")
        return output
    
    def _get_jobs_from_log(self,logfile,full_path=False):
        """check a possible log file for individual commands"""
        scr_path = os.path.join(self.dirmain,logfile)
        output = []
        if(os.path.exists(scr_path)==True):
            with open(scr_path,"r") as file:
                for line in file:
                    if(line.split(":")[0] != ''):
                        out = line.split(":")[0]
                        if(full_path == True):
                            output.append(os.path.join(self.dirmain,out))
                        else:
                            output.append(out)
        #else:
            #print("Warning: Could not find log")
        return output
    
    def _get_singe_job(self,job,full_path=False):
        """check if jobdir exists and returns path if specified"""
        if(os.path.exists(os.path.join(self.dirmain,job))==True):
            if(full_path==True):
                return os.path.join(self.dirmain,job)
            else:
                return job
    
    def _remove_singe_job(self,job,ignore_running=True):
        """deletes jobdirectors, @TODO: check for running"""
        jobpath = os.path.join(self.dirmain,job)
        if(os.path.exists(jobpath)==False):
            print("Job directory does not exist, do nothing")
        else:
            try:
                self.command_list = self._get_commands() #extra layer of security by command list
                if(job in self.command_list):
                    shutil.rmtree(jobpath)
                else:
                    print("Directory was not created by this class, add job again and remove then")
            except:
                print("Job cant be deleted, still running or accessed")
            else:
                self.command_list = self._get_commands()
                if(job in self.command_list):
                    self.command_list.pop(job)
                self._write_commands(self.command_list)
                return job

    def _get_joblist(self,full_path = False):
        """lists all current jobdrectories in main directory"""
        return self._get_directory_list(self.dirmain,full_path=full_path)   
    
    
    ###########################################################################
    # Functions for preparing or parsing input/output
    ###########################################################################
    
    def _clean_jobname(self,name):
        """ clean the jobname from unwanted chars"""
        bad_chars = r"[-()\"#/@;:<>{}`+=~|.!?,]"
        for x in bad_chars:
            name = name.replace(x,"")
        name = name.replace(" ","")
        return name
    
    def _parse_jobs_to_joblist(self,jobs,alljobs=None):
        """flexible input parsing for selecting jobs """
        joblist = []
        if isinstance(jobs, int):
            if alljobs == None:
                alljobs = self._get_joblist()
            joblist = alljobs[jobs:]
        if isinstance(jobs, str):
            if(os.path.exists(os.path.join(self.dirmain,jobs))==True):
                joblist = [jobs]
            else:
                print("Warning: job not found in directories: ",jobs)
        if isinstance(jobs, list):
            if alljobs == None:
                alljobs = self._get_joblist()
            joblist = [x for x in jobs if x in alljobs]
            if(len(joblist)<len(jobs)):
                print("Warning: jobs not found in directories")
        return joblist

    def _parse_ids_to_idlist(self,ids,allids=None):
        """flexible input parsing for selecting queue ids """
        idlist = []
        if allids == None:
            allids,_ = self.queue(print_level=0)
        if isinstance(ids, int):
            idlist = allids[ids:]
        if isinstance(ids, str):
            if(ids in allids):
                idlist = [ids]
            else:
                print("Warning: Queue id is not found in running id list: ",allids)
        if isinstance(ids, list):
            idlist = [x for x in ids if x in allids]
            if(len(idlist)<len(ids)):
                print("Warning: Not all queue ids are found in running id list")
        return idlist
    
    def _parse_list_to_type(self,joblist,typein):
        """flexible output for parsing string types"""
        if(typein==int):
            return joblist # does not make sense to cast to index here
        if(typein==str):
            if(len(joblist)==1):
                return joblist[0]
        if(typein== list):
            return joblist
    
    ###########################################################################
    # Functions for queue io
    ###########################################################################    
    
    def _make_slurm_script(self,slurm_name,name_list=[],pathlist=[],commands=[],header="\n",sl_time="10:00:00",sl_nodes = "1",sl_tasks = "10"):
        """Make bash script for unix for name,path and command list"""
        scriptpath = os.path.join(self.dirmain,slurm_name)
        slurmout = os.path.join(self.dirmain,"slurm_%j.output")
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
                rsh.write('cd %s\n'%self.dirmain)
                rsh.write('echo "%s:ended in script %s" >> log_%s.txt\n'%(name_list[i],slurm_name, os.path.splitext(slurm_name)[0]))
                rsh.write('\n')    
    
    def _make_slurm_sub(self,slurm_submit):
        """ make submission command for slurm via sbatch"""
        sbatch_cmd = ['sbatch']
        if(self.slurm_partition != None):
            sbatch_cmd = sbatch_cmd + ['-p',self.slurm_partition]
        sbatch_cmd = sbatch_cmd + [os.path.join(self.dirmain,slurm_submit)]
        proc = subprocess.run(sbatch_cmd,capture_output=True)
        id_sub = proc.stdout.decode('utf8').strip().split(" ")[-1]
        return id_sub
    
    def _make_slurm_queue(self,print_level = 0):
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
            if(os.path.exists(os.path.join(self.dirmain,line_bashname)) and os.path.basename(self.dirmain) == os.path.basename(os.path.dirname(line_jobdir))):
                list_ids.append(line_id)
                list_scripts.append(line_bashname)
                if(print_level >= 3):
                    print("ID: ", line_id,", Script: " ,line_bashname)
        if(print_level == 2):
            print("Number of Slurms tasks running for this directory:" , len(list_scripts))  
        return list_ids,list_scripts
    
    ###########################################################################
    # Public
    ###########################################################################

    
    def add(self,job,command=None):
        """Main function to add job plus command. Command is updated if job already exists.
        Adding a job means creating a file directory. Commands are stored in dictionaries.
        
        Args:
            job (str,list): Job names to be created. Either single string or list of strings
            command (str):  Command that is stored for each job. If list of jobs each job gets
                            the same command string. Can be None (default). If None, the command 
                            needs to be specified in run().
        Return:
            pathlist (str,list): Path to the created file directories (string or list)
        """
        pathlist = []
        if(isinstance(job, str) == True):
            job = self._clean_jobname(job)            
            jobpath = os.path.join(self.dirmain,job)
            if(os.path.exists(jobpath)==False):
                os.mkdir(jobpath)
            self.command_list = self._get_commands()
            self.command_list.update({job:command})
            self._write_commands(self.command_list)
            pathlist = [jobpath] 
        if(isinstance(job, list) == True): 
            for i in range(0,len(job)):
                i_job = self._clean_jobname(job[i])
                jobpath = os.path.join(self.dirmain,i_job)
                if(os.path.exists(jobpath)==False):
                    os.mkdir(jobpath)
                pathlist.append(jobpath)
                self.command_list = self._get_commands()
                self.command_list.update({i_job:command})
                self._write_commands(self.command_list)
                
        pathlist = self._parse_list_to_type(pathlist,type(job))
        return pathlist
            

    def run(self,jobs=0,procs = 1,command=None,header=None,ignore_running=False,scripts_only=False):
        """Main function to start e.g. slurm arrays from jobs. The command is taken from the command 
        dictionary if not None and has preference over the command given in function call.
        
        Args:
            jobs (str,int,list): Job names to run. Can be single string, list of names or int.
                                If (int) the index of all available jobs is taken: joblist[jobs:]
                                jobs = 0 means all jobs
                                jobs = -1 means last job in directory list (sorted by name?)
            command (str):  dafault command to run for all jobs which do not have a command specified in the
                            command dictionary, which is defined by add(job,command=None)
            header (str):   header for queueing system that is written to bash script.
                            If the member self.header = None is not None, self.header will be used before header from function call.
            ignore_running (bool): Start command from jobdirectory even though there is already a slurm script running in it.
            scripts_only (bool): Whether to only make scripts but not acutally run them
        
        Returns:
            queue_ids (list): The ruturn e.g. ids of the submission call
        """
        
        #Get default Header/Command
        if(header == None):
            header = '\n'
        if(self.slurm_header != None):
            header = self.slurm_header
        if(command == None):
            command = '\n'
        
        #Get list of jobs to run
        joblist = self._get_joblist()
        check_list = self._parse_jobs_to_joblist(jobs,joblist)
        ignorelist = []
        if(ignore_running == False):
            ignorelist = self.check(print_level=0)   
        
        if(ignore_running == True): #Needs to be done        
            sub_keys = check_list
        else:
            sub_keys = [key for key in check_list if key not in ignorelist]
            
        #Get Commands
        self.command_list = self._get_commands()
        sub_cmd = []
        for key in sub_keys:
            if(key in self.command_list):
                if(self.command_list[key] != None):
                    sub_cmd.append(self.command_list[key])
                else:
                    sub_cmd.append(command)
            else:
                sub_cmd.append(command)

        #Get Paths
        sub_path = []
        for key in sub_keys:
            sub_path.append(os.path.join(self.dirmain,key))
        
        #Get job array size
        len_jobs = len(sub_keys)
        num_procs = min(len_jobs,procs)
        len_per_array = len_jobs// num_procs + (len_jobs % num_procs > 0) 
        
        #Submit slurms
        id_list = []
        for i in range(0, len_jobs, len_per_array):
            num = self._get_free_bash_index()
            bash_submit= "%s_%i.sh"%(self.dirname,num)
            if(self.submit_type == "SLURM"):
                self._make_slurm_script(bash_submit,
                                    sub_keys[i:i + len_per_array],
                                    sub_path[i:i + len_per_array],
                                    sub_cmd[i:i + len_per_array],
                                    header=header,
                                    sl_nodes = self.slurm_nodes,
                                    sl_tasks = self.slurm_tasks,
                                    sl_time =self.slurm_time)
            if(scripts_only == False):
                if(self.submit_type == "SLURM"):
                    id_sub = self._make_slurm_sub(bash_submit)
                    id_list.append(id_sub) 
        #submits
        return id_list
    
    def get(self,jobs=0,full_path=True):
        """Get file path for job or list of jobs, which is used to write input.
        
        Args:
            jobs (str,int,list): Job names to get path for. Can be single string, list of names or int.
                                If (int) the index of all available jobs is taken: joblist[jobs:]
                                jobs = 0 means all jobs
                                jobs = -1 means last job in directory list (sorted by name?)
            full_path (bool): whether to return full path (default) or only the name if existing.
        
        Returns:
            outlist (str,list): Filepath of existing job/joblist requested in jobs input
        """
        
        joblist = self._parse_jobs_to_joblist(jobs)
        outlist = []
        if(full_path == True):
            outlist = [os.path.join(self.dirmain,x) for x in joblist]
        else:
            outlist= joblist
        outlist = self._parse_list_to_type(outlist,type(jobs))
        return outlist

    def check(self,print_level = 2,check_logs = True):
        """Function to check which jobs are running.
        
        Args:
            print_level (int): print information, high-level more printing, 0 means no print
            check_logs (bool): whether to check logs if a single jobs in array already finished
        
        Returns:
            running (list): list of running jobs for this class/main-directory
        """
        #Check possible jobs
        joblist = self._get_joblist()
        if(print_level >= 2):
            print("Number of jobs found:", len(joblist))
        
        #Check slurm
        list_ids, list_scripts = self.queue(print_level)
        
        #find running jobs for task
        running = []
        for runscr in list_scripts:
            if check_logs == False:
                scrjobsrun = self._get_jobs_from_script(runscr)
                running += [jo for jo in scrjobsrun if jo in joblist]
            else:
                scrjobsrun = self._get_jobs_from_script(runscr)
                scrlog = self._get_jobs_from_log("log_"+runscr.replace(".sh",".txt"))
                running += [jo for jo in scrjobsrun if jo not in scrlog and jo in joblist]
       
        if(print_level >= 2):
            print("Number of single jobs still running:",len(running))
        
        return running
        
    def evaluate(self,eval_function,jobs=0):
        """Wrapper function to test if run was succesful or retrieve values
        @TODO: improve this function, use decorators or something
        
        Args:
            eval_function (function): python function to call on each job directory, must accept filepath
            jobs (str,int,list): Job names to search for. Can be single string, list of names or int.
                                If (int) the index of all available jobs is taken: joblist[jobs:]
                                jobs = 0 means all jobs
                                jobs = -1 means last job in directory list (sorted by name?)
                                default is 0: all jobs
        Return:
            outlist (list): output of eval_function for each exisiting job in input jobs
        """
        joblist = self._parse_jobs_to_joblist(jobs)
        outlist = []            
        for key in joblist:
                outlist.append([key,eval_function(os.path.join(self.dirmain,key))])
        #outlist = self._parse_list_to_type(outlist,type(jobs))
        return outlist

    def remove(self,jobs=None):
        """Delete jobdirectories, may cause runnig slurm to crash or is denied.
        !!Warning!! this really removes os directories which is potentiall dangerous if jobdir is falsely
        initialized. Better use trash function or delete manually.
        
        Args:
            jobs (str,int,list): Job names to remove. Can be single string, list of names or int.
                                If (int) the index of all available jobs is taken: joblist[jobs:]
                                jobs = 0 means all jobs
                                jobs = -1 means last job in directory list (sorted by name?)
                                default is None: no jobs
        Return:
            oulist (str,list): list of removed directories including files plus subdirectories
        """
        joblist = self._parse_jobs_to_joblist(jobs)
        outlist = []
        for job in joblist:
            outlist.append(self._remove_singe_job(job))
        outlist = self._parse_list_to_type(outlist,type(jobs))
        return outlist
            
    def wait(self,jobs=0,updates=1,maxtime=25):
        """ Wait for jobs to finish. Repeatedly ask queue if jobs are finished.
        
        Args:
            jobs (str,int,list): Job names to wait for. Can be single string, list of names or int.
                                If (int) the index of all available jobs is taken: joblist[jobs:]
                                jobs = 0 means all jobs
                                jobs = -1 means last job in directory list (sorted by name?)
                                default is 0: all jobs
            updates (num): time wait between checks in min
            maxtime (num): maximum time to wait for jobs in h
            
        Return:
            oulist (str,list): list of jobs still running after timeout   
        """
        joblist = self._parse_jobs_to_joblist(jobs)
        i = 0
        while i*updates<maxtime*60:
            time.sleep(updates*60)
            i = i+1
            running_jobs = self.check(print_level=0) 
            bool_running = False
            for iter_jobs in joblist:
                if(iter_jobs in running_jobs):
                    bool_running = True
                    break
            if(bool_running == False):
                print("Time waited [min]:",i*updates)        
                return 0
            print("Jobs still running: ",len(running_jobs))
        print("Error Timeout:",i*updates)
        return len(self.check(print_level=0))

    def queue(self,print_level =2):
        """ function to check queueing system. Is used by check(). Should be quite unique for this directory and safely get jobs. 

        Args:
            print_level (int): print information, high-level more printing, 0 means no print
        
        Returns:
            list_ids,list_scripts (tuple): list of ids, running scripts
        """
        #Check slurm
        list_ids = []
        list_scripts = []
        if(self.submit_type == "SLURM"):
            list_ids,list_scripts = self._make_slurm_queue(print_level=print_level)
        
        return list_ids,list_scripts
    
    def cancel(self,ids=0):
        """ Rudimental function to cancel queueing job by id.
        @TODO: This is potentially dangerous as ids from check() are not unambigous.
        @TODO: make skip marks or kill scipts by jobname
        
        Args:
            ids (str,int,list): queue ids to cancel. Can be single string, list of ids or int.
                                If (int) the index of all available ids is taken: idlist[ids:]
                                ids = 0 means all running ids for this directory
                                ids = -1 means last id in id list (sorted by index)
                                default is 0: all ids   
        """
        idlist = self._parse_ids_to_idlist(ids)
        if(self.submit_type == "SLURM"):
            for x in idlist:
                proc = subprocess.run(['scancel',x],capture_output=True)


    def clean_up(self):
        """@TODO: remove scipts and logs and maybe zip complete folder to finish up"""
        pass
    
    def trah(self):
        """@TODO: make trashfolder and move abandonned jobs there"""
        pass