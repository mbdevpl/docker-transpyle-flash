FROM mbdevpl/transpyle:0.5.0

MAINTAINER Mateusz Bysiek <mateusz.bysiek.spam@gmail.com>

COPY --chown=user:user . /home/user/Projects/transpyle-flash-dependencies

#
# spack
#

USER user

WORKDIR /home/user

RUN git clone https://github.com/spack/spack.git Spack

RUN echo "source /home/user/Spack/share/spack/setup-env.sh" >> /home/user/.profile

WORKDIR /home/user/Projects/transpyle-flash-dependencies

#
# spack packages
#

RUN bash install_spack_packages.sh

#
# amrex
#

RUN spack load mpich@3.2.1 && bash install_amrex.sh
