# The lab's dev container: containerlab's Docker-in-Docker image plus the checker's Python venv.
# It's Debian 12, and it is the computer you learn on: its terminal is the "codespace" in every task.
FROM ghcr.io/srl-labs/containerlab/devcontainer-dind-slim:0.83.0

USER vscode
ENV VENV=/home/vscode/.venvs/lab
ENV PATH=/home/vscode/.venvs/lab/bin:$PATH
COPY --chown=vscode:vscode requirements.txt /tmp/lab/
# .ok records which requirements were installed (the same hash `make setup` checks), so the first start
# doesn't reinstall them.
RUN uv venv -q --python 3.13 "$VENV" \
 && uv pip install -q --python "$VENV/bin/python" -r /tmp/lab/requirements.txt \
 && cd /tmp/lab && python3 -c "import hashlib,sys; print(hashlib.sha256(b''.join(open(f,'rb').read() for f in sys.argv[1:])).hexdigest()[:16])" requirements.txt > "$VENV/.ok"

# code-server reads its own settings, not devcontainer.json's.
COPY --chown=vscode:vscode .devcontainer/code-server-settings.json /home/vscode/.local/share/code-server/User/settings.json

USER root
# traceroute is left out on purpose: task 4.1 installs it with apt.
RUN (dpkg -s traceroute >/dev/null 2>&1 && apt-get purge -y -qq traceroute) || true
USER vscode
# containerlab's image comes with an SSH key pair (it hands it to the switches it knows). This lab has none of
# those, and chapter 6 starts from "you have no key yet", so the learner makes their own.
RUN rm -f /home/vscode/.ssh/id_ecdsa /home/vscode/.ssh/id_ecdsa.pub
