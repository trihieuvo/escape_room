import heapq
from .base_solver import BaseSolver

class GreedySolver(BaseSolver):
    def __init__(self, maze_instance):
        super().__init__(maze_instance)
        # For solve_step_visualize
        self.viz_frontier_heap = [] 
        self.viz_visited_nodes = set()
        self.viz_came_from = {}
        self._viz_heap_count = 0
        self._viz_initialized_greedy = False 


    def _core_search_logic(self, start_node, target_node):
        segment_came_from = {start_node: None}
        segment_cost_to_reach = {start_node: 0} 

        local_heap = []
        heap_entry_count = 0 
        heapq.heappush(local_heap, (self.manhattan_heuristic(start_node, target_node), heap_entry_count, start_node))
        
        nodes_this_segment = 0
        processed_nodes_in_segment = set()

        while local_heap:
            _, _, current_node = heapq.heappop(local_heap)

            if current_node in processed_nodes_in_segment:
                continue 
            processed_nodes_in_segment.add(current_node)
            
            nodes_this_segment += 1

            if current_node == target_node:
                path = self.reconstruct_path_from_came_from_dict(target_node, start_node, segment_came_from)
                cost = segment_cost_to_reach.get(target_node, float('inf'))
                return path, cost, nodes_this_segment, True

            for neighbor_info in self.get_neighbors_and_costs(current_node):
                neighbor_node = neighbor_info['pos']
                cost_to_neighbor = neighbor_info['cost']

                if neighbor_node not in processed_nodes_in_segment: 
                    if neighbor_node not in segment_came_from: 
                        segment_came_from[neighbor_node] = current_node
                        segment_cost_to_reach[neighbor_node] = segment_cost_to_reach.get(current_node,0) + cost_to_neighbor
                    
                    heap_entry_count += 1
                    priority = self.manhattan_heuristic(neighbor_node, target_node)
                    heapq.heappush(local_heap, (priority, heap_entry_count, neighbor_node))
        
        return [], float('inf'), nodes_this_segment, False

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

    def solve_step_visualize(self):
        if not self._viz_initialized_greedy:
            self._viz_target = self.exit_pos
            if self.maze.keys: self._viz_target = self.maze.keys[0]

            self.viz_frontier_heap = [] 
            self._viz_heap_count = 0
            heapq.heappush(self.viz_frontier_heap, (self.manhattan_heuristic(self.start_pos, self._viz_target), self._viz_heap_count, self.start_pos))
            
            self.viz_came_from = {self.start_pos: None}
            self.viz_visited_nodes = set() 

            self.path = []
            self.path_found = False
            self.nodes_expanded = 0
            self._viz_initialized_greedy = True

        if not self.viz_frontier_heap:
            self._viz_initialized_greedy = False; return True

        _, _, current_viz_pos = heapq.heappop(self.viz_frontier_heap)

        if current_viz_pos in self.viz_visited_nodes : 
            return False if self.viz_frontier_heap else True

        self.viz_visited_nodes.add(current_viz_pos)
        self.nodes_expanded += 1

        if current_viz_pos == self._viz_target:
            self.path = self.reconstruct_path_from_came_from_dict(current_viz_pos, self.start_pos, self.viz_came_from)
            self.path_found = True
            self._viz_initialized_greedy = False; return True

        for neighbor_info in self.get_neighbors_and_costs(current_viz_pos):
            neighbor_pos = neighbor_info['pos']
            if neighbor_pos not in self.viz_visited_nodes:

                if neighbor_pos not in self.viz_came_from:
                     self.viz_came_from[neighbor_pos] = current_viz_pos
                

                self._viz_heap_count += 1
                priority = self.manhattan_heuristic(neighbor_pos, self._viz_target)

                heapq.heappush(self.viz_frontier_heap, (priority, self._viz_heap_count, neighbor_pos))
        
        if self.nodes_expanded > self.width * self.height * 1.5: 
             self._viz_initialized_greedy = False
             return True
        return False