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
Then create "jobs" (which are empty subdirectories)

```python
maindir.add("Calc_1",command=None)
```
Create Input via own custom functions using libraries like ase or pymatgen.

```python
def write_input(filepath ):
    # Do something
    return 0
	
write_input( maindir.get("Calc_1") )
```
And then run list of jobs or all subdirectries with run():

```python
maindir.run(procs=5,command="#Do a bash command here\n")
```
