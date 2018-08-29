FROM mbdevpl/transpyle-flash:dependencies-latest

MAINTAINER Mateusz Bysiek <mateusz.bysiek.spam@gmail.com>

COPY --chown=user:user . /home/user/Projects/transpyle-flash

USER user
WORKDIR /home/user/Projects/transpyle-flash

RUN cat bash_history_user.sh >> /home/user/.bash_history && \
  ln -s /home/user/Projects/transpyle-flash/flash-subset /home/user/Projects/flash-subset && \
  ln -s /home/user/Projects/transpyle-flash/flash-4.4 /home/user/Projects/flash-4.4 && \
  ln -s /home/user/Projects/transpyle-flash/flash-4.5 /home/user/Projects/flash-4.5
