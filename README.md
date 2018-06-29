# Docker container: Transpyle + FLASH


## Recommended knowledge

User must know how to use [FLASH](http://flash.uchicago.edu/site/flashcode/).

Familiarity at elementary level with the following will help:

* docker command-line interface
* Spack package manager
* `screen` linux command
* python
* jupyter notebook


## Using the Docker container


### Building the images

Rebuilding images is only necessary when:

* FLASH is updated (then, rebuild the main container image)
* dependencies are updated (then, rebuild the dependencies image and the main container image)
* transpyle framework is updated (changes in the [`Dockerfile`](dependencies/Dockerfile#L1)
  of the dependencies image plus rebuild of all of the above is required)


#### Rebuild the main container image

On the host, go to the root directory of this repository, and, first of all, update git submodules
with FLASH if necessary, as they will be copied into the image:

    git submodule update --init --remote

This requires access to FLASH repositories.

If you any modifications were made to submodules, you can revert them using:

    git submodule foreach git clean -f -d -x
    git submodule foreach git reset --hard HEAD

Then, build the image by running the following:

    sudo docker build --pull --no-cache -t mbdevpl/transpyle-flash:build-$(date +"%Y-%m-%d") .
    sudo docker push mbdevpl/transpyle-flash:build-$(date +"%Y-%m-%d")

    sudo docker tag mbdevpl/transpyle-flash:{build-$(date +"%Y-%m-%d"),latest}
    sudo docker push mbdevpl/transpyle-flash:latest

The, `--pull` option makes sure that image on which building this container depends, is also up to date.


#### Rebuilding the dependencies image

Normally you wouldn't need to do this, but if you want to update the dependencies image:

    cd dependencies
    sudo docker build --pull --no-cache -t mbdevpl/transpyle-flash:dependencies-$(date +"%Y-%m-%d") .
    sudo docker push mbdevpl/transpyle-flash:dependencies-$(date +"%Y-%m-%d")

And after that please update the 1st line of the main [`Dockerfile`](Dockerfile#L1) to mention
the latest dependencies image.


### Run the container

On the host, execute the following:

    sudo docker run -h transmachine -it transpyle-flash


## Using FLASH within the container


### Load Spack modules

We rely on Spack for FLASH dependencies. They have been already installed,
but necessary modules need to be loaded after starting the container.

For FLASH 4.4, 4.5 as well as FLASH subset:

    spack load mpich@3.2.1 hdf5@1.8.19 openblas@0.2.20 hypre@2.13.0

Additionally, FLASH subset depends on AMReX, which was also installed but outside of Spack due to
configuration issues with the version provided via Spack.


### Run FLASH in the container

In the container, go to the directory containing FLASH, then set up and run the simulation.
Some examples of how to do this are in file [`flash_setup_examples.sh`](flash_setup_examples.sh).

You can, for example, run that file:

    ./flash_setup_examples.sh

Or, the following will pick up and test functions from [`test_flash.py`](test_flash.py):

    python3 -m unittest discover --verbose
    python3 -m unittest test_flash.Flash45Tests.test_eos_idealGamma
    python3 -m unittest test_flash.Flash45Tests.test_hy_8wv_sweep
    python3 -m unittest test_flash.FlashSubsetTests


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
