"""OpenFlow 1.3 controller for the CN Jackfruit Mininet demonstration.

Learns host MAC addresses and installs datapath flows. TCP traffic using the
exam application's port (5050) is classified and marked with DSCP EF (46).
All other learned traffic is forwarded normally.
"""

from __future__ import annotations

from os_ken.base import app_manager
from os_ken.controller import ofp_event
from os_ken.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from os_ken.lib.packet import ethernet, ether_types, ipv4, packet, tcp
from os_ken.ofproto import ofproto_v1_3


class CNJackfruitController(app_manager.OSKenApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    EXAM_TCP_PORT = 5050
    EXAM_DSCP = 46  # Expedited Forwarding (EF) traffic-class marking.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mac_to_port: dict[int, dict[str, int]] = {}

    def add_flow(self, datapath, priority, match, actions, idle_timeout=300):
        parser = datapath.ofproto_parser
        instructions = [
            parser.OFPInstructionActions(datapath.ofproto.OFPIT_APPLY_ACTIONS, actions)
        ]
        flow_mod = parser.OFPFlowMod(
            datapath=datapath,
            priority=priority,
            match=match,
            instructions=instructions,
            idle_timeout=idle_timeout,
        )
        datapath.send_msg(flow_mod)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, event):
        datapath = event.msg.datapath
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions, idle_timeout=0)
        self.logger.info(
            "OpenFlow 1.3 switch connected: dpid=%016x; table-miss rule installed",
            datapath.id,
        )

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, event):
        message = event.msg
        datapath = message.datapath
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        in_port = message.match["in_port"]

        pkt = packet.Packet(message.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        if eth is None or eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        dpid = datapath.id
        learned = self.mac_to_port.setdefault(dpid, {})
        learned[eth.src] = in_port
        out_port = learned.get(eth.dst, ofproto.OFPP_FLOOD)

        ip_header = pkt.get_protocol(ipv4.ipv4)
        tcp_header = pkt.get_protocol(tcp.tcp)
        is_exam_traffic = bool(
            ip_header
            and tcp_header
            and (tcp_header.dst_port == self.EXAM_TCP_PORT or tcp_header.src_port == self.EXAM_TCP_PORT)
        )

        actions = []
        if is_exam_traffic:
            actions.append(parser.OFPActionSetField(ip_dscp=self.EXAM_DSCP))
            self.logger.info(
                "EXAM TRAFFIC | dpid=%016x | %s:%s -> %s:%s | DSCP=%s",
                dpid,
                ip_header.src,
                tcp_header.src_port,
                ip_header.dst,
                tcp_header.dst_port,
                self.EXAM_DSCP,
            )
        actions.append(parser.OFPActionOutput(out_port))

        # Install a specific flow once the destination port is known. The first
        # unknown-destination packet is flooded and still receives the DSCP action.
        if out_port != ofproto.OFPP_FLOOD:
            fields = {
                "in_port": in_port,
                "eth_src": eth.src,
                "eth_dst": eth.dst,
            }
            if ip_header:
                fields.update({
                    "eth_type": ether_types.ETH_TYPE_IP,
                    "ipv4_src": ip_header.src,
                    "ipv4_dst": ip_header.dst,
                })
                if tcp_header:
                    fields.update({
                        "ip_proto": 6,
                        "tcp_src": tcp_header.src_port,
                        "tcp_dst": tcp_header.dst_port,
                    })
            match = parser.OFPMatch(**fields)
            self.add_flow(datapath, 100 if is_exam_traffic else 10, match, actions)

        data = message.data if message.buffer_id == ofproto.OFP_NO_BUFFER else None
        packet_out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=message.buffer_id,
            in_port=in_port,
            actions=actions,
            data=data,
        )
        datapath.send_msg(packet_out)
