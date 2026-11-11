#!/usr/bin/env bash
# audit.sh: list the configs in a folder that have no "ntp server" line.
#
#   scripts/audit.sh DIR
#
# For every .cfg file in DIR (names can have spaces in them), print its name if no line in it starts with
# "ntp server". Other files are left alone. Exit 1 if it printed any, 0 if every config was fine (an empty
# folder is fine). With no DIR, or a DIR that isn't a folder, print a usage line on stderr and exit 2.
# Task 7.2: https://networkdoodles.com/labs/linux-cli-101/task-7-2/

# TODO 7.2: write it.
echo "TODO 7.2 is still open" >&2
exit 3
