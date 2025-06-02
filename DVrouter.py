####################################################
# DVrouter.py
# Name:
# HUID:
#####################################################

from router import Router
from packet import Packet
import json
import time


class DVrouter(Router):
    """Distance vector routing protocol implementation."""

    def __init__(self, addr, heartbeat_time):
        """Initialize distance vector router."""
        Router.__init__(self, addr, heartbeat_time)
        self.addr = addr
        self.heartbeat_time = heartbeat_time
        self.last_sent = 0

        # Distance vector: maps destination to (cost, port)
        self.dv = {addr: (0, None)}  # We can reach ourselves with 0 cost

        # Neighbors: maps port to (neighbor_addr, cost)
        self.neighbors = {}

        # Neighbor DVs: maps neighbor_addr to their distance vector
        self.neighbor_dvs = {}

        # Forwarding table: maps destination to outgoing port
        self.forwarding_table = {}

    def handle_packet(self, port, packet):
        """Process incoming packet."""
        if packet.is_traceroute:
            # Handle data packet using forwarding table
            if packet.dst_addr in self.forwarding_table:
                out_port = self.forwarding_table[packet.dst_addr]
                self.send(out_port, packet)
            # Check if this packet is destined for a client directly connected to us
            # by checking if the destination is a neighbor
            else:
                for p, (neighbor, _) in self.neighbors.items():
                    if neighbor == packet.dst_addr:
                        self.send(p, packet)
                        return
        else:
            # Handle routing packet (distance vector)
            try:
                neighbor_addr = self.neighbors[port][0]
                received_dv = json.loads(packet.content)

                # Check if this is a new neighbor or if the DV has changed
                dv_changed = False
                if neighbor_addr not in self.neighbor_dvs:
                    dv_changed = True
                else:
                    # Check if the DV has changed
                    old_dv = self.neighbor_dvs[neighbor_addr]
                    for dest, cost in received_dv.items():
                        if dest not in old_dv or old_dv[dest] != cost:
                            dv_changed = True
                            break

                # Store neighbor's distance vector
                self.neighbor_dvs[neighbor_addr] = received_dv

                # Update our distance vector if the neighbor's DV changed
                if dv_changed and self.update_distance_vector():
                    # If our DV changed, broadcast it
                    self.broadcast_dv()
            except Exception as e:
                # Handle parsing errors
                pass

    def handle_new_link(self, port, endpoint, cost):
        """Handle new link."""
        # Store new neighbor information
        self.neighbors[port] = (endpoint, cost)

        # Update our distance vector with the direct path to the new neighbor
        updated = False
        if endpoint not in self.dv or self.dv[endpoint][0] > cost:
            self.dv[endpoint] = (cost, port)
            self.forwarding_table[endpoint] = port
            updated = True

        # Recalculate distance vector with new link
        updated = self.update_distance_vector() or updated

        # Always broadcast our DV to all neighbors when a new link is added
        # This ensures that all routers are aware of the new link
        self.broadcast_dv()

        # Request the new neighbor's DV by sending our DV to it
        if port in self.neighbors:
            self.send_dv_to_neighbor(port)

    def handle_remove_link(self, port):
        """Handle removed link."""
        if port not in self.neighbors:
            return

        # Get the neighbor that was connected to this port
        neighbor_addr = self.neighbors[port][0]

        # Remove neighbor information
        del self.neighbors[port]
        if neighbor_addr in self.neighbor_dvs:
            del self.neighbor_dvs[neighbor_addr]

        # Update distance vector and forwarding table
        updated = False

        # Mark routes that used this port as infinity (16)
        routes_to_update = []
        for dest, (cost, out_port) in self.dv.items():
            if out_port == port:
                routes_to_update.append(dest)

        # Remove these routes from our DV
        for dest in routes_to_update:
            del self.dv[dest]
            if dest in self.forwarding_table:
                del self.forwarding_table[dest]
            updated = True

        # Recalculate distance vector to find alternative paths
        updated = self.update_distance_vector() or updated

        # Broadcast our DV if it changed
        if updated:
            self.broadcast_dv()
        else:
            # Even if our DV didn't change, we should broadcast to inform neighbors
            # about the link removal
            self.broadcast_dv()

    def handle_time(self, time_ms):
        """Handle periodic tasks."""
        # Send distance vector periodically
        if time_ms - self.last_sent >= self.heartbeat_time:
            # Recalculate distance vector before broadcasting
            self.update_distance_vector()
            self.broadcast_dv()
            self.last_sent = time_ms

    def update_distance_vector(self):
        """Update distance vector based on neighbors' DVs.
        Returns True if DV was changed, False otherwise."""
        updated = False

        # For each destination in any neighbor's DV
        all_destinations = set()
        for neighbor_dv in self.neighbor_dvs.values():
            all_destinations.update(neighbor_dv.keys())

        # Add our direct neighbors
        for port, (endpoint, cost) in self.neighbors.items():
            all_destinations.add(endpoint)

        # For each possible destination
        for dest in all_destinations:
            if dest == self.addr:
                continue  # Skip ourselves

            # Find best path through neighbors
            best_cost = float('inf')
            best_port = None

            # Check direct neighbors first
            for port, (endpoint, cost) in self.neighbors.items():
                if endpoint == dest and cost < best_cost:
                    best_cost = cost
                    best_port = port

            # Then check paths through neighbors
            for port, (neighbor, direct_cost) in self.neighbors.items():
                if neighbor in self.neighbor_dvs and dest in self.neighbor_dvs[neighbor]:
                    # Calculate cost through this neighbor
                    neighbor_cost = self.neighbor_dvs[neighbor][dest]

                    # Skip if neighbor reports infinity (16)
                    if neighbor_cost >= 16:
                        continue

                    total_cost = direct_cost + neighbor_cost

                    # Avoid count-to-infinity problem
                    if total_cost < best_cost and total_cost < 16:  # Infinity value
                        best_cost = total_cost
                        best_port = port

            # Update our DV if we found a better path or if this is a new destination
            if best_port is not None and (dest not in self.dv or self.dv[dest][0] > best_cost):
                self.dv[dest] = (best_cost, best_port)
                self.forwarding_table[dest] = best_port
                updated = True
            # If we can no longer reach a destination that was in our DV
            elif best_port is None and dest in self.dv:
                del self.dv[dest]
                if dest in self.forwarding_table:
                    del self.forwarding_table[dest]
                updated = True

        return updated

    def broadcast_dv(self):
        """Broadcast distance vector to all neighbors."""
        # Always include our own address with cost 0
        self.dv[self.addr] = (0, None)

        # Create a simplified DV with just costs
        simplified_dv = {}
        for dest, (cost, _) in self.dv.items():
            simplified_dv[dest] = cost

        # Send to each neighbor
        for port in self.neighbors:
            self.send_dv_to_neighbor(port)

    def send_dv_to_neighbor(self, port):
        """Send distance vector to a specific neighbor."""
        # Create a simplified DV with just costs
        simplified_dv = {}

        # Always include our own address with cost 0
        simplified_dv[self.addr] = 0

        for dest, (cost, out_port) in self.dv.items():
            # Split horizon with poison reverse
            if out_port == port:
                simplified_dv[dest] = 16  # "Infinity"
            else:
                simplified_dv[dest] = cost

        # Create and send packet
        if port in self.neighbors:  # Check if the neighbor still exists
            packet = Packet(Packet.ROUTING, self.addr, self.neighbors[port][0],
                            json.dumps(simplified_dv))
            self.send(port, packet)

    def __str__(self):
        """Return a string representation of the router state."""
        result = f"Router {self.addr}\n"
        result += "Distance Vector:\n"
        for dest, (cost, port) in sorted(self.dv.items()):
            result += f"  {dest}: cost {cost}, port {port}\n"
        result += "Forwarding Table:\n"
        for dest, port in sorted(self.forwarding_table.items()):
            result += f"  {dest} -> port {port}\n"
        return result
