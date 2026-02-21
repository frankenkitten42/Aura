#!/usr/bin/env python3
"""
AURA HTTP Server for UE5 Integration

This server provides a REST API that UE5 can query to get real-time
environmental parameters. Run this alongside your UE5 project.

Endpoints:
    GET  /status           - Server status
    GET  /regions          - List all regions
    GET  /region/<id>      - Get region state
    POST /region/<id>/pop  - Set region population
    GET  /parameters       - Get all UE5 parameters
    GET  /parameters/<id>  - Get region UE5 parameters
    POST /update           - Tick the simulation
    POST /reset            - Reset simulation

Usage:
    python ue5_server.py --port 8080

UE5 Integration:
    Use VaRest plugin or HTTP module to query this server.
"""

import sys
import os
import json
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from vde.pressure_coordinator import PressureCoordinator
from vde.wildlife import WildlifeManager
from vde.npc_behavior import NPCManager, NPCType
from vde.environmental_wear import WearManager, SurfaceType, RegionWearManager
from vde.motion_coherence import MotionManager, MotionCategory
from vde.attraction_system import AttractionCoordinator


class LSESimulation:
    """Main simulation state."""
    
    def __init__(self):
        self.lock = threading.Lock()
        
        # Core coordinator
        self.coordinator = PressureCoordinator()
        
        # Per-region subsystems
        self.wildlife: dict = {}
        self.npcs: dict = {}
        self.wear: dict = {}
        self.motion: dict = {}
        
        # Attraction coordinator
        self.attraction = AttractionCoordinator()
        
        self.time = 0.0
        self.tick_rate = 0.1  # 10 Hz
        self.auto_tick = False
        self._tick_thread = None
    
    def add_region(self, region_id: str, position: tuple = (0, 0), 
                   surface: str = "grass"):
        """Add a region to the simulation."""
        with self.lock:
            self.coordinator.add_region(region_id, position)
            self.attraction.add_region(region_id, position)
            
            # Create subsystems
            self.wildlife[region_id] = WildlifeManager()
            self.npcs[region_id] = NPCManager()
            
            surface_type = SurfaceType[surface.upper()] if surface else SurfaceType.GRASS
            self.wear[region_id] = WearManager(surface_type=surface_type)
            
            self.motion[region_id] = MotionManager()
            
            # Register default elements
            for i in range(3):
                self.motion[region_id].register_element(f"tree_{i}", MotionCategory.FOLIAGE)
                self.motion[region_id].register_element(f"banner_{i}", MotionCategory.CLOTH)
    
    def set_population(self, region_id: str, population: float):
        """Set population for a region."""
        with self.lock:
            if region_id in self.coordinator.regions:
                self.coordinator.set_population(region_id, population)
                self.attraction.set_population(region_id, population)
    
    def update(self, delta_time: float = None):
        """Update simulation."""
        if delta_time is None:
            delta_time = self.tick_rate
        
        with self.lock:
            self.time += delta_time
            
            # Update coordinator
            self.coordinator.update(delta_time)
            self.attraction.update(delta_time)
            
            # Update per-region subsystems
            for region_id, mgr in self.coordinator.regions.items():
                pop = mgr.state.population
                
                if region_id in self.wildlife:
                    self.wildlife[region_id].set_population(pop)
                    self.wildlife[region_id].update(delta_time)
                
                if region_id in self.npcs:
                    self.npcs[region_id].set_population(pop)
                    self.npcs[region_id].update(delta_time)
                
                if region_id in self.wear:
                    self.wear[region_id].set_population(pop)
                    self.wear[region_id].update(delta_time)
                
                if region_id in self.motion:
                    self.motion[region_id].set_population(pop)
                    self.motion[region_id].update(delta_time)
    
    def get_region_state(self, region_id: str) -> dict:
        """Get complete state for a region."""
        with self.lock:
            if region_id not in self.coordinator.regions:
                return None
            
            mgr = self.coordinator.regions[region_id]
            state = mgr.state
            
            result = {
                'region_id': region_id,
                'time': self.time,
                'population': state.population,
                'pressure': {
                    'sdi': state.sdi,
                    'vdi': state.vdi,
                    'vdi_lagged': state.vdi_lagged,
                    'phase': state.phase.value,
                    'combined': state.combined_pressure,
                    'differential': state.pressure_differential,
                },
                'attraction': self.attraction.get_attraction(region_id),
            }
            
            # Add subsystem states
            if region_id in self.wildlife:
                ws = self.wildlife[region_id].get_snapshot()
                result['wildlife'] = {
                    'state': ws.state.value,
                    'spawn_rate': ws.spawn_rate_modifier,
                    'behavior': ws.behavior_modifier,
                }
            
            if region_id in self.npcs:
                ns = self.npcs[region_id].get_snapshot()
                result['npcs'] = {
                    'comfort': ns.comfort_level.value,
                    'edge_preference': ns.edge_preference,
                    'repositioning_active': ns.repositioning_active,
                }
            
            if region_id in self.wear:
                wsnap = self.wear[region_id].get_snapshot()
                result['wear'] = {
                    'total': wsnap.total_wear,
                    'displacement': wsnap.layer_values.get('displacement', 0),
                    'discoloration': wsnap.layer_values.get('discoloration', 0),
                    'damage': wsnap.layer_values.get('damage', 0),
                }
            
            if region_id in self.motion:
                result['motion'] = {
                    'coherence_level': self.motion[region_id].coherence_level.value,
                    'coherence_value': self.motion[region_id].coherence_value,
                    'wind_direction': self.motion[region_id]._wind_direction,
                    'wind_strength': self.motion[region_id]._wind_strength,
                }
            
            return result
    
    def get_ue5_parameters(self, region_id: str) -> dict:
        """Get UE5-ready parameters for a region."""
        with self.lock:
            if region_id not in self.coordinator.regions:
                return None
            
            result = {
                'region_id': region_id,
                'time': self.time,
            }
            
            # Pressure parameters
            mgr = self.coordinator.regions[region_id]
            result['pressure'] = {
                'Pressure_SDI': mgr.sdi,
                'Pressure_VDI': mgr.vdi,
                'Pressure_Phase': mgr.phase.value,
                'Pressure_Combined': mgr.state.combined_pressure,
            }
            
            # Wildlife parameters
            if region_id in self.wildlife:
                ws = self.wildlife[region_id].get_snapshot()
                result['wildlife'] = {
                    'Wildlife_SpawnRate': ws.spawn_rate_modifier,
                    'Wildlife_State': ws.state.value,
                    'Wildlife_BehaviorMod': ws.behavior_modifier,
                }
            
            # NPC parameters
            if region_id in self.npcs:
                ns = self.npcs[region_id].get_snapshot()
                result['npcs'] = {
                    'NPC_ComfortLevel': ns.comfort_level.value,
                    'NPC_EdgePreference': ns.edge_preference,
                    'NPC_InteractionRadius': ns.interaction_radius_modifier,
                }
            
            # Wear parameters
            if region_id in self.wear:
                params = self.wear[region_id].get_ue5_parameters()
                result['wear'] = params.to_ue5_json()
            
            # Motion parameters
            if region_id in self.motion:
                params = self.motion[region_id].get_ue5_parameters()
                result['motion'] = params.to_ue5_json()
            
            # Attraction
            if region_id in self.attraction.regions:
                params = self.attraction.get_region_parameters(region_id)
                result['attraction'] = params.to_ue5_json()
            
            return result
    
    def get_all_parameters(self) -> dict:
        """Get all UE5 parameters."""
        with self.lock:
            return {
                'time': self.time,
                'regions': {
                    rid: self.get_ue5_parameters(rid)
                    for rid in self.coordinator.regions
                },
                'world': {
                    'highest_pressure': self.coordinator.get_highest_pressure_region(),
                    'lowest_pressure': self.coordinator.get_lowest_pressure_region(),
                    'pressure_map': self.coordinator.get_pressure_map(),
                    'attraction_map': dict(self.coordinator._attraction_targets),
                }
            }
    
    def reset(self):
        """Reset simulation."""
        with self.lock:
            self.coordinator.reset()
            self.attraction.reset()
            
            for w in self.wildlife.values():
                w.reset()
            for n in self.npcs.values():
                n.reset()
            for w in self.wear.values():
                w.reset()
            for m in self.motion.values():
                m.reset()
            
            self.time = 0.0
    
    def start_auto_tick(self):
        """Start automatic ticking."""
        if self._tick_thread is None or not self._tick_thread.is_alive():
            self.auto_tick = True
            self._tick_thread = threading.Thread(target=self._tick_loop, daemon=True)
            self._tick_thread.start()
    
    def stop_auto_tick(self):
        """Stop automatic ticking."""
        self.auto_tick = False
    
    def _tick_loop(self):
        """Background tick loop."""
        while self.auto_tick:
            self.update()
            time.sleep(self.tick_rate)


