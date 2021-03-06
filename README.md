[![Documentation Status](https://readthedocs.org/projects/mjdir/badge/?version=latest)](https://mjdir.readthedocs.io/en/latest/?badge=latest)
[![PyPI version](https://badge.fury.io/py/mjdir.svg)](https://badge.fury.io/py/mjdir)
[![GitHub version](https://badge.fury.io/gh/aimat-lab%2Fjobdir_queue_submit.svg)](https://badge.fury.io/gh/aimat-lab%2Fjobdir_queue_submit)

# Multiple Job Directory

Python class to manage job directories and submit batch jobs.

# Table of Contents
* [General](#general)
* [Installation](#installation)
* [Documentation](#documentation)
* [Examples](#examples)
* [Usage](#usage)
* [Citing](#citing)
 

<a name="general"></a>
# General
The concept of this pyhton class is to have a neat interface to manage a folder with multiple jobdirectories.
Having a managed directory, jobs can be submitted from via a queueing system like slurm and distributed in folders.
The goal is to be able to submit array-jobs via python, providing the same interface as bash and queueing like slurm.
In [commands](mjdir/commands), modules should be collected that are used to generate and read input for specific task and programs.
The main class is sought to have as little dependencies as possible, ideally none.
The directory management should be os-independent, the submission is not. For the moment only slurm is supported. 
A [documentation](https://mjdir.readthedocs.io/en/latest/index.html) is generated in [docs](docs).

<a name="installation"></a>
# Installation

Clone repository https://github.com/aimat-lab/jobdir_queue_submit and install for example with editable mode:

```bash
pip install -e ./jobdir_queue_submit
```
or latest release via Python Package Index.
```bash
pip install mjdir
```

<a name="documentation"></a>
# Documentation

Auto-documentation generated at https://mjdir.readthedocs.io/en/latest/index.html.

<a name="examples"></a>
# Examples

A set of examples can be found in [examples](examples), that demonstrate usage and typical tasks for projects.

<a name="usage"></a>
# Usage

The basic idea of the interface is as follows: Create or load the physical main directory. Be careful and check where you place the main directory before generating a large number of jobs.

```python
from mjdir.MultiJobDirectory import MultiJobDirectory
maindir = MultiJobDirectory("Name","filepath")
```
Then create multiple "jobs", for which empty physical subdirectories are automatically created by the python class.

```python
maindir.add("Calc_1")
maindir.add(["Calc_2","Calc_3"])
maindir.add({"Calc_4": {"command": 'echo "{path}" '} })
```
Get the current path list and information of all available directories via `get()` or for a specific sublist.

```python
maindir.get()  # list all
maindir.get("Calc_1")
```
The class python dict holds a job plus path and additional information. You can delete entries via `remove()`. However, their physical subdirectories are not deleted!!

```python
maindir.remove()  # remove all
maindir.remove("Calc_1")
```
You can save and reload the python dict and also add existing directories that may not be in the pyhton dict if necessary.

```python
maindir.save() 
maindir.load()
maindir.load(add_existing=True)  # Can add all physical subdirectories without information
```
Create Input via own custom functions using libraries like ase or pymatgen that take a directory filepath as input.
The path can be obtained by `get()`. Some functions are found in [commands](mjdir/commands).

```python
def write_input(filepath ):
    # Do something
    return 0
	
write_input( maindir.get()["Calc_1"]['path'] )
```
Modify and adjust queue settings. 
```python
slurm_params = { 'tasks' : "10",
                # "ntasks-per-node" : "10",
                'time' : "30:00:00",
                'nodes' : "1"}
submit_properties = {'-p':'normal'}
```

And then run all jobs or a specific selection of available jobs with `run()`. Here you can specify a number of properties. Like default command as string, the number of submits the jobs are distributed on and how many commands should be started asynchronously within one submission. The asynchronous execution must be compatible with the program and the system to use on. For more information see [commands](mjdir/commands) and [queue](mjdir/queue). The command is a string representing a bash command which is formatted by arguments provided by `add()` and enabled by `command_arguments`. Path information is available by default. Finally a set of bash scripts are generated and submitted. To inspect the submission without running, use `prepare_only=True` and look into the main directory. 

```python
maindir.run(procs = 1,
	    asyn = 0,
            header="module purge",
            command= "# If not sepcified in add() use this",
            command_arguments = ['path'],
            queue_properties = slurm_params,
            submit_properties = submit_properties ,
            prepare_only = False)
```

<a name="citing"></a>
# Citing

If you want to cite the package, try this:

```
@Misc{,
    author = {Patrick Reiser},
    title = {Multiple Job Directory},
    year = {2020},
    publisher = {GitHub},
    journal = {GitHub Repository},
    howpublished = {\url{https://github.com/aimat-lab/jobdir_queue_submit}},
    url = "https://github.com/aimat-lab/jobdir_queue_submit"
}
```
