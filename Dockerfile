FROM mbdevpl/transpyle:0.4.0

MAINTAINER Mateusz Bysiek <mateusz.bysiek.spam@gmail.com>

#
#
#

COPY --chown=user:user . /home/user/Projects/transpyle-flash

#
#
#

USER root

WORKDIR /usr/lib/x86_64-linux-gnu/
RUN ln -s libhdf5_openmpi.so libhdf5.so
RUN ln -s libhdf5_openmpi_hl.so libhdf5_hl.so
WORKDIR /root
RUN git clone https://github.com/AMReX-Codes/amrex
WORKDIR /root/amrex
RUN git checkout development
RUN ./configure --dim=2 --debug=yes --with-mpi=no --prefix=/usr
RUN make
RUN make install

USER user

#
# FLASH subset
#

RUN ln -s /home/user/Projects/transpyle-flash/flash-subset /home/user/Projects/flash-subset

#
# FLASH 4.4
#

RUN ln -s /home/user/Projects/transpyle-flash/flash-4.4 /home/user/Projects/flash-4.4

#
# FLASH 4.5
#

RUN ln -s /home/user/Projects/transpyle-flash/flash-4.5 /home/user/Projects/flash-4.5

#
#
#

WORKDIR /home/user/Projects/transpyle-flash

# docker build -t transpyle .
# docker run -it transpyle
