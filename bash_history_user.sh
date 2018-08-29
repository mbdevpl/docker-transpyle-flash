./setup --help
./setup Sod -auto -2d -site spack
./setup Sod -auto -2d +Mode1 -site spack
./setup Sod -auto -2d +Mode3 -site spack
cd object
make
./flash4
mpirun -np 1 ./flash4
mpirun -np 2 ./flash4
