FROM mbdevpl/transpyle:0.5.1

MAINTAINER Mateusz Bysiek <mateusz.bysiek.spam@gmail.com>

USER user
WORKDIR /home/user

RUN mkdir -p Projects && \
  git clone https://github.com/mbdevpl/spack.git --branch amrex_no_cmake_yes_configure --depth 1 Spack && \
  echo "source /home/user/Spack/share/spack/setup-env.sh" >> /home/user/.profile

COPY --chown=user:user . /home/user/Projects/transpyle-flash-dependencies

RUN spack install mpich@3.2.1 && \
  spack install --no-checksum hdf5@1.8.20 +cxx +fortran +hl +mpi +szip +threadsafe ^mpich && \
  spack install --no-checksum hypre@2.14.0 +mpi ^mpich ^openblas@0.3.2 threads=openmp && \
  echo "spack load -r mpich && spack load -r hdf5 && spack load -r hypre" >> /home/user/.bash_history && \
  spack install amrex@develop dimensions=2 ~openmp +fortran +particles +mpi ^mpich && \
  echo "spack load -r mpich && spack load -r hdf5 && spack load -r hypre && spack load -r amrex" >> /home/user/.bash_history

#   && \
#  spack install hpctoolkit@master +mpi ^mpich && \
#  echo "spack load -r hpctoolkit@master" >> /home/user/.bash_history
