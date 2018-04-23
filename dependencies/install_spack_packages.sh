#!/bin/bash
set -Eeuxo pipefail

#PS1=""
#source ${HOME}/.profile
#source /etc/profile  # for module command
#source "/home/user/Spack/share/spack/setup-env.sh"

#
# spack packages
#

# RUN spack install hpctoolkit

#
# FLASH dependencies
#

# MPI

spack install mpich@3.2.1
spack load mpich@3.2.1

# HDF5

spack install hdf5@1.8.19 +fortran +hl +mpi ^mpich@3.2.1
spack load hdf5@1.8.19

# hypre

spack install openblas@0.2.20 threads=openmp
spack load openblas@0.2.20

spack install hypre@2.13.0 +mpi ^mpich@3.2.1 ^openblas@0.2.20 threads=openmp
spack load hypre@2.13.0

# amrex

# RUN spack install amrex@develop dims=2 +debug +mpi ^mpich
# RUN spack load amrex@develop
