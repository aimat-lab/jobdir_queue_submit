"""The concept of this pyhton class is to have a neat interface to manage a folder with multiple jobdirectories.
Having a managed directory, jobs can be submitted from there via a queueing system like slurm.
The goal is to be able to submit array-jobs via python, providing functions like run,check,wait,cancel etc. for this jobdirectory.
In commands, modules should be collected that are used to generate and read input for specific task and programs.
The directory management should be os-independent. 

@author: Patrick Reiser
"""

import os
import shutil
import json
import subprocess
import datetime

from mjdir.queue.slurm import _make_slurm_queue,_make_slurm_script,_make_slurm_sub

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
        if(os.path.exists(self.dirmain)==False):
            os.mkdir(self.dirmain)
        
        #Main Dict
        self.jobinfo_name = "JOBDIR_Info.json"
        self.jobinfo = {}
        self.load()


        
    ###########################################################################
    # General File IO functions by full os.path
    # They are not connected to class memebers
    ###########################################################################
            
    def _write_json_to_file(self,out_dict,filename):
        """private function to save dictionary to json in main directory.
        
        Args:
            out_dict (dict): Python dictionary with standard python objects
            filename (str): Filename or -path to write dictionary to
        """
        with open(filename, 'w') as json_file:
            json.dump(out_dict, json_file) 
            
    def _read_json_from_file(self,filename):
        """private function to read dictionary from json in main directory."""
        file_read = None
        if(os.path.exists(filename)==True):
            with open(filename) as json_file:
                file_read = json.load(json_file)
        return file_read
           
    def _copy_files_to_dir(self,directory,filelist):
        """function to copy files from a list of files to a directory."""   
        copied = []
        if(os.path.exists(directory)==True):
            for file in filelist:
                if(os.path.exists(file)==True):
                    shutil.copy(file,directory)
                    copied.append(file)
        return copied
    
    def _copy_files_from_dir(self,directory,destination,ending):
        """function to copy files from job directory to destination"""
        copied = []
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
                print("Warning: Can not delete: ",scr)
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
    
    def _remove_dir(self,jobpath):
        if(os.path.exists(jobpath)==False):
            print("Warning: Job directory does not exist.")
        else:
            try:
                shutil.rmtree(jobpath)
            except:
                print("Warning: Directory can not be deleted.")
    
    
    ###########################################################################
    # Functions for jobs by name
    ###########################################################################
    
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
      
    
    def _clean_jobname(self,name):
        """ clean the jobname from unwanted chars"""
        bad_chars = r"[-()\"#/@;:<>{}`+=~|.!?,]"
        former = int(len(name))
        for x in bad_chars:
            name = name.replace(x,"")
        name = name.replace(" ","")
        if(int(len(name)) != former):
            print("Warning: Invalid dir name, replaced by",name)
        return name
    
    
    
    ###########################################################################
    # Public
    ###########################################################################
    
    def save(self):
        self._write_json_to_file(self.jobinfo,os.path.join(self.dirmain,self.jobinfo_name))
    
    def load(self,add_existing=False):
        if(os.path.exists(os.path.join(self.dirmain,self.jobinfo_name)) == True):
            self.jobinfo = self._read_json_from_file(os.path.join(self.dirmain,self.jobinfo_name))
        for key,value in self.jobinfo.items():
            if(os.path.abspath(os.path.dirname(value['path'])) != self.dirmain):
                print("Error: Loaded of data has wrong path.",key)
        alljobs = list(self.jobinfo.keys())
        alljobs_dir = self._get_directory_list(self.dirmain)
        if(add_existing == True):
            found_dirs = False
            for x in alljobs_dir:
                if(x not in alljobs):
                    self.add(x)
                    found_dirs = True
            if(found_dirs == True):
                print("Warning: Additional directories found. Adding directories...")
        
    def add(self,job):
        """
        Main function to add job plus e.g. command. Command is updated if job already exists.
        Adding a job means creating a file directory. Commands are stored in dictionaries.
        
        Args:
            job (str,list,dict): Job names to be created. Either single string or list of strings
            
        Return:
            pathlist (str,list,dict): Path to the created file directories (string or list)
        """
        pathlist = None
        if(isinstance(job, str) == True):
            job = self._clean_jobname(job)            
            jobpath = os.path.join(self.dirmain,job)
            is_folder = os.path.exists(jobpath)
            is_jobentry = job in self.jobinfo
            if(is_folder==False):
                os.mkdir(jobpath)
            if(is_jobentry == True):
                
                self.jobinfo[job].update({"path" : str(jobpath) , "modified" : str(datetime.datetime.now()) })
            else:
                 self.jobinfo[job] = {"path" : str(jobpath) , "created" : str(datetime.datetime.now()) }
            pathlist = jobpath
        if(isinstance(job, list) == True): 
            pathlist = []
            for i in range(0,len(job)):
                i_job = self._clean_jobname(job[i])
                jobpath = os.path.join(self.dirmain,i_job)
                is_folder = os.path.exists(jobpath)
                is_jobentry = i_job in self.jobinfo
                if(is_folder==False):
                    os.mkdir(jobpath)
                if(is_jobentry == True and is_folder == True):
                    self.jobinfo[i_job].update({"path" : str(jobpath) , "modified" : str(datetime.datetime.now()) })
                else:
                    self.jobinfo[i_job] = {"path" : str(jobpath) , "created" : str(datetime.datetime.now()) }
                pathlist.append(jobpath)
        if(isinstance(job, dict) == True): 
            pathlist = []
            for key,value in job.items():
                i_job = self._clean_jobname(key)
                jobpath = os.path.join(self.dirmain,i_job)
                is_folder = os.path.exists(jobpath)
                is_jobentry = i_job in self.jobinfo
                if(is_folder==False):
                    os.mkdir(jobpath)
                jobaddinfo = {}
                jobaddinfo.update(value)
                if(is_jobentry == True and is_folder == True):
                    jobaddinfo.update({"path" : str(jobpath) , "modified" : str(datetime.datetime.now()) }) 
                    self.jobinfo[i_job].update(jobaddinfo)
                else:
                    jobaddinfo.update({"path" : str(jobpath) ,  "created" : str(datetime.datetime.now()) }) 
                    self.jobinfo[i_job] = jobaddinfo
                pathlist.append(jobpath)
        
        return pathlist
        
    
    def get(self,jobs=0,add_existing=False):
        """
        Get jobdict from job or list of jobs, which is used to write input.
        
        Args:
            jobs (str,int,list): Job names to get path for. Can be single string, list of names or int.
                                 If (int) the index of all available jobs is taken: joblist[jobs:]
                                 jobs = 0 means all jobs
                                 jobs = -1 means last job in directory list (sorted by name?)
            add_existing (bool): Whether to add existing directories found. 
        
        Returns:
            outlist (dict): Filepath of existing job/joblist requested in jobs input
        """
        alljobs = list(self.jobinfo.keys())
        alljobs_dir = self._get_directory_list(self.dirmain)
        if(add_existing == True):
            found_dirs = False
            for x in alljobs_dir:
                if(x not in alljobs):
                    self.add(x)
                    found_dirs = True
            if(found_dirs == True):
                print("Warning: Additional directories found. Adding directories...")
            alljobs = list(self.jobinfo.keys())
        joblist = {}
        if isinstance(jobs, int):
            return {x: self.jobinfo[x] for x in alljobs[jobs:]}
        if isinstance(jobs, str):
            if(jobs in alljobs):
                return {jobs : self.jobinfo[jobs]}
            else:
                print("Warning: job not found.")
        if isinstance(jobs, list):
            joblist = {x: self.jobinfo[x] for x in jobs if x in alljobs}
            if(len(joblist)<len(jobs)):
                print("Warning: Not all jobs exist, missing",len(joblist)-len(jobs) )
    
        return joblist
    

        

    def run(self,jobs=0,procs = 1,command=None,header=None,prepare_only=False):
        """Main function to start e.g. slurm arrays from jobs. The command is taken from the command 
        dictionary if not None and has preference over the command given in function call.
        
        Args:
            jobs (str,list,int): Job names to run. Can be single string, list of names or int.
                                  If (int) the index of all available jobs is taken: joblist[jobs:]
                                  jobs = 0 means all jobs
                                  jobs = -1 means last job in directory list (sorted by name?)
            procs (int): Number of bash scripts to start.            
            command (str):  default command to run if no command is specified.
            header (str):   header for queueing system that is written to bash script.
                            If the member self.header = None is not None, self.header will be used before header from function call.
            prepare_only (bool): Whether to only make scripts etc. but not acutally run them
        
        Returns:
            queue_ids (list): The ruturn e.g. ids of the submission call
        """
        #Get Paths
        sub_jobs = self.get(jobs)
        sub_keys = list(sub_jobs.keys())
        sub_path = [sub_jobs[x]['path'] for x in sub_keys]
        sub_cmd = [sub_jobs[x]['command'] if 'command' in sub_jobs[x] else command for x in sub_keys ]

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
                _make_slurm_script(self.dirmain,bash_submit,
                                    sub_keys[i:i + len_per_array],
                                    sub_path[i:i + len_per_array],
                                    sub_cmd[i:i + len_per_array],
                                    header=header)
            if(prepare_only == False):
                if(self.submit_type == "SLURM"):
                    id_sub = _make_slurm_sub(self.dirmain,bash_submit)
                    id_list.append(id_sub) 
        #submits
        return id_list
    
         

    def queue(self,print_level =2):
        """ 
        Function to check queueing system. Should be quite unique for this directory and safely get jobs. 

        Args:
            print_level (int): print information, high-level more printing, 0 means no print
        
        Returns:
            list_ids,list_scripts (tuple): list of ids, running scripts
        """
        #Check slurm
        list_ids = []
        list_scripts = []
        if(self.submit_type == "SLURM"):
            list_ids,list_scripts = _make_slurm_queue(self.dirmain,print_level=print_level)
        
        return list_ids,list_scripts
    
    
    def cancel(self,ids=[]):
        """ 
        Rudimental function to cancel queueing by id.
        
        Args:
            ids (str,list): queue ids to cancel. Can be single string, list of ids or int.
        
        """
        if(isinstance(ids,str)==True):
            ids = [ids]    
        if(self.submit_type == "SLURM"):
            for x in ids:
                proc = subprocess.run(['scancel',x],capture_output=True)
                
