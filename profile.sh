#!/usr/bin/env bash
set -Eeuxo pipefail

# resolved absolute path to where this script is located
HERE=$(dirname $(test -L "$BASH_SOURCE" && readlink -f "$BASH_SOURCE" || echo "$BASH_SOURCE"))

NOW_DATE=$(date +"%Y%m%d")
executable="./flash4"

samples="$1" # numer, e.g. 1, 10, 100

app="$2" # flash-subset
experiment="$3" # Sedov

if [ -n "$4" ] ; then
  source="$4/+"
else
  source="$HERE/${app}/+"
fi

sample=0
while [ ${sample} -le ${samples} ] ; do
  ((sample += 1))
  hpcrun -o "$HERE/results/profile_${NOW_DATE}_${app}_${experiment}" ${executable}
done

hpcstruct -I "${source}" -o "$HERE/results/profile_${NOW_DATE}_${app}_${experiment}/flash4.hpcstruct" ${executable}

hpcprof -I "${source}" "$HERE/results/profile_${NOW_DATE}_${app}_${experiment}" \
  -S "$HERE/results/profile_${NOW_DATE}_${app}_${experiment}/flash4.hpcstruct" \
  -M stats \
  -o "$HERE/results/profile_${NOW_DATE}_${app}_${experiment}_db"
