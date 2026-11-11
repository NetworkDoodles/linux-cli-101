#!/usr/bin/env bash
# Maintainers: every task, start to finish, the way the guide does it, then make check. Run it as vscode in a
# fresh dev container, from a fresh clone of main, with the lab up:
#   bash .maint/walkthrough.sh 2>&1 | tee /tmp/walkthrough.log
# What the guide does in an editor (nano, VS Code) is printf or sed here. Passwords the guide types are given
# through SSH_ASKPASS, and the host-key questions are answered with the fingerprint checks the guide asks for.
set -uo pipefail
cd "$(dirname "$0")/.."
step() { printf '\n\033[1m── %s\033[0m\n' "$*"; }
show() { printf '\033[2m$ %s\033[0m\n' "$*"; bash -c "$*"; }
check() { make -s check T="$1" | grep '╰─'; }
fill() { sed -i "s|^$2:.*|$2: $3|" "answers/$1.yml"; }
ASK=$(mktemp); printf '#!/bin/sh\necho "$LAB_PASSWORD"\n' > "$ASK"; chmod 700 "$ASK"
withpw() { LAB_PASSWORD="$1" SSH_ASKPASS="$ASK" SSH_ASKPASS_REQUIRE=force DISPLAY=:0 "${@:2}" </dev/null; }
export ASK; export -f withpw

step "1.1"
show 'pwd; echo ~; grep PRETTY /etc/os-release; ls -a files | head -4'
show 'ls --help | grep -- --human'
os=$(. /etc/os-release; echo "$PRETTY_NAME")
fill 1.1 home "$HOME"; fill 1.1 repo "$PWD"; fill 1.1 os "$os"; fill 1.1 hidden_file .lab-notes
fill 1.1 ls_sizes_option -h; fill 1.1 logs_folder /var/log
check 1.1

step "1.2"
show 'cd files/site/nyc/rack2 && pwd && cat ../README.txt && cd .. && pwd && cd ../../.. && pwd'
show 'cd files/site/nyc/rack1 && cat ../../chi/rack2/chi-leaf2.cfg | head -n 5'
fill 1.2 chi_leaf2_absolute "$PWD/files/site/chi/rack2/chi-leaf2.cfg"; fill 1.2 from_nyc_rack1 ../../chi/rack2/chi-leaf2.cfg
fill 1.2 readme_from_chi_rack2 ../README.txt; fill 1.2 parent_of_home /home
check 1.2

step "2.1"
show 'head -n 3 files/logs/r1.log; tail -n 2 files/logs/r1.log'
make -s live
sleep 14
show 'tail -n 5 files/logs/live.log'
word=$(grep -o 'the word is [a-z]*' files/logs/live.log | awk '{print $4}')
t=$(grep -m1 'LINK_DOWN: Interface GigabitEthernet1 ' files/logs/r1.log | awk '{print $3}' | cut -c1-8)
first=$(head -n 1 files/logs/r1.log | grep -o -- '-5-[A-Z_]*' | cut -c4-)
last=$(tail -n 1 files/logs/r1.log | grep -o -- '-5-[A-Z_]*' | cut -c4-)
fill 2.1 first_event "$first"; fill 2.1 last_event "$last"; fill 2.1 gi1_down_time "$t"; fill 2.1 live_word "$word"
printf 'checked r1\n' > ~/notes.txt
check 2.1

step "2.2"
show "ls -l files/backups"
show "find files -name '*.cfg' -empty"
show "find files -name '*leaf2*'"
fill 2.2 empty_files "$(find files -name '*.cfg' -empty | wc -l)"; fill 2.2 leaf2_files "$(find files -name '*leaf2*' | wc -l)"
(cd files/backups && mkdir r1 sw1 && mv 'sw1 2026-11-02.cfg' sw1-2026-11-02.cfg && rm r1-2026-11-03.cfg sw1-2026-11-03.cfg \
  && mv r1-*.cfg r1/ && mv sw1-*.cfg sw1/)
show 'ls -R files/backups'
check 2.2

step "3.1"
export LOG=files/logs/r1.log
show 'grep LINK_DOWN "$LOG" | cut -d" " -f6'
fill 3.1 gi2_lines 'grep -c GigabitEthernet2 "$LOG"'
fill 3.1 failed_lines 'grep LOGIN_FAILED "$LOG"'
fill 3.1 not_config 'grep -vc CONFIG_DONE "$LOG"'
fill 3.1 downs_per_interface "grep LINK_DOWN \"\$LOG\" \\| cut -d' ' -f6 \\| sort \\| uniq -c \\| sort -rn"
fill 3.1 save_errors 'grep -- -3- "$LOG" > reports/errors.txt'
show 'grep LINK_DOWN "$LOG" | cut -d" " -f6 | sort | uniq -c | sort -rn'
check 3.1

