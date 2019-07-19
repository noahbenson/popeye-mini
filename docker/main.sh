#! /bin/bash
#
# This script is run inside the neuropythy docker and simply invokes neuropythy's main function.
# By Noah C. Benson

set -eo pipefail

function die {
    echo "$@"
    exit 1
}

[ -d /input ]  || die "No /input directory found!\nThe /input directory must contain test nifti files."

if [ "$1" = "bash" ]
then exec /bin/bash
elif [ "$1" = "python" ]
then exec python3
elif [ "$1" = "solve" ] || [ -z "$1" ]
then python /main.py #&> /input/log.txt
else echo "Unrecognized command: $1"
     exit 1
fi

