import math
import random
from solvers.base_solver import BaseSolver 

class SimulatedAnnealingSolver(BaseSolver):
    def __init__(self, maze_instance, 
                 initial_temp=5000000.0,      
                 cooling_rate=0.9999,     
                 min_temp=0.00001,           
                 max_iterations_per_core_logic=150000, 
                 max_steps_in_segment=None):
        super().__init__(maze_instance) 
        
        self.initial_temp = initial_temp
        self.cooling_rate = cooling_rate
        self.min_temp = min_temp
        self.max_iterations_per_core_logic = max_iterations_per_core_logic
        

        if max_steps_in_segment is None:
            self.max_steps_in_segment = self.maze.width * self.maze.height * 100
        else:
            self.max_steps_in_segment = max_steps_in_segment
            
        self.rand = random.Random() 

    def _get_valid_neighbor_positions(self, pos):
        """
        Lấy danh sách các vị trí (tuple (x,y)) của các ô hàng xóm hợp lệ.
        SA chỉ cần vị trí, không cần chi phí ở bước chọn hàng xóm.
        """
        x, y = pos
        neighbors_pos = []
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]: 
            nx, ny = x + dx, y + dy
            if not self.maze.is_wall(nx, ny):
                neighbors_pos.append((nx, ny))
        return neighbors_pos

    def _calculate_segment_cost(self, path_segment):
        """
        Tính chi phí thực tế của một đoạn đường đi, có xét đến bùn.
        """
        if not path_segment or len(path_segment) < 2:
            return 0
        
        cost = 0
        # Chi phí được tính khi *bước vào* ô mới
        for i in range(1, len(path_segment)):
            node_x, node_y = path_segment[i]
            
            cost_to_step = 1 # Chi phí cơ bản
            if self.maze.is_mud(node_x, node_y):
                cost_to_step = self.maze.MUD_COST_FOR_ALGORITHM

            cost += cost_to_step
        return cost

    def _core_search_logic(self, start_node, target_node):
        """
        Triển khai logic tìm kiếm SA cho một chặng đường từ start_node đến target_node.
        Trả về: (path_segment, total_cost_of_segment, nodes_expanded_in_segment, found_bool)
        """
        current_pos = start_node
        current_energy = self.manhattan_heuristic(current_pos, target_node) 
        
        path_segment = [current_pos] 
        
        temp = self.initial_temp
        iterations = 0 

        while temp > self.min_temp and iterations < self.max_iterations_per_core_logic:
            if current_pos == target_node:
                segment_cost = self._calculate_segment_cost(path_segment)
                return path_segment, segment_cost, iterations, True 

            if len(path_segment) > self.max_steps_in_segment:
                break 

            neighbor_positions = self._get_valid_neighbor_positions(current_pos)
            if not neighbor_positions:
                break 

            next_pos = self.rand.choice(neighbor_positions) 
            next_energy = self.manhattan_heuristic(next_pos, target_node)
            
            delta_energy = next_energy - current_energy

            accepted_move = False
            if delta_energy < 0: 
                accepted_move = True
            elif temp > 1e-9:
                acceptance_probability = math.exp(-delta_energy / temp)
                if self.rand.random() < acceptance_probability:
                    accepted_move = True
            
            if accepted_move:
                current_pos = next_pos
                current_energy = next_energy
                path_segment.append(current_pos) 
            
            temp *= self.cooling_rate 
            iterations += 1
        

        if current_pos == target_node:
            segment_cost = self._calculate_segment_cost(path_segment)
            return path_segment, segment_cost, iterations, True
        

        return None, float('inf'), iterations, False

    def solve_all_stages(self):
        """
        Override phương thức của BaseSolver để phù hợp với SA.
        SA tìm đường tuần tự đến các chìa khóa rồi đến lối ra.
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
                self.path_found = False
                self.path = [] 
                self.total_cost = float('inf')
                return
        if current_start_node_for_stage == self.exit_pos: 
            self.path_found = True

        else: 
            self.path_found = False
            self.total_cost = float('inf')

        
        return self.path_found


    def solve_step_visualize(self):
        """
        Triển khai visualization cho SA.
        Cách đơn giản: chạy toàn bộ một lần và sau đó báo cáo hoàn thành.
        Hoặc, nếu muốn từng bước, cần cấu trúc lại _core_search_logic thành generator.
        """
        if not self.path_found and not hasattr(self, '_sa_visualization_solve_done'):

            self.solve_all_stages() 

            self._sa_visualization_solve_done = True 
            
            if self.path_found:
                self.viz_visited_nodes = set(self.path) 
                if hasattr(self, 'viz_frontier'): self.viz_frontier = None
            else:
                self.viz_visited_nodes = set()

            return True 
        
        return True

