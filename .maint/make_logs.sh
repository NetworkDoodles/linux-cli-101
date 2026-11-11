#!/usr/bin/env bash
# Maintainers: record files/logs/r1.log, the practice log, from the running lab. Run it as root in the dev
# container, with sshpass installed, right after make reset:
#   bash .maint/make_logs.sh > files/logs/r1.log
# OpenSSH 9.8+ penalises a source address after failed logins (PerSourcePenalties), so failures are spaced out.
# CapeOS 0.11.0 logs LOGIN_FAILED only for user names it doesn't know (a wrong password for admin shows up in
# sshd's own log as a PAM error, not in the router's log), so the failures here use unknown names.
set -u
R="docker exec -i r1 capeos-cli"
cfg() { printf 'configure terminal\n%s\nend\n' "$1" | $R >/dev/null; }
fail() { sshpass -p "$2" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o PubkeyAuthentication=no \
         -o ConnectTimeout=5 "$1@172.80.102.2" exit >/dev/null 2>&1; sleep 8; }
ok() { sshpass -p capeos-lab ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o PubkeyAuthentication=no \
       admin@172.80.102.2 "show clock" >/dev/null 2>&1; sleep 1; }
flap() { cfg "interface $1"$'\n shutdown'; sleep 2; cfg "interface $1"$'\n no shutdown'; sleep 3; }
ok
flap GigabitEthernet2
fail guest guest
fail netops netops
flap GigabitEthernet1
fail netops Netops1
fail support support
ok
flap GigabitEthernet2
fail guest 123456
fail netops netops-lab
fail operator operator
flap GigabitEthernet2
fail support changeme
ok
cfg $'interface GigabitEthernet2\n description srv1 network'
sleep 1
docker exec -i r1 capeos-cli -c "show logging" | sed -n '/^\*/p'
