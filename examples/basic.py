from mjdir.MultiJobDirectory import MultiJobDirectory
import os
import time

#Example for basic usage
jobdir = MultiJobDirectory("TestJobs")

# Adding jobdirectories
jobdir.add({"job_1" : {'command' : 'echo "simple job" > {path}/test.txt\n' , 'input' : "coord"}}) # if command is not None, this command will be used in run()
jobdir.add(["job_2","job_3","job_4","job_5"])


# Get path of jobdirectory
print("Path of job 1:",jobdir.get("job_1"))

#Typical input generation
def fun_write_input_example(path):
    with open(os.path.join(path,"inputfile.txt"),"w") as f:
        f.write("atom here")
#Write input
fun_write_input_example(jobdir.get()["job_1"]['path'])


submit_properties = {'-p':'normal'} # For for-hlr need partition to run slurm

#Submit jobs for array, procs = 2 number of jobs to submit
submits = jobdir.run(procs=2,
                     command='echo "default command" > {path}/test.txt\n',
                     header = "cd $SLURM_SUBMIT_DIR\n#module load something\n",
                     submit_properties = {}, # for int-nano
                     ) 
print("Slurm submitted:",submits)


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


print("Waiting 10s ...")
time.sleep(10)
    
#Use get() or by evaluate(function)
print(fun_test_success(jobdir.get()['job_1']['path']))
