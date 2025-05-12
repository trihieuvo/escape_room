import copy 
from .base_solver import BaseSolver

class CSPBacktrackingFCSolver(BaseSolver):
    def __init__(self, maze_instance):
        super().__init__(maze_instance)
        self.variables = [] 
        self.domains = {}   
        self.constraints = [] 
        self.viz_current_path = []
        self.viz_nodes_evaluated = 0 
        self._csp_solve_complete = False


    def _solve_csp_for_segment(self, current_pos, target_pos, keys_collected_this_segment, all_keys_for_stage):
        """
        Giải quyết một đoạn của bài toán CSP: từ current_pos đến target_pos.
        keys_collected_this_segment: set các chìa khóa đã thu thập trong đoạn này.
        all_keys_for_stage: list các chìa khóa cần thu thập cho toàn bộ giai đoạn (nếu có).
        """
        assignment = {} 
        initial_path = [current_pos]
        

        nodes_evaluated_csp = 0

        MAX_PATH_LEN = self.maze.width * self.maze.height * 2

        memo_fc = {} 

        def solve_recursive_fc(current_path, current_target, collected_keys_on_path, nodes_count):
            nodes_count += 1
            current_node = current_path[-1]
            
            path_tuple = tuple(current_path)
            memo_key = (path_tuple, current_target, tuple(sorted(list(collected_keys_on_path))))
            if memo_key in memo_fc:
                return memo_fc[memo_key], nodes_count

            self.viz_current_path = list(current_path) 
            self.viz_nodes_evaluated = nodes_count

            if current_node == current_target:
                if current_target in all_keys_for_stage and current_target not in collected_keys_on_path:
                    memo_fc[memo_key] = None
                    return None, nodes_count 
                
                memo_fc[memo_key] = current_path
                return list(current_path), nodes_count

            if len(current_path) >= MAX_PATH_LEN: 
                memo_fc[memo_key] = None
                return None, nodes_count

            neighbors_data = self.get_neighbors_and_costs(current_node)
            neighbors_data.sort(key=lambda n_info: self.manhattan_heuristic(n_info['pos'], current_target))

            for neighbor_info in neighbors_data:
                neighbor_pos = neighbor_info['pos']

                if len(current_path) > 1 and neighbor_pos == current_path[-2]:
                    continue
                

                is_target_key_not_collected = (neighbor_pos == current_target and 
                                               neighbor_pos in all_keys_for_stage and 
                                               neighbor_pos not in collected_keys_on_path)
                is_final_exit_target = (neighbor_pos == current_target and 
                                       current_target == self.exit_pos and 
                                       (not all_keys_for_stage or 
                                        all(k in collected_keys_on_path for k in all_keys_for_stage if k != self.exit_pos))) 


                if neighbor_pos in current_path and not (is_target_key_not_collected or is_final_exit_target):
                    continue


                new_collected_keys = set(collected_keys_on_path)
                is_potential_key_pickup = False
                if neighbor_pos in all_keys_for_stage and neighbor_pos not in new_collected_keys:
                    new_collected_keys.add(neighbor_pos)
                    is_potential_key_pickup = True

                result_path, nodes_count = solve_recursive_fc(current_path + [neighbor_pos], 
                                                              current_target, 
                                                              new_collected_keys, 
                                                              nodes_count)
                if result_path:
                    memo_fc[memo_key] = result_path
                    return result_path, nodes_count
            
            memo_fc[memo_key] = None
            return None, nodes_count

        solution_path, nodes_evaluated_this_segment = solve_recursive_fc(
            initial_path, target_pos, keys_collected_this_segment, 0
        )
        
        if solution_path:
            cost = self.calculate_total_cost(solution_path)
            return solution_path, cost, nodes_evaluated_this_segment, True
        else:
            return [], float('inf'), nodes_evaluated_this_segment, False


    def _core_search_logic(self, start_node, target_node):
        """
        Called by BaseSolver.solve_all_stages for one segment.
        `target_node` is either a key or the exit.
        """
        keys_relevant_to_this_segment = []
        if target_node in self.maze.keys: 
            keys_relevant_to_this_segment = [target_node]


        path_segment, cost_segment, nodes_evaluated, found = self._solve_csp_for_segment(
            start_node, 
            target_node, 
            set(), 
            keys_relevant_to_this_segment 
        )

        return path_segment, cost_segment, nodes_evaluated, found


    def solve_all_stages(self):
        self.variables = []
        self.domains = {}
        self.constraints = []
        self.viz_current_path = []
        self.viz_nodes_evaluated = 0
        self._csp_solve_complete = False
        self.path = []
        self.total_cost = 0
        self.nodes_expanded = 0 
        self.path_found = False

        super().solve_all_stages() 
        self._csp_solve_complete = True


    def solve_step_visualize(self):
        if not self._csp_solve_complete and not self.path_found:
            if not hasattr(self, '_csp_viz_has_run_once'):
                self.solve_all_stages() 
                self._csp_viz_has_run_once = True

            if self.path_found:
                self.viz_visited_nodes = set(self.path)
            else: 
                self.viz_visited_nodes = set(self.viz_current_path)

            self.nodes_expanded = self.viz_nodes_evaluated 


            if self.viz_nodes_evaluated > self.width * self.height * 50: 
                self._csp_solve_complete = True
                print("CSP viz safety limit reached.")
                return True

            return not self.path_found 

        return True


    def calculate_total_cost(self, path_nodes):
        return super().calculate_total_cost(path_nodes)