#!/usr/bin/env bash

# to be invoked by cron

# make callable from anywhere
cd "$( dirname "${BASH_SOURCE[0]}" )" || exit

# check if a screen session with name "tbot_image_snow" exists,
# if not, create it

echo $RANDOM > /dev/null
if ! screen -list | grep -q "tbot_image_snow"; then
    # sleep random amount between 0.1 and 0.9 seconds
    sleep "$(echo "$(shuf -i 1000-9000 -n 1)/10000" | bc -l)"
else
    exit 1
fi


if ! screen -list | grep -q "tbot_image_snow"; then
    screen -dm -S tbot_image_snow /usr/bin/zsh -c "./main.py"
fi


if screen -list | grep "tbot_image_snow" | grep -q "Dead"; then
    screen -wipe
fi
