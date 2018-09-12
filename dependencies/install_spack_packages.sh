#!/bin/bash
set -Eeuxo pipefail

#
# FLASH dependencies
#

spack install mpich@3.2.1
spack install --no-checksum hdf5@1.8.20 +cxx +fortran +hl +mpi +szip +threadsafe ^mpich
spack install --no-checksum hypre@2.14.0 +mpi ^mpich ^openblas@0.3.2 threads=openmp
spack install --no-checksum superlu@5.2.1 +pic ^openblas@0.3.2 threads=openmp
spack install amrex@develop dimensions=2 ~openmp +fortran +particles +mpi ^mpich

#
# other spack packages
#

#spack install hpctoolkit@master +mpi ^mpich
