#!/usr/bin/env bash
# reach.sh: ping every host in a list, say which ones answer, and fail if any of them doesn't.
#
#   scripts/reach.sh [FILE]     FILE has one host per line; without one, it reads hosts.txt
#
# It prints one line per host, "ws1 up" or "ws1 down", and exits 0 if every host answered, 1 if not.
# Task 7.1: https://networkdoodles.com/labs/linux-cli-101/task-7-1/

file="${1:-hosts.txt}"        # the first argument, or hosts.txt if there isn't one
down=0                        # becomes 1 as soon as one host doesn't answer

while read -r host; do
  case "$host" in ""|"#"*) continue ;; esac      # skip blank lines and comments

  # TODO 7.1a: ping "$host" once (-c 1), waiting at most one second (-W 1), and throw its output away.
  #            If it answers, print "$host up". If it doesn't, print "$host down" and set down=1.
  echo "TODO 7.1a is still open: $host"

done < "$file"

# TODO 7.1b: finish with exit code $down, so that 0 means every host answered.
