# CN Jackfruit — SDN / OpenFlow deliverable

This folder contains a real OpenFlow 1.3 control-plane demonstration, separate
from the ordinary TCP client/server demo:

- `exam_controller.py` is an OS-Ken controller application. It learns host MAC
  addresses and installs OpenFlow rules in the switch.
- TCP traffic whose source or destination port is `5050` (the exam service) is
  classified by the controller and marked with DSCP EF (`46`). The switch then
  forwards matching packets using the installed rule.
- `exam_topology.py` creates two student hosts, one exam-server host, and one
  Open vSwitch managed by the remote controller.

OS-Ken provides a Ryu-compatible OpenFlow controller API; Mininet provides
the emulated hosts, links, and Open vSwitch topology.

## Environment

Run this part in an Ubuntu VM or a Mininet VM, not in a normal Windows terminal.
Mininet needs Linux network namespaces and root network-device access. Its
project documentation recommends using its pre-built VM as the easiest setup.

From the project root inside the Linux VM:

```bash
sudo apt update
sudo apt install -y mininet openvswitch-switch python3-venv xterm
python3 -m venv --system-site-packages .venv-sdn
source .venv-sdn/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-sdn.txt
```

If Open vSwitch is not already running:

```bash
sudo systemctl enable --now openvswitch-switch
```

## Start the controller and topology

**Terminal 1 — controller** (run as your normal VM user):

```bash
source .venv-sdn/bin/activate
osken-manager sdn/exam_controller.py --ofp-tcp-listen-port 6653 --verbose
```

**Terminal 2 — topology**:

```bash
sudo -E .venv-sdn/bin/python sdn/exam_topology.py
```

The Mininet prompt should appear. Start the TCP exam server in the server host:

```text
mininet> xterm h3
```

In the new `h3` terminal, first change to the directory containing `main_code/` (the project root), then run:

```bash
cd /path/to/cn-jackfruit-project
python3 main_code/server.py --host 0.0.0.0 --port 5050 --duration 180 --max-connections 20
```

Open student terminals:

```text
mininet> xterm h1 h2
```

In each student terminal, first change to the same project root. In the `h1` terminal:

```bash
cd /path/to/cn-jackfruit-project
python3 main_code/client.py --host 10.0.0.3 --port 5050 --name "Student One"
```

In the `h2` terminal:

```bash
cd /path/to/cn-jackfruit-project
python3 main_code/client.py --host 10.0.0.3 --port 5050 --name "Student Two"
```

The ordinary client/server protocol, scoring, timer, and result CSV are unchanged;
the packets now traverse the Mininet switch controlled by OS-Ken.

## Verify that SDN rules were installed

At the Mininet prompt:

```text
mininet> sh ovs-ofctl -O OpenFlow13 dump-flows s1
```

After exam traffic has crossed the switch, inspect the flow entries for TCP
source/destination port `5050` and an action that sets `ip_dscp` to `46`.
The OS-Ken terminal should also log `EXAM TRAFFIC` classification messages.

For a quick non-interactive network/load check, start the server on `h3` and run:

```text
mininet> h1 python3 main_code/load_test.py --host 10.0.0.3 --port 5050 --clients 5 --pings 2
```

Exit the Mininet prompt with `exit`. Clean stale Mininet/OVS state before a
fresh run if needed:

```bash
sudo mn -c
```

## Important distinction

The Windows localhost demo proves the TCP socket-programming deliverable. It
does not, by itself, prove SDN. The SDN deliverable is demonstrated only when
the controller is connected to the OpenFlow 1.3 switch and the installed flows
are visible in `ovs-ofctl dump-flows`. DSCP marking is a traffic-class label;
this example does not configure switch queues or promise a bandwidth guarantee.
