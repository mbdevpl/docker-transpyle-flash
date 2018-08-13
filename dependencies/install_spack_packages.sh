#!/bin/bash
set -Eeuxo pipefail

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

spack install --no-checksum hdf5@1.8.20 +fortran +hl +mpi ^mpich@3.2.1
spack load hdf5@1.8.20

# hypre

spack install --no-checksum hypre@2.14.0 +mpi ^mpich@3.2.1 ^openblas@0.3.2 threads=openmp
spack load hypre@2.14.0

# amrex

# RUN spack install amrex@develop dims=2 +debug +mpi ^mpich
# RUN spack load amrex@develop
