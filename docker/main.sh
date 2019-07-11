#! /bin/bash
#
# This script is run inside the neuropythy docker and simply invokes neuropythy's main function.
# By Noah C. Benson

if [ "$1" = "bash" ]
then exec /bin/bash
elif [ "$1" = "pythong" ]
then exec python3
elif [ "$1" = "solve" ] || [ -z "$1" ]
then python /main.py
else echo "Unrecognized command: $1"
     exit 1
fi
