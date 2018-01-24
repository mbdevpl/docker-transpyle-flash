#!/bin/bash

sed -i  's|/usr/local/mpich2/|/usr|' sites/Prototypes/Linux/Makefile.h
sed -i  's|/usr/local/hdf5|/usr|' sites/Prototypes/Linux/Makefile.h
sed -i  's|${HDF5_PATH}/include |${HDF5_PATH}/include/hdf5/openmpi |' sites/Prototypes/Linux/Makefile.h