step "3.2"
show 'grep LOGIN_FAILED "$LOG" | head -n 3'
show 'grep LOGIN_FAILED "$LOG" | cut -d" " -f8 | sort | uniq -c | sort -rn'
fill 3.2 failed_total 'grep -c LOGIN_FAILED "$LOG"'
fill 3.2 failed_by_user "grep LOGIN_FAILED \"\$LOG\" \\| cut -d' ' -f8 \\| sort \\| uniq -c \\| sort -rn"
fill 3.2 users_once "grep LOGIN_FAILED \"\$LOG\" \\| cut -d' ' -f8 \\| sort -u"
check 3.2
unset LOG

step "4.1"
show 'ls -l /etc/shadow; cat /etc/shadow; id'
show 'sudo head -n 1 /etc/shadow | cut -c1-6'
show 'mkdir -p work && touch work/private.txt && ls -l work && chmod 600 work/private.txt && ls -l work'
show "echo 'echo \"it runs\"' > work/run.sh; work/run.sh; chmod 755 work/run.sh; work/run.sh"
show 'traceroute'
show 'sudo apt install traceroute 2>&1 | tail -n 3'
show 'sudo apt update 2>&1 | tail -n 1; sudo apt install traceroute 2>&1 | tail -n 4; traceroute --version'
fill 4.1 shadow_owner root; fill 4.1 shadow_group shadow; fill 4.1 without_sudo "Permission denied"
check 4.1

step "4.2"
make -s break T=4.2
show 'ls -l work/keys work/bin work/team-notes.txt'
show 'ssh -o StrictHostKeyChecking=accept-new -o BatchMode=yes -i work/keys/lab_key netops@ws1 hostname 2>&1 | head -n 12'
show 'work/bin/hello.sh'
chmod 600 work/keys/lab_key; chmod 755 work/bin/hello.sh; chmod 644 work/team-notes.txt
show 'ssh -o BatchMode=yes -i work/keys/lab_key netops@ws1 hostname; work/bin/hello.sh'
fill 4.2 ssh_warning UNPROTECTED
check 4.2

step "5.1"
show 'sleep 300 & jobs; ps; kill %1'
fill 5.1 shell_name bash; fill 5.1 python_path "$(bash -ic 'which python' 2>/dev/null)"; fill 5.1 stopped_word Stopped
fill 5.1 top_quit_key q
LAB_SITE=nyc
show "bash -c 'echo [\$LAB_SITE]'"
echo 'export LAB_SITE=nyc' >> ~/.bashrc
check 5.1

step "5.2"
make -s break T=5.2
sleep 2
show 'ps -eo pid,pcpu,comm --sort=-pcpu | head -n 3'
pid=$(pgrep -x labhog)
show "kill $pid; sleep 1; ps -p $pid -o pid,stat,comm"
show "kill -9 $pid; sleep 1; ps -p $pid -o pid,comm; echo exit \$?"
show 'files/labinfo'
mkdir -p ~/tools && cp files/labinfo ~/tools/ && chmod +x ~/tools/labinfo
show 'cd / && labinfo'
echo 'export PATH="$HOME/tools:$PATH"' >> ~/.bashrc
fill 5.2 hog_pid "$pid"; fill 5.2 signal_that_worked KILL
check 5.2

step "6.1"
show 'ls -la ~/.ssh'
show 'docker exec ws1 ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub'
fp=$(docker exec ws1 ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub | awk '{print $2}')
show 'ssh-keygen -R ws1'
show '(sleep 3; printf "no\n") | timeout 15 script -qec "ssh netops@ws1" /dev/null 2>&1 | tr -d "\r" | head -n 6'
# typing yes saves the one key ssh was shown: the ED25519 one
ssh-keyscan -t ed25519 ws1 2>/dev/null | ssh-keygen -lf - | grep -q "$fp" && ssh-keyscan -t ed25519 -H ws1 >> ~/.ssh/known_hosts 2>/dev/null
show "ssh-keygen -t ed25519 -N '' -f ~/.ssh/id_ed25519 | head -n 4"
withpw netops-lab ssh-copy-id netops@ws1 2>&1 | tail -n 3
show 'ssh -o BatchMode=yes netops@ws1 hostname'
fill 6.1 ws1_fingerprint "$fp"
check 6.1

