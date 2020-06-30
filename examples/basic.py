"""
Basic example of possible usage
@author: Patrick Reiser
"""

from mjdir.MultiJobDirectory import MultiJobDirectory
import os

#Example for basic usage
jobdir = MultiJobDirectory("TestJobs")

# Adding jobdirectories
jobdir.add("job_1",command = 'echo "simple job" > test.txt\n') # if command is not None, this command will be used in run()
jobdir.add(["job_2","job_3","job_4","job_5"])
#jobdir.remove("job_3")

# Get path of jobdirectory
print("Path of job 2:",jobdir.get("job_2",full_path=True))

#Typical input generation
def fun_write_input_example(path):
    with open(os.path.join(path,"inputfile.txt"),"w") as f:
        f.write("atom here")
#Write input
fun_write_input_example(jobdir.get("job_1"))

#Ddefine slurm settings
jobdir.slurm_header = "cd $SLURM_SUBMIT_DIR\n#module load something\n"
jobdir.slurm_tasks = "2"
jobdir.slurm_time = "30:00:00"
#jobdir.slurm_partition = 'normal'  # For for-hlr need partition to run slurm

#Submit jobs for array, procs = 2 number of jobs to submit
submits = jobdir.run(procs=2,command='echo "default command" > test.txt\n',scripts_only=False,ignore_running=True) # jobs=0 means all
print("Slurm submitted:",submits)

#Check for running jobs
runjobs = jobdir.check(check_logs = False)
print("Jobs running: ",runjobs)

#Copy file from jobdir, will be done by public function in the future
jobdir._copy_files_from_dir(jobdir.get("job_1"),".",".txt")

#Wait/check for a specific job to finish
jobdir.wait(updates=0.2)
runjobs = jobdir.check(check_logs = True)
print("Jobs running: ",runjobs)

#Read output via custom function
def fun_test_success(path):
    out = "Error"
    filepath = os.path.join(path,"test.txt")
    if(os.path.exists(filepath)):
        with open(filepath,"r") as f:
            out= f.read().strip()
            return out
    else:
        return out
    
#Use get() or by evaluate(function)
print("Readout: ",jobdir.evaluate(fun_test_success))
