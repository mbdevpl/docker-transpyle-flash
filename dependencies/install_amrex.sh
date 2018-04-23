#!/bin/bash
set -Eeuxo pipefail

cd ~/Projects

git clone https://github.com/AMReX-Codes/amrex
cd ~/Projects/amrex

git checkout development

spack load mpich@3.2.1

./configure --dim 2 --with-mpi no --with-omp yes --debug yes --prefix ~/Software/AMReX_2d_nompi_debug
make
make install

make clean

./configure --dim 2 --with-mpi no --with-omp yes --prefix ~/Software/AMReX_2d_nompi
make
make install

make clean

./configure --dim 2 --with-omp yes --debug yes --prefix ~/Software/AMReX_2d_debug
make
make install

make clean

./configure --dim 2 --with-omp yes --prefix ~/Software/AMReX_2d
make
make install

make clean

./configure --with-omp yes --debug yes --prefix ~/Software/AMReX_3d_debug
make
make install

make clean

./configure --with-omp yes --prefix ~/Software/AMReX_3d
make
make install

make clean
