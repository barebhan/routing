####################################################
# LSrouter.py
# Name:
# HUID:
#####################################################

from router import Router
from packet import Packet
import json
import heapq
import time


class LSrouter(Router):
    """Link state routing protocol implementation.

    Add your own class fields and initialization code (e.g. to create forwarding table
    data structures). See the `Router` base class for docstrings of the methods to
    override.
    """

    def __init__(self, addr, heartbeat_time):
        """Initialize link state router."""
        Router.__init__(self, addr, heartbeat_time)
        self.addr = addr
        self.heartbeat_time = heartbeat_time
        self.last_sent = 0

        self.ls_db = {addr: {}}
        self.seq_nums = {addr: 0}
        self.neighbors = {}
        self.forwarding_table = {}
        self.packet_history = set()

    def handle_packet(self, port, packet):
        """Process incoming packet."""
        if packet.is_traceroute:
            if packet.dst_addr in self.forwarding_table:
                out_port = self.forwarding_table[packet.dst_addr]
                self.send(out_port, packet)
            else:
                for p, (neighbor, _) in self.neighbors.items():
                    if neighbor == packet.dst_addr:
                        self.send(p, packet)
                        return
        else:
            try:
                ls_data = json.loads(packet.content)
                router_addr = ls_data["router"]
                seq_num = ls_data["seq"]
                link_state = ls_data["links"]

                if (router_addr, seq_num) in self.packet_history:
                    return

                self.packet_history.add((router_addr, seq_num))

                if (router_addr not in self.seq_nums or seq_num > self.seq_nums[router_addr]):
                    self.seq_nums[router_addr] = seq_num
                    self.ls_db[router_addr] = link_state
                    self.calculate_forwarding_table()
                    self.flood_packet(packet, port)
            except Exception as e:
                pass

    def handle_new_link(self, port, endpoint, cost):
        """Handle new link."""
        self.neighbors[port] = (endpoint, cost)
        self.ls_db[self.addr][endpoint] = cost
        self.seq_nums[self.addr] += 1
        self.calculate_forwarding_table()
        self.broadcast_link_state()

    def handle_remove_link(self, port):
        """Handle removed link."""
        if port not in self.neighbors:
            return

        neighbor_addr = self.neighbors[port][0]
        del self.neighbors[port]

        if neighbor_addr in self.ls_db[self.addr]:
            del self.ls_db[self.addr][neighbor_addr]

        self.seq_nums[self.addr] += 1
        self.calculate_forwarding_table()
        self.broadcast_link_state()

    def handle_time(self, time_ms):
        """Handle periodic tasks."""
        if time_ms - self.last_sent >= self.heartbeat_time:
            self.broadcast_link_state()
            self.last_sent = time_ms

    def calculate_forwarding_table(self):
        """Calculate forwarding table using Dijkstra's algorithm."""
        self.forwarding_table = {}

        distances = {self.addr: 0}
        predecessors = {}
        first_hops = {}
        pq = [(0, self.addr)]

        while pq:
            dist, current = heapq.heappop(pq)

            if current in distances and dist > distances[current]:
                continue

            if current in self.ls_db:
                for neighbor, cost in self.ls_db[current].items():
                    new_dist = dist + cost

                    if neighbor not in distances or new_dist < distances[neighbor]:
                        distances[neighbor] = new_dist
                        predecessors[neighbor] = current

                        if current == self.addr:
                            for port, (endpoint, _) in self.neighbors.items():
                                if endpoint == neighbor:
                                    first_hops[neighbor] = port
                        elif current in first_hops:
                            first_hops[neighbor] = first_hops[current]

                        heapq.heappush(pq, (new_dist, neighbor))

        self.forwarding_table = first_hops

    def broadcast_link_state(self):
        """Broadcast link state to all neighbors."""
        ls_data = {
            "router": self.addr,
            "seq": self.seq_nums[self.addr],
            "links": self.ls_db[self.addr]
        }

        for port, (neighbor, _) in self.neighbors.items():
            packet = Packet(Packet.ROUTING, self.addr, neighbor, json.dumps(ls_data))
            self.send(port, packet)

        self.last_sent = int(time.time() * 1000)

    def flood_packet(self, packet, exclude_port):
        """Flood a link state packet to all neighbors except the one we received from."""
        for port in self.neighbors:
            if port != exclude_port:
                self.send(port, packet)

    def __str__(self):
        """Return a string representation of the router state."""
        result = f"Router {self.addr}\n"
        result += "Link State Database:\n"
        for router, links in sorted(self.ls_db.items()):
            result += f"  {router}: {links}\n"
        result += "Forwarding Table:\n"
        for dest, port in sorted(self.forwarding_table.items()):
            result += f"  {dest} -> port {port}\n"
        return result