step "6.2"
printf 'Host ws1\n    User netops\nHost srv1\n    User netops\nHost r1\n    User admin\n' >> ~/.ssh/config
show 'ssh -G ws1 | head -n 4'
ssh-keyscan -t ed25519 -H srv1 >> ~/.ssh/known_hosts 2>/dev/null
withpw netops-lab ssh-copy-id srv1 2>&1 | tail -n 2
show 'scp files/notes/handover.txt srv1: && ssh srv1 cat handover.txt'
make -s break T=6.2
show 'ssh -o BatchMode=yes srv1 true 2>&1'
show 'ssh-keygen -R srv1'
ssh-keyscan -t ed25519 -H srv1 >> ~/.ssh/known_hosts 2>/dev/null
show 'ssh srv1 hostname'
show 'printf "exit\n" | withpw capeos-lab ssh -o StrictHostKeyChecking=accept-new r1 2>&1 | tail -n 2' || true
check 6.2

step "7.1"
chmod +x scripts/reach.sh
show './scripts/reach.sh | head -n 2'
show 'ping -c 1 -W 1 ws1 >/dev/null 2>&1; echo $?; ping -c 1 -W 1 172.80.102.99 >/dev/null 2>&1; echo $?'
python3 - <<'PY'
import pathlib
p = pathlib.Path("scripts/reach.sh"); s = p.read_text()
s = s.replace('  echo "TODO 7.1a is still open: $host"\n', '  if ping -c 1 -W 1 "$host" >/dev/null 2>&1; then\n    echo "$host up"\n  else\n    echo "$host down"\n    down=1\n  fi\n')
s = s.replace("# TODO 7.1b: finish with exit code $down, so that 0 means every host answered.\n", "# TODO 7.1b: finish with exit code $down, so that 0 means every host answered.\nexit \"$down\"\n")
p.write_text(s)
PY
show './scripts/reach.sh; echo $?'
show "printf 'ws1\nsrv1\n' > /tmp/up.txt; ./scripts/reach.sh /tmp/up.txt && echo 'all up'"
check 7.1

step "7.2"
show 'ls files/configs'
show "grep -c '^ntp server' files/configs/*.cfg"
show 'for f in $(ls files/configs); do echo "[$f]"; done | head -n 4'
cat > scripts/audit.sh <<'SH'
#!/usr/bin/env bash
dir="${1:-}"
if [ -z "$dir" ] || [ ! -d "$dir" ]; then
  echo "usage: $0 DIR   (DIR is a folder of .cfg files)" >&2
  exit 2
fi
missing=0
for f in "$dir"/*.cfg; do
  [ -e "$f" ] || continue
  if ! grep -q '^ntp server' "$f"; then
    basename "$f"
    missing=1
  fi
done
exit "$missing"
SH
chmod +x scripts/audit.sh
show './scripts/audit.sh files/configs; echo "exit $?"'
check 7.2

step "8.1"
show 'ssh ws1 "ip -br addr; ip route; cat /etc/resolv.conf; dig +short srv1.lab; ip route get 192.168.20.10; traceroute -n srv1"'
fill 8.1 gateway 192.168.10.1; fill 8.1 mgmt_interface eth0; fill 8.1 srv1_address 192.168.20.10
fill 8.1 dns_server 192.168.20.10; fill 8.1 hops_to_srv1 2; fill 8.1 route_dev eth1
check 8.1

step "8.2"
show 'ssh ws1 "curl -v http://srv1:8080/ 2>&1 | grep -i fail"'
show 'ssh srv1 "curl -s http://localhost:8080/; ss -tlnp; cat /etc/labweb.conf"'
ssh srv1 "sudo sed -i 's/^BIND=.*/BIND=0.0.0.0/' /etc/labweb.conf && sudo labweb restart && ss -tln"
show 'ssh ws1 curl -s http://srv1:8080/'
fill 8.2 curl_said refused; fill 8.2 listen_before 127.0.0.1; fill 8.2 listen_after 0.0.0.0
check 8.2

step "8.3"
show 'ssh ws1 "sudo tcpdump -n -i eth1 -w web.pcap port 8080 & sleep 2; curl -s http://srv1:8080/ >/dev/null; sleep 1; sudo pkill -INT -x tcpdump; sleep 1; ls -l web.pcap"'
show 'ssh ws1 "tcpdump -n -r web.pcap | head -n 2"'
show 'scp ws1:web.pcap captures/ && tcpdump -n -r captures/web.pcap 2>/dev/null | wc -l'
port=$(tcpdump -n -r captures/web.pcap 2>/dev/null | head -n 1 | awk '{print $3}' | awk -F. '{print $NF}')
fill 8.3 client_port "$port"; fill 8.3 packets "$(tcpdump -n -r captures/web.pcap 2>/dev/null | wc -l)"
check 8.3

step "everything"
make -s check | grep '╰─' | tail -n 1
