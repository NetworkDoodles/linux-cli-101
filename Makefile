# Network Doodles lab · Linux and the command line 101
# Guide: https://networkdoodles.com/labs/linux-cli-101/
#
# Tasks are numbered chapter.task, so T=2.1 is chapter 2, task 1. CH=<n> means a whole chapter.
.DEFAULT_GOAL := help
# The dev container keeps its venv outside the repo (VENV is set there); locally it is .venv.
VENV ?= .venv
PY := $(VENV)/bin/python
TOPO := lab/topology.clab.yml
BOLT := ghcr.io/dkhenderson2/capeos-bolt:0.11.0
HOST := nd-linuxhost:1
NODES := ws1 srv1 r1
T ?=
CH ?=
H ?=

help: ## show this help
	@grep -hE '^[a-z0-9-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

REQS := requirements.txt
REQ_HASH = $(shell python3 -c "import hashlib,sys; print(hashlib.sha256(b''.join(open(f,'rb').read() for f in sys.argv[1:])).hexdigest()[:16])" $(REQS))

setup: ## create the Python venv the checker uses
	@if [ "$$(cat $(VENV)/.ok 2>/dev/null)" = "$(REQ_HASH)" ] && [ -x $(PY) ]; then exit 0; fi; \
	echo "installing the checker's Python packages into $(VENV)"; \
	if command -v uv >/dev/null; then \
	  uv venv -q --allow-existing --python 3.13 $(VENV) && uv pip install -q --python $(PY) -r $(REQS); \
	else \
	  python3 -m venv $(VENV) && $(PY) -m pip install -q -r $(REQS); \
	fi && echo "$(REQ_HASH)" > $(VENV)/.ok

# The dev container's own Docker engine starts alongside the container, so the first commands can beat it.
docker-ready:
	@for i in $$(seq 1 60); do docker info >/dev/null 2>&1 && exit 0; [ $$i = 1 ] && echo "  waiting for Docker to start ..."; sleep 2; done; \
	echo "Docker isn't answering. In the dev container it starts on its own; on a laptop, start Docker Desktop."; exit 1

images: docker-ready ## pull the router image and build the Linux machines' image (the dev container does this once)
	@docker image inspect $(BOLT) >/dev/null 2>&1 || docker pull -q $(BOLT)
	@docker build -q -t $(HOST) lab/host >/dev/null && echo "  built $(HOST), the lab's Linux machines"

up: setup docker-ready ## start the network: ws1, r1 and srv1 (under a minute)
	@command -v containerlab >/dev/null || (echo "containerlab isn't installed: it comes with the dev container"; exit 2)
	@$(MAKE) -s images
	@$(PY) lab/solve.py clear-state
	containerlab deploy -t $(TOPO) --reconfigure
	@# containerlab writes an SSH config that skips host-key checks for the lab's nodes. This course is
	@# about those checks (chapter 6), so the lab takes it out again. Its /etc/hosts names stay.
	@sudo rm -f /etc/ssh/ssh_config.d/clab-lcli.conf
	@$(PY) lab/wait.py

down: ## remove the network (your files stay)
	containerlab destroy -t $(TOPO) --cleanup

reset: ## the network back to how it started (your files, ~/.ssh and ~/.bashrc stay)
	$(MAKE) up

shell: ## a root shell on a machine or the router, without SSH:  make shell H=ws1
	@case " $(NODES) " in *" $(H) "*) ;; *) echo "usage: make shell H=<name>   one of: $(NODES)"; exit 2;; esac
	@case "$(H)" in r1) docker exec -it r1 capeos-cli;; *) docker exec -it -w /root $(H) bash;; esac

status: ## what's running, and where to start  (WAIT=1 waits for the network)
	@$(PY) lab/status.py $(if $(WAIT),--wait)

live: ## task 2.1: a minute of new lines in files/logs/live.log, to watch with tail -f
	@$(PY) lab/solve.py live

check: ## verify a task, a chapter or everything:  make check T=1.1 · CH=1 · (nothing)
	@$(PY) checks/check.py $(if $(T),$(T),$(if $(CH),ch$(CH),all))

solve: ## stuck, or skipped a task? do it for you and fill in its answers, printing every command:  make solve T=1.2
	@test -n "$(T)" || (echo "usage: make solve T=<chapter.task>, e.g. T=1.2"; exit 2)
	@$(PY) lab/solve.py solve $(T)

break: ## set up a task's problem on purpose:  make break T=4.2 · T=5.2 · T=6.2
	@test -n "$(T)" || (echo "usage: make break T=4.2|5.2|6.2"; exit 2)
	@$(PY) lab/solve.py break $(T)

.PHONY: help setup docker-ready images up down reset shell status live check solve break