# Global simulation instance
simulation = LSESimulation()


class LSERequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for LSE server."""
    
    def _send_json(self, data, status=200):
        """Send JSON response."""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())
    
    def _send_error(self, message, status=400):
        """Send error response."""
        self._send_json({'error': message}, status)
    
    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path == '/status':
            self._send_json({
                'status': 'running',
                'time': simulation.time,
                'regions': list(simulation.coordinator.regions.keys()),
                'auto_tick': simulation.auto_tick,
            })
        
        elif path == '/regions':
            self._send_json({
                'regions': list(simulation.coordinator.regions.keys()),
            })
        
        elif path.startswith('/region/'):
            region_id = path.split('/')[2]
            state = simulation.get_region_state(region_id)
            if state:
                self._send_json(state)
            else:
                self._send_error(f"Region '{region_id}' not found", 404)
        
        elif path == '/parameters':
            self._send_json(simulation.get_all_parameters())
        
        elif path.startswith('/parameters/'):
            region_id = path.split('/')[2]
            params = simulation.get_ue5_parameters(region_id)
            if params:
                self._send_json(params)
            else:
                self._send_error(f"Region '{region_id}' not found", 404)
        
        else:
            self._send_error(f"Unknown endpoint: {path}", 404)
    
    def do_POST(self):
        """Handle POST requests."""
        parsed = urlparse(self.path)
        path = parsed.path
        
        # Read body
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode() if content_length > 0 else '{}'
        
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_error("Invalid JSON")
            return
        
        if path == '/update':
            delta = data.get('delta_time', simulation.tick_rate)
            simulation.update(delta)
            self._send_json({'time': simulation.time})
        
        elif path == '/reset':
            simulation.reset()
            self._send_json({'status': 'reset', 'time': simulation.time})
        
        elif path == '/auto_tick/start':
            simulation.start_auto_tick()
            self._send_json({'status': 'auto_tick started'})
        
        elif path == '/auto_tick/stop':
            simulation.stop_auto_tick()
            self._send_json({'status': 'auto_tick stopped'})
        
        elif path.startswith('/region/') and path.endswith('/pop'):
            region_id = path.split('/')[2]
            population = data.get('population', 0.5)
            simulation.set_population(region_id, population)
            self._send_json({
                'region_id': region_id,
                'population': population,
            })
        
        elif path == '/region/add':
            region_id = data.get('region_id')
            position = tuple(data.get('position', [0, 0]))
            surface = data.get('surface', 'grass')
            
            if not region_id:
                self._send_error("region_id required")
                return
            
            simulation.add_region(region_id, position, surface)
            self._send_json({
                'status': 'added',
                'region_id': region_id,
            })
        
        else:
            self._send_error(f"Unknown endpoint: {path}", 404)
    
    def log_message(self, format, *args):
        """Custom log format."""
        print(f"[{self.log_date_time_string()}] {args[0]}")


def main():
    parser = argparse.ArgumentParser(description='LSE/VDE HTTP Server')
    parser.add_argument('--port', '-p', type=int, default=8080, help='Port to listen on')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--auto-tick', action='store_true', help='Start with auto-tick enabled')
    
    args = parser.parse_args()
    
    # Add default regions
    simulation.add_region("town_square", (0, 0), "stone")
    simulation.add_region("market", (400, 0), "dirt")
    simulation.add_region("park", (700, 0), "grass")
    simulation.add_region("forest", (1000, 0), "grass")
    
    # Set initial populations
    simulation.set_population("town_square", 0.30)
    simulation.set_population("market", 0.50)
    simulation.set_population("park", 0.20)
    simulation.set_population("forest", 0.10)
    
    if args.auto_tick:
        simulation.start_auto_tick()
    
    server = HTTPServer((args.host, args.port), LSERequestHandler)
    
    print("=" * 60)
    print("  AURA HTTP Server")
    print("=" * 60)
    print(f"  Listening on: http://{args.host}:{args.port}")
    print(f"  Auto-tick: {'enabled' if args.auto_tick else 'disabled'}")
    print()
    print("  Endpoints:")
    print("    GET  /status              - Server status")
    print("    GET  /regions             - List regions")
    print("    GET  /region/<id>         - Get region state")
    print("    GET  /parameters          - All UE5 parameters")
    print("    GET  /parameters/<id>     - Region UE5 parameters")
    print("    POST /region/<id>/pop     - Set population")
    print("    POST /region/add          - Add new region")
    print("    POST /update              - Tick simulation")
    print("    POST /reset               - Reset simulation")
    print("    POST /auto_tick/start     - Start auto-tick")
    print("    POST /auto_tick/stop      - Stop auto-tick")
    print()
    print("  Press Ctrl+C to stop")
    print("=" * 60)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        simulation.stop_auto_tick()
        server.shutdown()


if __name__ == '__main__':
    main()
