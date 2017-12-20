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

On the host, go to the root directory of this repository, and, first of all, update git submodule
with FLASH if necessary, as it will be copied into the image:

    git submodule update --remote

This requires access to FLASH repository.

Then, build the image by running the following:

    sudo docker build --no-cache -t transpyle-flash .


### Run the container

On the host, execute the following:

    sudo docker run -h transmachine -it transpyle-flash


### Run FLASH in the container

In the container, go to the directory contianing FLASH and build and run the simulation:

    cd ~/Projects/flash-subset/FLASH4.4/
    ./setup HydroStatic --auto +unsplitHydro
    cd object/
    make
    mpirun -np 2 flash4


### Transpile FLASH in the container

Then, in the container:

    cd ~/Projects/transpyle-flash
    screen -S "TranspyleNotebook" python3 -m jupyter notebook --ip=$(hostname -i) --port=8080

Then, point your host browser to the address of the notebook which should be printed in the terminal.
After that, you can detach from the notebook's screen in the container (using Ctrl+A+D).
If at any time you want to return to the notebook console, type `screen -r TranspyleNotebook`.

In your host's browser, you should see jupyter notebook index page `http://container-ip:8080/tree`.
Open `transpyle_flash.ipynb`. To test default transpilation scenario, execute all cells in the notebook.

After transpilation is finihsed, you can setup, build and run FLASH again to test it.


### Transpile host's FLASH from the container

You can also mount a directory with FLASH (or other Fortran code) into the container from your host,
via `--mount` comandline option of `docker run`. So instead of initial command, execute for example:

    sudo docker run -h transmachine --mount src=~/my-flash,target=/home/user/Projects/my-flash,type=bind -it mbdevpl/transpyle-flash

That way the container is used only for transpilation, but building and execution of FLASH
can be done on pre-configured host.
