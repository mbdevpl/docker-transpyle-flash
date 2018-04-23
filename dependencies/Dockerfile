FROM mbdevpl/transpyle:0.4.0

MAINTAINER Mateusz Bysiek <mateusz.bysiek.spam@gmail.com>

SHELL ["/bin/bash", "--login", "-c"]

COPY --chown=user:user . /home/user/Projects/transpyle-flash-dependencies

#
# modules
#

USER root

RUN apt install -y environment-modules

# RUN source /etc/profile

#
# spack
#

USER user

WORKDIR /home/user

RUN git clone https://github.com/spack/spack.git Spack

RUN echo "source /home/user/Spack/share/spack/setup-env.sh" >> /home/user/.profile

WORKDIR /home/user/Projects/transpyle-flash-dependencies

RUN bash install_spack_packages.sh

#
# amrex
#

RUN bash install_amrex.sh

#WORKDIR /home/user/Projects

#RUN git clone https://github.com/AMReX-Codes/amrex
#WORKDIR /home/user/Projects/amrex

#RUN git checkout development
#RUN ./configure --dim 2 --with-mpi yes --with-omp yes --debug yes
#RUN make
#RUN make install
