#!/bin/bash

# this file demonstrates one problem setup per FLASH version

#
# FLASH subset
#

cd ~/Projects/flash-subset/FLASH4.4

./setup Sod -auto -2d +Mode3 -site spack

cd object

make
mpirun -np 1 ./flash4

#
# FLASH 4.4
#

cd ~/Projects/flash-4.4

./setup Sod -auto -2d -site spack

cd object

make
mpirun -np 2 ./flash4

#
# FLASH 4.5
#

cd ~/Projects/flash-4.5

./setup Sod -auto -2d -site spack

cd object

make
mpirun -np 2 ./flash4
