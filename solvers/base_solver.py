from abc import ABC, abstractmethod
import heapq 
from constants import MUD_COST_ALGO, PORTAL_COST_ALGO, SLIDE_CELL_COST_ALGO

class BaseSolver(ABC):
    def __init__(self, maze_instance):
        self.maze = maze_instance # Keep a reference to the full Maze object
        if self.maze:
            self.width = self.maze.width
            self.height = self.maze.height
            self.start_pos = self.maze.start_pos
            self.exit_pos = self.maze.exit_pos
            # Keys are fetched from self.maze.keys when a solve starts
        else:
            self.width = 0
            self.height = 0
            self.start_pos = None
            self.exit_pos = None

        # Results
        self.path = []
        self.total_cost = 0
        self.nodes_expanded = 0 # Cumulative for all search stages in a solve_all call
        self.path_found = False
        
        # Temporary structures for a single _core_search_logic call, reset each time
        self.came_from = {}
        self.cost_so_far = {} # Cost from start_node of the current core search segment

    def _get_slide_endpoint_and_cost_factor(self, water_entry_x, water_entry_y, entry_dx, entry_dy):
        # ... (logic trượt nước) ...
        cx, cy = water_entry_x, water_entry_y 
        slid_cells_count = 0 
        while True:
            next_cx = cx + entry_dx
            next_cy = cy + entry_dy
            if self.maze.is_wall(next_cx, next_cy): 
                return (cx, cy), slid_cells_count 
            elif not self.maze.is_water(next_cx, next_cy): 
                slid_cells_count += 1 
                return (next_cx, next_cy), slid_cells_count
            else: 
                cx, cy = next_cx, next_cy
                slid_cells_count += 1

    def get_neighbors_and_costs(self, current_pos):
        x, y = current_pos
        potential_neighbors = []
        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]: 
            next_x, next_y = x + dx, y + dy
            if self.maze.is_wall(next_x, next_y):
                continue
            cost_to_step_onto_next_tile = 1
            if self.maze.is_mud(next_x, next_y): 
                cost_to_step_onto_next_tile = self.maze.MUD_COST_FOR_ALGORITHM
            if self.maze.is_water(next_x, next_y):
                land_pos, num_slid_cells = self._get_slide_endpoint_and_cost_factor(next_x, next_y, dx, dy)
                slide_travel_cost = num_slid_cells * self.maze.SLIDE_CELL_COST_FOR_ALGORITHM
                total_move_cost = cost_to_step_onto_next_tile + slide_travel_cost
                potential_neighbors.append({'pos': land_pos, 'cost': total_move_cost})
            elif self.maze.is_portal(next_x, next_y):
                portal_target_pos = self.maze.get_portal_target(next_x, next_y)
                if portal_target_pos:
                    portal_usage_cost = self.maze.PORTAL_COST_FOR_ALGORITHM
                    total_move_cost = cost_to_step_onto_next_tile + portal_usage_cost
                    potential_neighbors.append({'pos': portal_target_pos, 'cost': total_move_cost})
                else: 
                    potential_neighbors.append({'pos': (next_x, next_y), 'cost': cost_to_step_onto_next_tile})
            else: 
                potential_neighbors.append({'pos': (next_x, next_y), 'cost': cost_to_step_onto_next_tile})
        return potential_neighbors

    def reconstruct_path_from_came_from(self, target_node, start_node_of_segment):
        # ... (logic tái tạo đường đi) ...
        path_segment = []
        curr = target_node
        while curr != start_node_of_segment:
            if curr is None: return [] 
            path_segment.append(curr)
            if curr not in self.came_from: return [] 
            curr = self.came_from[curr]
            if curr is None and start_node_of_segment is not None : return []
        if start_node_of_segment is not None: path_segment.append(start_node_of_segment)
        path_segment.reverse()
        return path_segment

    def manhattan_heuristic(self, pos_a, pos_b):
        return abs(pos_a[0] - pos_b[0]) + abs(pos_a[1] - pos_b[1])

    def solve_all_stages(self): 

        self.path = [self.start_pos] 
        self.total_cost = 0
        self.nodes_expanded = 0 
        self.path_found = False 
        current_pos_in_sequence = self.start_pos
        keys_to_collect = list(self.maze.keys) 
        while keys_to_collect:
            best_key_to_target = None
            path_to_chosen_key = []
            cost_to_chosen_key = float('inf')
            nodes_for_current_evaluation_round = 0
            for key_loc in keys_to_collect:
                temp_path, temp_cost, temp_nodes, temp_found = self._core_search_logic(current_pos_in_sequence, key_loc) 
                nodes_for_current_evaluation_round += temp_nodes 
                if temp_found and temp_cost < cost_to_chosen_key:
                    cost_to_chosen_key = temp_cost
                    best_key_to_target = key_loc
                    path_to_chosen_key = temp_path
            self.nodes_expanded += nodes_for_current_evaluation_round 
            if best_key_to_target is None: 
                self.path_found = False; return 
            self.path.extend(path_to_chosen_key[1:]) 
            self.total_cost += cost_to_chosen_key
            current_pos_in_sequence = best_key_to_target
            keys_to_collect.remove(best_key_to_target)
        final_path_segment, final_cost_segment, final_nodes_segment, final_found = \
            self._core_search_logic(current_pos_in_sequence, self.exit_pos) 
        self.nodes_expanded += final_nodes_segment 
        if final_found:
            self.path.extend(final_path_segment[1:])
            self.total_cost += final_cost_segment
            self.path_found = True
        else:
            self.path_found = False 

    def calculate_total_cost(self, path_nodes):
        """
        Calculates the actual cost of a given path segment, considering terrain.
        This should be used by subclasses if they construct paths directly.
        """
        if not path_nodes or len(path_nodes) < 2:
            return 0
        
        current_cost = 0
        for i in range(1, len(path_nodes)):
            prev_node = path_nodes[i-1] # Ô trước đó
            current_node_in_path = path_nodes[i] 
            cost_to_enter_current_node = 1 
            if self.maze.is_mud(current_node_in_path[0], current_node_in_path[1]):
                cost_to_enter_current_node = self.maze.MUD_COST_FOR_ALGORITHM
            current_cost += cost_to_enter_current_node
        return current_cost

    @abstractmethod
    def _core_search_logic(self, start_node, target_node):
        pass

    @abstractmethod
    def solve_step_visualize(self):
        pass

    def get_solver_results(self):
        return {
            "name": self.__class__.__name__.replace("Solver", ""), # THÊM DÒNG NÀY ĐỂ CÓ TÊN
            "path_found": self.path_found,
            "path": self.path,
            "cost": self.total_cost,
            "nodes_expanded": self.nodes_expanded,
            "steps": len(self.path) - 1 if self.path_found and self.path else 0, # THÊM DÒNG NÀY
        }