# Multiple Job Directory

Python class to manage job directories and submit batch jobs.

# Table of Contents
* [General](#general)
* [Installation](#installation)
* [Examples](#examples)
* [Usage](#usage)
 

<a name="general"></a>
# General
The concept of this pyhton class is to have a neat interface to manage a folder with multiple jobdirectories.
Having a managed directory, jobs can be submitted from via a queueing system like slurm.
The goal is to be able to submit array-jobs via python, providing functions like run for this jobdirectory.
In [commands](mjdir/commands), modules should be collected that are used to generate and read input for specific task and programs.
The main class is sought to have as little dependencies as possible, ideally none.
The directory management should be os-independent. 
A documentation can be found in [docs](docs).

<a name="installation"></a>
# Installation

Clone repository and install for example with editable mode:

```bash
pip install -e ./jobdir_queue_submit
```
<a name="examples"></a>
# Examples

A set of examples can be found in [examples](examples), that demonstrate usage and typical tasks for projects.

<a name="usage"></a>
# Usage

The basic idea of the interface is as follows: Create or load the main directory.

```python
from mjdir.MultiJobDirectory import MultiJobDirectory
maindir = MultiJobDirectory("Name","filepath")
```
Then create multiple "jobs", which are empty subdirectories automatically created.

```python
maindir.add("Calc_1")
maindir.add(["Calc_2","Calc_3"])
maindir.add({"Calc_4": {"command": 'echo "{path}" '} })
```
Get the current path list and information of all available directories via get() or for a specific sublist.

```python
maindir.get()  # list all
maindir.get("Calc_1")
```
The class python dict holds a job plus path and additional information. You can delete entries via
However, they physical subdirectories are not deleted.

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
The path can be obtained by get(). Some functions are found in [commands](mjdir/commands).

```python
def write_input(filepath ):
    # Do something
    return 0
	
write_input( maindir.get()["Calc_1"]['path'] )
```
Modify and adjust queue settings. 
```python

```

And then run list of jobs or all subdirectries with run():

```python
maindir.run(procs=5,command="#Do a bash command here\n")
```
