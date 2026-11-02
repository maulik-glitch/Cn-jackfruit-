"""Three-host Mininet topology for the CN Jackfruit OpenFlow demonstration."""

from __future__ import annotations

from mininet.cli import CLI
from mininet.log import info, setLogLevel
from mininet.net import Mininet
from mininet.node import OVSSwitch, RemoteController
from mininet.topo import Topo


class ExamTopology(Topo):
    def build(self):
        student_one = self.addHost("h1", ip="10.0.0.1/24")
        student_two = self.addHost("h2", ip="10.0.0.2/24")
        exam_server = self.addHost("h3", ip="10.0.0.3/24")
        switch = self.addSwitch("s1", protocols="OpenFlow13")

        self.addLink(student_one, switch)
        self.addLink(student_two, switch)
        self.addLink(exam_server, switch)


def main():
    setLogLevel("info")
    topology = ExamTopology()
    network = Mininet(
        topo=topology,
        controller=None,
        switch=OVSSwitch,
        autoSetMacs=True,
        autoStaticArp=True,
    )
    network.addController(
        name="c0",
        controller=RemoteController,
        ip="127.0.0.1",
        port=6653,
    )

    try:
        info("*** Starting CN Jackfruit SDN topology\n")
        network.start()
        info("*** Hosts: h1=10.0.0.1, h2=10.0.0.2, h3/server=10.0.0.3\n")
        info("*** OpenFlow 1.3 switch s1 is controlled by OS-Ken at 127.0.0.1:6653\n")
        info("*** Start the exam server on h3, then clients on h1/h2.\n")
        CLI(network)
    finally:
        network.stop()


if __name__ == "__main__":
    main()
