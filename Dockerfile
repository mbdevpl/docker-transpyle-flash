FROM mbdevpl/transpyle:ubuntu16.04

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

USER user

#
# FLASH subset
#

RUN ln -s /home/user/Projects/transpyle-flash/flash-subset /home/user/Projects/flash-subset

#WORKDIR /home/user/Projects/flash-subset
WORKDIR /home/user/Projects/flash-subset/FLASH4.4
RUN bash /home/user/Projects/transpyle-flash/setup_flash.sh

RUN ./setup HydroStatic --auto +unsplitHydro

WORKDIR /home/user/Projects/flash-subset/FLASH4.4/object

#RUN sed -i  's|lrefine_max                    = 5|lrefine_max                    = 2|' flash.par
#RUN make

#
# FLASH tools
#

#WORKDIR /home/user/Projects/flash/tools
#WORKDIR /home/user/Projects/flash-subset/FLASH4.4/tools

#RUN python2.7 setup.py
#RUN sed -i  's|yt.data_objects.field_info_container|yt.fields.field_info_container|' python/yt_derived_fields.py

#
#
#

# docker build -t transpyle .
# docker run -it transpyle
