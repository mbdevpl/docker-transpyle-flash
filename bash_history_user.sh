spack load mpich@3.2.1 hdf5@1.8.19 openblas@0.2.20 hypre@2.13.0
./setup --help
./setup Sod -auto -2d -site spack
./setup Sod -auto -2d +Mode1 -site spack
./setup Sod -auto -2d +Mode3 -site spack
cd object
make
mpirun -np 1 ./flash4
mpirun -np 2 ./flash4
