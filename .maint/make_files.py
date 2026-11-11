"""Maintainers: write the practice files under files/ (configs, backups, notes). Run from the repo root:
    python3 .maint/make_files.py
The configs follow `show running-config` from the lab's r1 (CapeOS Bolt 0.11.0), with other names and addresses.
files/logs/r1.log is recorded from the live router instead: .maint/make_logs.sh.
"""
import os
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parents[1]
F = ROOT / "files"


def config(host, ifaces, ntp=True, logging=True):
    """A running-config in r1's format. ifaces: [(name, description, address, mask)]."""
    out = ["Building configuration...", "", "Current configuration : 337 bytes", "!", f"hostname {host}", "!"]
    if logging:
        out += ["logging host 192.168.20.10", "!"]
    out += ["interface GigabitEthernet0", " ip address dhcp", "!"]
    for name, desc, ip, mask in ifaces:
        out += [f"interface {name}", f" description {desc}", f" ip address {ip} {mask}", "!"]
    out += ["line con 0", "line vty 0 4", "!"]
    if ntp:
        out += ["ntp server 192.168.20.10", "!"]
    out += ["end", ""]
    text = "\n".join(out)
    return text.replace("337", str(len(text)))


def leaf(site, n, rack, ntp=True):
    third = {"nyc": 30, "chi": 40}[site] + rack
    return config(f"{site}-leaf{n}", [
        ("GigabitEthernet1", f"uplink to {site}-spine1", f"10.{third}.0.{n * 2 + 1}", "255.255.255.254"),
        ("GigabitEthernet2", f"servers, rack {rack}", f"10.{third}.{n}.1", "255.255.255.0"),
    ], ntp=ntp)


def write(path, text, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    os.chmod(path, mode)


def main():
    for d in ("site", "backups", "configs", "notes"):
        shutil.rmtree(F / d, ignore_errors=True)

    # Chapter 1: a small tree to find your way round. Two sites, two racks each, a leaf switch per rack.
    for site in ("nyc", "chi"):
        for rack in (1, 2):
            write(F / "site" / site / f"rack{rack}" / f"{site}-leaf{rack}.cfg", leaf(site, rack, rack))
        write(F / "site" / site / "README.txt", f"The {site} site: one leaf switch in each rack.\n")
    write(F / ".lab-notes", "A hidden file: ls shows it only with -a, because its name starts with a dot.\n")

    # Chapter 2: a backups folder that needs tidying (task 2.2).
    b = F / "backups"
    write(b / "r1-2026-11-01.cfg", config("r1", [("GigabitEthernet1", "ws1's network", "192.168.10.1", "255.255.255.0")]))
    write(b / "r1-2026-11-02.cfg", config("r1", [("GigabitEthernet1", "ws1's network", "192.168.10.1", "255.255.255.0"),
                                                ("GigabitEthernet2", "srv1 network", "192.168.20.1", "255.255.255.0")]))
    write(b / "sw1-2026-11-01.cfg", config("sw1", [("GigabitEthernet1", "uplink to r1", "192.168.10.2", "255.255.255.0")]))
    write(b / "sw1 2026-11-02.cfg", config("sw1", [("GigabitEthernet1", "uplink to r1", "192.168.10.2", "255.255.255.0")], ntp=False))
    write(b / "r1-2026-11-03.cfg", "")
    write(b / "sw1-2026-11-03.cfg", "")
    write(b / "README.txt", "Config backups, one file per device per day. Someone has been saving them by hand.\n")

    # Chapter 7: configs to audit for a missing ntp server line (task 7.2).
    c = F / "configs"
    write(c / "nyc-leaf1.cfg", leaf("nyc", 1, 1))
    write(c / "nyc-leaf2.cfg", leaf("nyc", 2, 2, ntp=False))
    write(c / "chi-leaf1.cfg", leaf("chi", 1, 1))
    write(c / "chi leaf2.cfg", leaf("chi", 2, 2, ntp=False))
    write(c / "README.txt", "Every device must have an ntp server line. Not all of them do.\n")

    # Chapter 6: a file to copy to srv1 with scp (task 6.2).
    write(F / "notes" / "handover.txt",
          "Handover for the srv1 team\n\n- labweb listens on port 8080\n- r1 is the gateway for both networks\n")
    print("wrote files/site, files/backups, files/configs, files/notes")


main()
