# import datetime
import json
import os
import shutil
import subprocess

from mjdir.queue.slurm import make_slurm_queue, make_slurm_script, make_slurm_sub


class MultiJobDirectory(object):
    """Class to manage jobs and submit array of task with queue system eg. slurm.
    
    Concept is each subjob "=" a directory from wich the commands are run.
    The function run() submits a script that goes to a job directory and execute a given command.
    """

    def __init__(self, name, dirpath=os.path.join(os.path.expanduser("~"), "MultiJobDirectory")):
        """Creates a new or "loads" an existing directory and initializes class.
        
        Args:
            name (str): Name of the directory 
            dirpath (str) : Path where to make/find the main jobdirectory on the operating system
                            Default is user path/MultiJobDirectory
        """

        self.submit_type = "SLURM"  # Only possible queue system supported

        # File Management
        self.maindirpath = dirpath
        if not os.path.exists(self.maindirpath):
            os.mkdir(self.maindirpath)
        self.dirname = name
        self.dirmain = os.path.join(dirpath, name)
        if not os.path.exists(self.dirmain):
            os.mkdir(self.dirmain)

        # Main Dict
        self.jobinfo_name = "JOBDIR_Info.json"
        self.jobinfo = {}
        self.load()

    ###########################################################################
    # General File IO functions by full os.path
    # They are not connected to class memebers
    ###########################################################################

    @staticmethod
    def _write_json_to_file(out_dict, filename):
        """private function to save dictionary to json in main directory.
        
        Args:
            out_dict (dict): Python dictionary with standard python objects
            filename (str): Filename or -path to write dictionary to
        """
        with open(filename, 'w') as json_file:
            json.dump(out_dict, json_file)

    @staticmethod
    def _read_json_from_file(filename):
        """private function to read dictionary from json in main directory."""
        file_read = None
        if os.path.exists(filename):
            with open(filename) as json_file:
                file_read = json.load(json_file)
        return file_read

    @staticmethod
    def _copy_files_to_dir(directory, filelist):
        """function to copy files from a list of files to a directory."""
        copied = []
        if os.path.exists(directory):
            for file in filelist:
                if os.path.exists(file):
                    shutil.copy(file, directory)
                    copied.append(file)
        return copied

    @staticmethod
    def _copy_files_from_dir(directory, destination, ending):
        """function to copy files from job directory to destination"""
        copied = []

        search_path = directory
        if os.path.exists(search_path):
            if ending != "":
                flist = [f for f in os.scandir(search_path) if f.name.endswith(ending)]
            else:
                flist = [f for f in os.scandir(search_path)]
            for file in flist:
                shutil.copy(file, destination)
                copied.append(file)
        return copied

    @staticmethod
    def _get_file_list(search_path, ending=""):
        """private function to read all files in searchpath, ignores directiories"""
        files = []
        if os.path.exists(search_path):
            if ending != "":
                files = [f for f in os.listdir(search_path) if
                         os.path.isfile(os.path.join(search_path, f)) and f.endswith(ending)]
            else:
                files = [f for f in os.listdir(search_path) if os.path.isfile(os.path.join(search_path, f))]
        return files

    def _remove_all_files(self, searchpath, ending):
        """clean up all files"""
        list_remove = self._get_file_list(searchpath, ending=ending)
        outlist = []
        for scr in list_remove:
            try:
                os.remove(os.path.join(searchpath, scr))
            except FileNotFoundError:
                print("Warning: Can not delete: ", scr)
            else:
                outlist.append(scr)
        return outlist

    @staticmethod
    def _get_directory_list(searchpath, full_path=False):
        """lists all current drectories in directory"""
        dirlist = []
        if os.path.exists(searchpath):
            if not full_path:
                dirlist = [f.name for f in os.scandir(searchpath) if f.is_dir()]
            else:
                dirlist = [f.path for f in os.scandir(searchpath) if f.is_dir()]
        return dirlist

    @staticmethod
    def _remove_dir(jobpath):
        if not os.path.exists(jobpath):
            print("Warning: Job directory does not exist.")
        else:
            try:
                shutil.rmtree(jobpath)
            except FileNotFoundError:
                print("Warning: Directory can not be deleted.")

    ###########################################################################
    # Functions for jobs by name
    ###########################################################################

    def _get_free_bash_index(self):
        """sarches for highest number of submitted .sh in main directory"""
        # Find bashs
        list_bsh = self._get_file_list(self.dirmain, ending=".sh")
        max_num = 0
        for x in list_bsh:
            x = x.replace(".sh", "")
            x = x.split('_')
            if len(x) > 1:
                max_num = max(int(x[-1]), max_num)
        return max_num + 1

    def _clean_jobname(self, name):
        """ clean the jobname from unwanted chars"""
        bad_chars = r"[-()\"#/@;:<>{}`+=~|.!?,]"
        former = int(len(name))
        for x in bad_chars:
            name = name.replace(x, "")
        name = name.replace(" ", "")
        if int(len(name)) != former:
            print("Warning: Invalid dir name, replaced by", name)
        return name

    ###########################################################################
    # Public
    ###########################################################################

    def save(self):
        self._write_json_to_file(self.jobinfo, os.path.join(self.dirmain, self.jobinfo_name))

    def load(self, add_existing=False):
        if os.path.exists(os.path.join(self.dirmain, self.jobinfo_name)):
            self.jobinfo = self._read_json_from_file(os.path.join(self.dirmain, self.jobinfo_name))
        for key, value in self.jobinfo.items():
            if os.path.abspath(os.path.dirname(value['path'])) != self.dirmain:
                print("Error: Loaded of data has wrong path.", key)
        alljobs = list(self.jobinfo.keys())
        alljobs_dir = self._get_directory_list(self.dirmain)
        if add_existing:
            found_dirs = False
            for x in alljobs_dir:
                if x not in alljobs:
                    self.add(x)
                    found_dirs = True
            if found_dirs:
                print("Warning: Additional directories found. Adding directories...")

    def add(self, job):
        """
        Main function to add job plus e.g. command. Command is updated if job already exists.
        Adding a job means creating a file directory. Commands are stored in dictionaries.
        
        Args:
            job (str,list,dict): Job names to be created. Either single string or list of strings
            
        Return:
            pathlist (dict): Path to the created file directories (string or list)
        """
        pathlist = {}
        if isinstance(job, str):
            job = self._clean_jobname(job)
            jobpath = os.path.join(self.dirmain, job)
            is_folder = os.path.exists(jobpath)
            is_jobentry = job in self.jobinfo
            if not is_folder:
                os.mkdir(jobpath)
            if is_jobentry:
                self.jobinfo[job].update({"path": str(jobpath)})  # ,  "modified" : str(datetime.datetime.now())
            else:
                self.jobinfo[job] = {"path": str(jobpath)}  # , "created" : str(datetime.datetime.now())
            pathlist.update({job: self.jobinfo[job]})
        if isinstance(job, list):
            for i in range(0, len(job)):
                i_job = self._clean_jobname(job[i])
                jobpath = os.path.join(self.dirmain, i_job)
                is_folder = os.path.exists(jobpath)
                is_jobentry = i_job in self.jobinfo
                if not is_folder:
                    os.mkdir(jobpath)
                if is_jobentry and is_folder:
                    self.jobinfo[i_job].update({"path": str(jobpath)})
                else:
                    self.jobinfo[i_job] = {"path": str(jobpath)}
                pathlist.update({i_job: self.jobinfo[i_job]})
        if isinstance(job, dict):
            for key, value in job.items():
                i_job = self._clean_jobname(key)
                jobpath = os.path.join(self.dirmain, i_job)
                is_folder = os.path.exists(jobpath)
                is_jobentry = i_job in self.jobinfo
                if not is_folder:
                    os.mkdir(jobpath)
                jobaddinfo = {}
                jobaddinfo.update(value)
                if is_jobentry and is_folder:
                    jobaddinfo.update({"path": str(jobpath)})
                    self.jobinfo[i_job].update(jobaddinfo)
                else:
                    jobaddinfo.update({"path": str(jobpath)})
                    self.jobinfo[i_job] = jobaddinfo
                pathlist.update({i_job: self.jobinfo[i_job]})

        return pathlist

    def get(self, jobs=0, add_existing=False):
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
        if add_existing:
            alljobs_dir = self._get_directory_list(self.dirmain)
            found_dirs = False
            for x in alljobs_dir:
                if x not in alljobs:
                    self.add(x)
                    found_dirs = True
            if found_dirs:
                print("Warning: Additional directories found. Adding directories...")
            alljobs = list(self.jobinfo.keys())
        joblist = {}
        if isinstance(jobs, int):
            return {x: self.jobinfo[x] for x in alljobs[jobs:]}
        if isinstance(jobs, str):
            if jobs in alljobs:
                return {jobs: self.jobinfo[jobs]}
            else:
                print("Warning: job not found.")
        if isinstance(jobs, dict):
            jobs = list(jobs.keys())
        if isinstance(jobs, list):
            joblist = {x: self.jobinfo[x] for x in jobs if x in alljobs}
            if len(joblist) < len(jobs):
                print("Warning: Not all jobs exist, missing", len(joblist) - len(jobs))

        return joblist

    def remove(self, jobs=0):
        """
        Remove jobdict from list of jobs, but does NOT delete physical directory.
        
        Args:
            jobs (str,int,list): Job names to get path for. Can be single string, list of names or int.
                                 If (int) the index of all available jobs is taken: joblist[jobs:]
                                 jobs = 0 means all jobs
                                 jobs = -1 means last job in directory list (sorted by name?)
                                 
        Returns:
            None
        """
        jobs_to_remove = list(self.get(jobs).keys())

        for x in jobs_to_remove:
            self.jobinfo.pop(x)

    def run(self, jobs=0, procs=1, asyn=0,
            header="",
            command="",
            command_arguments=['path'],
            queue_properties={},
            submit_properties={},
            prepare_only=False):
        """Main function to start e.g. slurm arrays from jobs. The command is taken from the command 
        dictionary if not None and has preference over the command given in function call.
        
        Args:
            jobs (str,list,int): Job names to run. Can be single string, list of names or int.
                                 If (int) the index of all available jobs is taken: joblist[jobs:]
                                 jobs = 0 means all jobs
                                 jobs = -1 means last job in directory list (sorted by name?)
            procs (int): Number of bash scripts to start.            
            asyn (int): Number of asynchronous commands to start.
            header (str): Header for queueing system that is written to bash script.
            command (str):  Default command to run if no command is specified. 
            command_arguments (list): Arguments that can be formatted into command.
                                      Default include {path} variable for the command string.
            queue_properties (dict): Queue specific parameters for scripts. Default is {}.
                                     Each queue system will enter default values.
            submit_properties (dict): Queue specific parameters for submission. Default is {}.
                                        Like {'-p',"partition"}
            prepare_only (bool): Whether to only make scripts etc. but not acutally run them.
        
        Returns:
            queue_ids (list): The ruturn e.g. ids of the submission call
        """
        # Get Paths
        sub_jobs = self.get(jobs)
        sub_keys = list(sub_jobs.keys())
        sub_cmd = [sub_jobs[x]['command'] if 'command' in sub_jobs[x] else command for x in sub_keys]
        sub_path = [{y: sub_jobs[x][y] for y in command_arguments if y in sub_jobs[x]} for x in sub_keys]

        # Get job array size
        len_jobs = len(sub_keys)
        num_procs = min(len_jobs, procs)
        len_per_array = len_jobs // num_procs + (len_jobs % num_procs > 0)

        # Submit slurms
        id_list = []
        for i in range(0, len_jobs, len_per_array):
            num = self._get_free_bash_index()
            bash_submit = "%s_%i.sh" % (self.dirname, num)
            if self.submit_type == "SLURM":
                make_slurm_script(self.dirmain, bash_submit, asyn,
                                  sub_keys[i:i + len_per_array],
                                  sub_path[i:i + len_per_array],
                                  sub_cmd[i:i + len_per_array],
                                  header=header,
                                  slurm_variables=queue_properties
                                  )
            if not prepare_only:
                if self.submit_type == "SLURM":
                    id_sub = make_slurm_sub(self.dirmain, bash_submit,
                                            submit_properties)
                    id_list.append(id_sub)
                    # submits
        return id_list

    def queue(self, print_level=2):
        """ 
        Function to check queueing system. Should be quite unique for this directory and safely get jobs. 

        Args:
            print_level (int): print information, high-level more printing, 0 means no print
        
        Returns:
            list_ids,list_scripts (tuple): list of ids, running scripts
        """
        # Check slurm
        list_ids = []
        list_scripts = []
        if self.submit_type == "SLURM":
            list_ids, list_scripts = make_slurm_queue(self.dirmain, print_level=print_level)

        return list_ids, list_scripts

    def cancel(self, ids=[]):
        """ 
        Rudimental function to cancel queueing by id.
        
        Args:
            ids (str,list): queue ids to cancel. Can be single string, list of ids or int.
        
        """
        if isinstance(ids, str):
            ids = [ids]
        if self.submit_type == "SLURM":
            for x in ids:
                _ = subprocess.run(['scancel', x], capture_output=True)
