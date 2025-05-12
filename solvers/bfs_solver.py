from collections import deque
from .base_solver import BaseSolver

class BFSSolver(BaseSolver):
    def __init__(self, maze_instance):
        super().__init__(maze_instance)
        self.viz_frontier = deque()
        self.viz_visited_nodes = set()
        self.viz_came_from = {}   
        self._viz_initialized_bfs = False 

    def _core_search_logic(self, start_node, target_node):
        """
        Finds a path from start_node to target_node using BFS.
        Calculates the cost of the path found. BFS finds shortest path in terms of "hops".
        """
        queue = deque([start_node])
        segment_came_from = {start_node: None}
        segment_cost_to_reach = {start_node: 0}
        
        nodes_expanded_this_segment = 0

        while queue:
            current_node = queue.popleft()
            nodes_expanded_this_segment += 1

            if current_node == target_node:
                path = self.reconstruct_path_from_came_from_dict(target_node, start_node, segment_came_from)
                cost = segment_cost_to_reach.get(target_node, float('inf'))
                return path, cost, nodes_expanded_this_segment, True

            for neighbor_info in self.get_neighbors_and_costs(current_node):
                neighbor_node = neighbor_info['pos']
                action_cost = neighbor_info['cost'] 

                if neighbor_node not in segment_came_from: 
                    segment_came_from[neighbor_node] = current_node
                    current_path_cost_to_current_node = segment_cost_to_reach.get(current_node, 0) 
                    segment_cost_to_reach[neighbor_node] = current_path_cost_to_current_node + action_cost
                    queue.append(neighbor_node)
        
        return [], float('inf'), nodes_expanded_this_segment, False

    def reconstruct_path_from_came_from_dict(self, target_node, start_node_of_segment, came_from_dict):
        """ Helper to reconstruct path using a specific came_from dictionary. """
        path_segment = []
        curr = target_node
        while curr != start_node_of_segment:
            if curr is None: return [] 
            path_segment.append(curr)
            if curr not in came_from_dict: return [] 
            prev_node = came_from_dict[curr]
            if prev_node is None and start_node_of_segment is not None: return []
            curr = prev_node
        
        if start_node_of_segment is not None: 
            path_segment.append(start_node_of_segment)
        path_segment.reverse() 
        return path_segment

    def solve_step_visualize(self):
        """
        Performs one step of BFS visualization for finding a path to the current _viz_target.
        The _viz_target is typically the first key or the exit.
        """
        if not self._viz_initialized_bfs:

            self._viz_target = self.exit_pos 
            if self.maze.keys: 
                uncollected_keys_viz = [k for k in self.maze.keys if k not in (self.path or [])] 
                if uncollected_keys_viz:
                    self._viz_target = uncollected_keys_viz[0]
                elif self.maze.keys and not uncollected_keys_viz : 
                     self._viz_target = self.exit_pos


            self.viz_frontier.clear()
            self.viz_frontier.append(self.start_pos)
            self.viz_came_from = {self.start_pos: None} 
            self.viz_visited_nodes.clear()            
            
            self.path = [] 
            self.path_found = False
            self.nodes_expanded = 0 
            self._viz_initialized_bfs = True

        if not self.viz_frontier: 
            self._viz_initialized_bfs = False 
            return True 

        current_viz_pos = self.viz_frontier.popleft()

        if current_viz_pos in self.viz_visited_nodes:
            return False

        self.viz_visited_nodes.add(current_viz_pos) 
        self.nodes_expanded += 1

        if current_viz_pos == self._viz_target:
            self.path = self.reconstruct_path_from_came_from_dict(current_viz_pos, self.start_pos, self.viz_came_from)
            self.path_found = True 
            self._viz_initialized_bfs = False 
            return True 

        for neighbor_info in self.get_neighbors_and_costs(current_viz_pos):
            neighbor_pos = neighbor_info['pos']
            if neighbor_pos not in self.viz_came_from:
                self.viz_came_from[neighbor_pos] = current_viz_pos 
                self.viz_frontier.append(neighbor_pos)            

        if self.nodes_expanded > (self.width * self.height * 2): #
             self._viz_initialized_bfs = False
             return True 
             
        return False 