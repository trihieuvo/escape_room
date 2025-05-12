import heapq 
from solvers.base_solver import BaseSolver

class LocalBeamSearchSolver(BaseSolver):
    def __init__(self, maze_instance, beam_width_k=1000, max_iterations_per_core_logic=100000):
        super().__init__(maze_instance)
        self.k = beam_width_k
        self.max_iterations = max_iterations_per_core_logic

    def heuristic(self, pos, target_pos):
        """Sử dụng heuristic từ BaseSolver."""
        return self.manhattan_heuristic(pos, target_pos)



    def _core_search_logic(self, start_node, target_node):
        """
        Triển khai Local Beam Search cho một chặng, sử dụng get_neighbors_and_costs.
        Trả về: (path_segment, total_cost_of_segment, nodes_expanded_in_segment, found_bool)
        """

        current_beams = [(self.heuristic(start_node, target_node), start_node, [start_node])]
        
        iterations = 0


        while iterations < self.max_iterations:
            iterations += 1
            all_next_candidate_beams = [] 

            if not current_beams:
                return None, float('inf'), iterations, False


            for h_val, pos, path_hist in current_beams:
                if pos == target_node:

                    cost = self.calculate_total_cost(path_hist) 
                    return path_hist, cost, iterations, True

            generated_next_positions_this_iteration = set() 

            for h_val_curr, current_pos_beam, current_path_beam in current_beams:
                if len(current_path_beam) > self.maze.width * self.maze.height * 2: 
                    continue


                for neighbor_info in self.get_neighbors_and_costs(current_pos_beam):
                    next_pos_after_effect = neighbor_info['pos']
                    if next_pos_after_effect in current_path_beam[-2:]: 
                        continue


                    new_path_for_candidate = current_path_beam + [next_pos_after_effect]
                    h_val_candidate = self.heuristic(next_pos_after_effect, target_node)
                    

                    all_next_candidate_beams.append((h_val_candidate, next_pos_after_effect, new_path_for_candidate))


            if not all_next_candidate_beams:
                return None, float('inf'), iterations, False

            if len(all_next_candidate_beams) > self.k:
                next_beams_selected = heapq.nsmallest(self.k, all_next_candidate_beams, key=lambda x: x[0])
            else:
                next_beams_selected = sorted(all_next_candidate_beams, key=lambda x: x[0]) 
            
            if not next_beams_selected:
                return None, float('inf'), iterations, False

            current_beams = next_beams_selected
            

        return None, float('inf'), iterations, False


    def solve_all_stages(self):
        """
        Override phương thức của BaseSolver.
        LocalBeamSearch tìm đường tuần tự đến các chìa khóa rồi đến lối ra.
        """
        self.path = [self.start_pos]
        self.total_cost = 0
        self.nodes_expanded = 0 
        self.path_found = False

        current_start_node_for_stage = self.start_pos
        keys_in_order = list(self.maze.keys) 
        all_targets_in_sequence = keys_in_order + [self.exit_pos]

        for target_node_for_stage in all_targets_in_sequence:
            path_segment, cost_segment, nodes_segment, found_segment = \
                self._core_search_logic(current_start_node_for_stage, target_node_for_stage)
            
            self.nodes_expanded += nodes_segment

            if found_segment and path_segment:

                self.path.extend(path_segment[1:]) 
                self.total_cost += cost_segment 
                current_start_node_for_stage = path_segment[-1]
            else:
                self.path_found = False; self.path = []; self.total_cost = float('inf')
                return False 

        if current_start_node_for_stage == self.exit_pos:
            self.path_found = True

        else:
            self.path_found = False; self.total_cost = float('inf')
        
        return self.path_found

    def solve_step_visualize(self):
        """
        Triển khai visualization cho LocalBeamSearch.
        Cách đơn giản: chạy toàn bộ một lần và sau đó báo cáo hoàn thành.
        """
        if not self.path_found and not hasattr(self, '_lbs_visualization_solve_done'):
            self.solve_all_stages() 
            self._lbs_visualization_solve_done = True
            
            if self.path_found:
                self.viz_visited_nodes = set(self.path)

            else:
                self.viz_visited_nodes = set()
            return True 
        return True

  