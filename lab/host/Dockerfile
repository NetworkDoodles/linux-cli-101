# The lab's two Linux machines, ws1 (a workstation) and srv1 (a server): Debian, like the codespace,
# with OpenSSH and the everyday network tools.
#   ip (iproute2)  addresses, routes        ss         what's listening   (also iproute2)
#   ping, traceroute, dig, curl, tcpdump     nano, less  to read and edit files
#   python3        runs srv1's small web service       dnsmasq  srv1 answers the lab's DNS names
FROM debian:trixie-slim
RUN apt-get update -qq \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends \
      bash openssh-server openssh-client iproute2 iputils-ping traceroute bind9-dnsutils curl tcpdump \
      nano less procps sudo python3 dnsmasq ca-certificates >/dev/null \
 && rm -rf /var/lib/apt/lists/*
# One everyday user, netops, with the password the guide gives (task 6.1) and sudo without a password.
# Host keys are made once, here, so they stay the same each time the lab restarts.
RUN useradd -m -s /bin/bash netops \
 && echo 'netops:netops-lab' | chpasswd \
 && echo 'netops ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/netops && chmod 440 /etc/sudoers.d/netops \
 && mkdir -p /run/sshd && ssh-keygen -A \
 && printf 'PasswordAuthentication yes\nKbdInteractiveAuthentication no\n' > /etc/ssh/sshd_config.d/lab.conf \
 && echo 'PS1="\u@\h:\w\$ "' >> /home/netops/.bashrc
COPY start.sh /usr/local/bin/start
COPY labweb /usr/local/bin/labweb
RUN chmod 755 /usr/local/bin/start /usr/local/bin/labweb
CMD ["sleep", "infinity"]
