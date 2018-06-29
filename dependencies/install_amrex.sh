#!/bin/bash
set -Eeuxo pipefail

cd ~/Projects

git clone https://github.com/AMReX-Codes/amrex
cd ~/Projects/amrex

git checkout development

spack load mpich@3.2.1

for debug in "no" "yes"
do
  for mpi in "yes" "no"
  do
    for omp in "yes" "no"
    do
      for dim in "2" "3"
      do
        prefix="${HOME}/Software/AMReX_${dim}d"
        if [ ${mpi} == "no" ] ; then
          prefix="${prefix}_nompi"
        fi
        if [ ${omp} == "no" ] ; then
          prefix="${prefix}_noomp"
        fi
        if [ ${debug} == "yes" ] ; then
          prefix="${prefix}_debug"
        fi
        # echo "${prefix}"
        ./configure --dim ${dim} --with-mpi ${mpi} --with-omp ${omp} --debug ${debug} --prefix ${prefix}
        make
        make install
        make clean
      done
    done
  done
done
