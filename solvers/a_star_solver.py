import heapq
from .base_solver import BaseSolver 

class AStarSolver(BaseSolver):
    def __init__(self, maze_instance): 
        super().__init__(maze_instance)
        self.viz_frontier_heap = []
        self.viz_visited_nodes = set()
        self.viz_came_from = {}
        self._viz_heap_count = 0
        self._viz_initialized_astar = False 
        
        self.use_belief_data = False
        self.belief_data_map = None 
        self.belief_get_neighbors_func = None 

    def _get_neighbors_and_costs_for_astar(self, current_pos):
        if self.use_belief_data and self.belief_get_neighbors_func:
            return self.belief_get_neighbors_func(current_pos, set()) 
        else: 
            return super().get_neighbors_and_costs(current_pos)


    def _core_search_logic(self, start_node, target_node):
        self.came_from = {start_node: None}
        self.cost_so_far = {start_node: 0}

        local_heap = []
        heap_entry_count = 0 
        heapq.heappush(local_heap, 
                       (self.manhattan_heuristic(start_node, target_node), 
                        heap_entry_count, 
                        start_node))
        
        nodes_this_segment = 0
        
        while local_heap:
            f_val, _, current_node = heapq.heappop(local_heap)

            nodes_this_segment += 1

            if current_node == target_node:
                path = self.reconstruct_path_from_came_from(target_node, start_node) 
                cost = self.cost_so_far.get(target_node, float('inf'))
                return path, cost, nodes_this_segment, True

            for neighbor_info in self._get_neighbors_and_costs_for_astar(current_node):
                neighbor_node = neighbor_info['pos']
                cost_to_neighbor_action = neighbor_info['cost']

                new_g_cost_for_neighbor = self.cost_so_far.get(current_node, float('inf')) + cost_to_neighbor_action

                if new_g_cost_for_neighbor < self.cost_so_far.get(neighbor_node, float('inf')):
                    self.cost_so_far[neighbor_node] = new_g_cost_for_neighbor
                    priority_f_cost = new_g_cost_for_neighbor + self.manhattan_heuristic(neighbor_node, target_node)
                    heap_entry_count +=1
                    heapq.heappush(local_heap, (priority_f_cost, heap_entry_count, neighbor_node))
                    self.came_from[neighbor_node] = current_node
        
        return [], float('inf'), nodes_this_segment, False

    def solve_step_visualize(self):
        if not self._viz_initialized_astar:
            self._viz_target = self.exit_pos
            if self.maze.keys: self._viz_target = self.maze.keys[0]

            self.viz_frontier_heap = [] 
            self._viz_heap_count = 0
            # Store (f_cost, count, node)
            initial_g_cost = 0
            initial_h_cost = self.manhattan_heuristic(self.start_pos, self._viz_target)
            heapq.heappush(self.viz_frontier_heap, 
                           (initial_g_cost + initial_h_cost, self._viz_heap_count, self.start_pos))
            
            self.viz_came_from = {self.start_pos: None}
            self.viz_visited_nodes = set() 
            self.viz_cost_so_far_g = {self.start_pos: 0} # Track g-costs for viz

            self.path = []
            self.path_found = False
            self.nodes_expanded = 0
            self._viz_initialized_astar = True

        if not self.viz_frontier_heap:
            self._viz_initialized_astar = False; return True

        _, _, current_viz_pos = heapq.heappop(self.viz_frontier_heap)

        if current_viz_pos in self.viz_visited_nodes : 
            return False if self.viz_frontier_heap else True 

        self.viz_visited_nodes.add(current_viz_pos)
        self.nodes_expanded += 1

        if current_viz_pos == self._viz_target:
            self.path = self.reconstruct_path_from_came_from_dict(current_viz_pos, self.start_pos, self.viz_came_from)
            self.path_found = True
            self._viz_initialized_astar = False; return True

        for neighbor_info in self.get_neighbors_and_costs(current_viz_pos): # Use standard get_neighbors
            neighbor_pos = neighbor_info['pos']
            action_cost = neighbor_info['cost']
            
            new_g_cost = self.viz_cost_so_far_g.get(current_viz_pos, float('inf')) + action_cost

            if new_g_cost < self.viz_cost_so_far_g.get(neighbor_pos, float('inf')):
                self.viz_cost_so_far_g[neighbor_pos] = new_g_cost
                self.viz_came_from[neighbor_pos] = current_viz_pos
                
                h_cost_neighbor = self.manhattan_heuristic(neighbor_pos, self._viz_target)
                f_cost_neighbor = new_g_cost + h_cost_neighbor
                
                self._viz_heap_count += 1
                heapq.heappush(self.viz_frontier_heap, (f_cost_neighbor, self._viz_heap_count, neighbor_pos))
        
        if self.nodes_expanded > self.width * self.height * 1.5: 
             self._viz_initialized_astar = False
             return True
        return False

    # Helper specifically for viz if reconstruction logic differs slightly or uses different dicts
    def reconstruct_path_from_came_from_dict(self, target_node, start_node_of_segment, came_from_dict):
        path_segment = []
        curr = target_node
        while curr != start_node_of_segment:
            if curr is None : return [] 
            path_segment.append(curr)
            if curr not in came_from_dict: return [] 
            prev_node = came_from_dict[curr]
            if prev_node is None and start_node_of_segment is not None : return []
            curr = prev_node
        if start_node_of_segment is not None: path_segment.append(start_node_of_segment)
        path_segment.reverse()
        return path_segment