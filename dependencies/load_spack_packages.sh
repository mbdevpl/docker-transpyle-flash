#!/bin/bash
set -Eeuxo pipefail

spack load -r mpich
spack load -r hdf5
spack load -r hypre
spack load -r superlu
spack load -r amrex
spack load -r hpctoolkit@master
