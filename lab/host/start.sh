#!/bin/sh
# Sets a machine up when the lab starts (containerlab runs `start <role>` on each one).
# eth0 is the lab's management network, the way your codespace reaches it. eth1 is its cable to r1.
set -e
sysctl -qw net.ipv6.conf.all.disable_ipv6=1 net.ipv6.conf.default.disable_ipv6=1 2>/dev/null || true
for a in $(ip -o link show eth1 | grep -o 'altname [^ ]*' | cut -d' ' -f2); do ip link property del dev eth1 altname "$a"; done
ip link set eth1 up
# The management network only reaches the codespace: everything else goes through r1.
ip route del default 2>/dev/null || true
# Names come from the lab's DNS server (srv1), not from a list containerlab wrote: so `srv1` means
# 192.168.20.10, through r1, the way it would on a real network.
printf '127.0.0.1\tlocalhost\n127.0.1.1\t%s\n' "$1" > /etc/hosts
case "$1" in
  ws1)
    ip addr add 192.168.10.10/24 dev eth1
    ip route add default via 192.168.10.1
    printf 'nameserver 192.168.20.10\nsearch lab\n' > /etc/resolv.conf
    ;;
  srv1)
    ip addr add 192.168.20.10/24 dev eth1
    ip route add default via 192.168.20.1
    printf 'nameserver 127.0.0.1\nsearch lab\n' > /etc/resolv.conf
    # The lab's DNS names, from the files in /etc/lab-dns (lab/dns/ in the repo). It asks nobody else.
    dnsmasq --no-resolv --no-hosts --hostsdir=/etc/lab-dns --domain=lab --local=/lab/ --interface=eth1 \
            --interface=lo --bind-interfaces --local-ttl=60 --log-facility=/var/log/dnsmasq.log
    # A small web service (task 8.2). Its settings are in /etc/labweb.conf.
    mkdir -p /srv/www && echo "Hello from srv1, 192.168.20.10" > /srv/www/index.html
    printf '# labweb: the small web service on srv1. Change a setting, then: sudo labweb restart\nBIND=127.0.0.1\nPORT=8080\n' > /etc/labweb.conf
    labweb start
    ;;
esac
/usr/sbin/sshd
