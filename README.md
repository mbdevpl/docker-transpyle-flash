# Docker container: Transpyle + FLASH


## Recommended knowledge

User must know how to use [FLASH](http://flash.uchicago.edu/site/flashcode/).

Familiarity at elementary level with the following will help:

* docker command-line interface
* `screen` linux command
* python
* jupyter notebook


## How to use


### Build the container image

On the host, go to the root directory of this repository, and, first of all, update git submodules
with FLASH if necessary, as they will be copied into the image:

    git submodule update --init
    git submodule update --remote flash-subset

This requires access to FLASH repositories.

Then, make sure that images on which building this image depends, are also up to date:

    sudo docker pull mbdevpl/usable-ubuntu:16.04
    sudo docker pull mbdevpl/usable-python:ubuntu16.04
    sudo docker pull mbdevpl/transpyle:0.3.1

If you any modifications were made to submodules, you can revert them using:

    git submodule foreach git clean -f -d -x
    git submodule foreach git reset --hard HEAD

Then, build the image by running the following:

    sudo docker build --no-cache -t transpyle-flash .


### Run the container

On the host, execute the following:

    sudo docker run -h transmachine -it transpyle-flash


### Run FLASH in the container

In the container, go to the directory containing FLASH, then set up and run the simulation.
Some examples of how to do this are in file [`flash_setup_examples.sh`](flash_setup_examples.sh).

You can, for example, run that file:

    ./flash_setup_examples.sh

Or, the following will pick up and test functions from [`test_flash.py`](test_flash.py):

    python3 -m unittest discover --verbose
    python3 -m unittest test_flash.Flash45Tests.test_eos_idealGamma


### Transpile FLASH in the container

In the container, do the following:

    cd ~/Projects/transpyle-flash
    screen -S "TranspyleNotebook" python3 -m jupyter notebook --ip=$(hostname -i) --port=8080

Then, point your host browser to the address of the notebook which should be printed in the terminal.
After that, you can detach from the notebook's screen in the container (using `Ctrl+A+D`).
If at any time you want to return to the notebook console, type `screen -r TranspyleNotebook`.

In your host's browser, you should see jupyter notebook index page `http://container-ip:8080/tree`.
Open [`transpyle_flash.ipynb`](transpyle_flash.ipynb). To test default transpilation scenario,
execute all cells in the notebook.

After transpilation is finihsed, you can setup, build and run FLASH again to test it.


### Transpile host's FLASH from the container

You can also mount a directory with FLASH (or other Fortran code) into the container from your host,
via `--mount` comandline option of `docker run`. So instead of initial command, execute for example:

    sudo docker run -h transmachine --mount src=~/my-flash,target=/home/user/Projects/my-flash,type=bind -it transpyle-flash

That way the container is used only for transpilation, but building and execution of FLASH
can be done on pre-configured host.

Remark: when mounting, the mounted folder is owned by root within the container - and changing it's
ownership breaks ownership of files in the host system. Therefore it's best to mount files from
host with read-only intentions. See: https://github.com/moby/moby/issues/2259
