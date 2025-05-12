# solvers/spo_solver.py
import random
import pygame
import heapq
from collections import deque # Có thể cần cho sub-planner
from .base_solver import BaseSolver
# Giả sử chúng ta dùng A* làm sub-planner trên belief map
from .a_star_solver import AStarSolver # Bạn cần tạo file này, hoặc dùng lại BFS/Greedy cho sub-planner
from constants import MUD_COST_ALGO, PORTAL_COST_ALGO, SLIDE_CELL_COST_ALGO

# Trạng thái của một ô trong belief map
UNKNOWN = -1
BELIEF_WALL = 1
BELIEF_PATH = 0
# (Có thể thêm BELIEF_MUD, BELIEF_KEY, etc. nếu muốn agent ghi nhớ chi tiết hơn)

class SPOSolver(BaseSolver):
    def __init__(self, maze_instance, observation_range=20, max_planning_steps=500000):
        super().__init__(maze_instance)
        self.observation_range = observation_range # Agent nhìn được bao xa (1 = chỉ các ô kề)
        self.max_planning_steps = max_planning_steps # Giới hạn cho mỗi lần sub-planning

        # Belief state
        self.belief_maze_data = [[UNKNOWN for _ in range(self.width)] for _ in range(self.height)]
        self.belief_keys = set() # Các chìa khóa agent đã "thấy"
        self.belief_exit_pos = None # Lối ra agent đã "thấy"
        self.belief_mud = set()
        self.belief_water = set() # Agent có thể không biết slide dẫn đi đâu ban đầu
        self.belief_portals = {} # Agent có thể không biết portal dẫn đi đâu ban đầu

        self.agent_current_pos = self.start_pos
        self.agent_keys_collected_belief = set() # Những chìa khóa agent tin rằng mình đã thu thập

        # Các ô đã được agent ghé thăm
        self.visited_by_agent = {self.start_pos}

        # Cho việc visualize
        self.viz_belief_map_surface = None # Sẽ được tạo khi cần
        self._spo_solve_complete = False

        # Sub-planner (ví dụ: A* hoặc BFS đơn giản để chạy trên belief map)
        # Chúng ta cần một cách để tạo một "Maze-like" object từ belief map
        # cho sub-planner. Hoặc sub-planner có thể trực tiếp làm việc với belief_data.
        # For simplicity, let's assume sub-planner can take belief_data.
        # If using a full solver class, it needs careful instantiation.
        # self.sub_planner = AStarSolver(None) # Sẽ cần cách để cập nhật "maze" cho nó


    def _update_belief_map(self):
        """Agent observes its surroundings and updates its belief map."""
        x, y = self.agent_current_pos
        
        # Luôn cập nhật ô hiện tại (nếu chưa)
        if self.belief_maze_data[y][x] == UNKNOWN:
            if self.maze.is_wall(x,y): # Điều này không nên xảy ra nếu agent di chuyển hợp lệ
                 self.belief_maze_data[y][x] = BELIEF_WALL
            else:
                self.belief_maze_data[y][x] = BELIEF_PATH
                if self.maze.is_key(x,y): self.belief_keys.add((x,y))
                if self.maze.is_mud(x,y): self.belief_mud.add((x,y))
                if self.maze.is_water(x,y): self.belief_water.add((x,y)) # Agent thấy nước
                if self.maze.is_portal(x,y): # Agent thấy portal
                    # Agent chưa biết portal dẫn đi đâu cho đến khi bước vào
                    if (x,y) not in self.belief_portals:
                        self.belief_portals[(x,y)] = {'target': None, 'observed': True}
                if (x,y) == self.maze.exit_pos: self.belief_exit_pos = (x,y)


        # Quan sát các ô trong phạm vi
        for r_y in range(-self.observation_range, self.observation_range + 1):
            for r_x in range(-self.observation_range, self.observation_range + 1):
                # if abs(r_x) + abs(r_y) > self.observation_range: continue # Cho hình thoi

                obs_x, obs_y = x + r_x, y + r_y

                if 0 <= obs_x < self.width and 0 <= obs_y < self.height:
                    if self.belief_maze_data[obs_y][obs_x] == UNKNOWN: # Chỉ cập nhật nếu chưa biết
                        if self.maze.is_wall(obs_x, obs_y):
                            self.belief_maze_data[obs_y][obs_x] = BELIEF_WALL
                        else:
                            self.belief_maze_data[obs_y][obs_x] = BELIEF_PATH
                            # Agent "thấy" các thuộc tính của ô path đó
                            if self.maze.is_key(obs_x, obs_y): self.belief_keys.add((obs_x, obs_y))
                            if self.maze.is_mud(obs_x, obs_y): self.belief_mud.add((obs_x, obs_y))
                            if self.maze.is_water(obs_x, obs_y): self.belief_water.add((obs_x, obs_y))
                            if self.maze.is_portal(obs_x, obs_y):
                                if (obs_x,obs_y) not in self.belief_portals:
                                     self.belief_portals[(obs_x,obs_y)] = {'target': None, 'observed': True}
                            if (obs_x, obs_y) == self.maze.exit_pos: self.belief_exit_pos = (obs_x, obs_y)


    def _get_belief_neighbors_and_costs(self, pos, current_keys_collected_belief):
        """
        Giống get_neighbors_and_costs của BaseSolver, nhưng hoạt động trên belief_map.
        Chi phí ở đây có thể là 1 cho mỗi bước di chuyển trên belief_path.
        """
        x, y = pos
        neighbors = []
        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            next_x, next_y = x + dx, y + dy

            if not (0 <= next_x < self.width and 0 <= next_y < self.height):
                continue
            
            # Kiểm tra belief map
            if self.belief_maze_data[next_y][next_x] == BELIEF_WALL:
                continue
            if self.belief_maze_data[next_y][next_x] == UNKNOWN: # Agent không thể đi vào ô chưa biết
                continue

            # Nếu là BELIEF_PATH
            cost = 1 # Chi phí cơ bản
            actual_next_pos_after_effect = (next_x, next_y) # Vị trí sau khi hiệu ứng (nếu có)

            if (next_x, next_y) in self.belief_mud:
                cost = MUD_COST_ALGO # Sử dụng chi phí thật nếu biết là bùn

            # Xử lý portal và water phức tạp hơn trong SPO
            # vì agent có thể chưa biết điểm đến của chúng.
            # Cách 1: Nếu portal/water đã được agent "trải nghiệm", nó biết điểm đến.
            # Cách 2: Agent coi việc bước vào portal/water chưa biết là một rủi ro/chi phí cao.
            # Cách 3 (đơn giản nhất cho sub-planner): Nếu chưa biết, coi như không thể dùng
            #           hoặc chỉ đi được tới ô portal/water đó, không biết hiệu ứng.

            if (next_x, next_y) in self.belief_portals:
                portal_info = self.belief_portals.get((next_x,next_y))
                if portal_info and portal_info.get('target'): # Nếu đã biết target
                    actual_next_pos_after_effect = portal_info['target']
                    cost += PORTAL_COST_ALGO
                # else: agent chưa biết portal dẫn đi đâu, không thêm vào neighbor cho sub-planning
                #       hoặc coi như chỉ đến được ô portal đó.
                #       For now, let's assume if target not known, it just lands on portal.

            if (next_x, next_y) in self.belief_water:
                # Tương tự portal, nếu agent đã trượt qua đây, nó có thể nhớ điểm đến.
                # Nếu không, nó chỉ biết đó là nước.
                # Đây là phần phức tạp: agent cần nhớ lại "kinh nghiệm"
                # Hiện tại, để đơn giản, sub-planner chỉ coi ô nước là 1 ô bình thường
                # và việc trượt sẽ do `_take_step_on_actual_maze` xử lý.
                # Hoặc, nếu agent đã "trải nghiệm" một đường trượt cụ thể, nó có thể lưu lại.
                pass # Để đơn giản, chưa xử lý slide trong belief_neighbors


            neighbors.append({'pos': actual_next_pos_after_effect, 'cost': cost})
        return neighbors

    def _plan_on_belief_map_bfs(self, start_pos, target_pos_list):
        """
        Sử dụng BFS đơn giản trên belief map để tìm đường đến một trong các target_pos.
        Trả về path ngắn nhất (theo số bước trên belief map) và điểm target đạt được.
        """
        if not isinstance(target_pos_list, list): target_pos_list = [target_pos_list]
        
        q = deque([(start_pos, [start_pos])])
        visited_in_plan = {start_pos}
        
        nodes_expanded_this_plan = 0

        while q:
            nodes_expanded_this_plan +=1
            if nodes_expanded_this_plan > self.max_planning_steps : # Giới hạn
                return None, None, nodes_expanded_this_plan

            curr, path = q.popleft()

            if curr in target_pos_list:
                return path, curr, nodes_expanded_this_plan

            # Sử dụng _get_belief_neighbors_and_costs
            # Chú ý: current_keys_collected_belief không dùng trong BFS đơn giản này
            # nhưng có thể cần nếu sub-planner phức tạp hơn.
            for neighbor_info in self._get_belief_neighbors_and_costs(curr, self.agent_keys_collected_belief):
                neighbor_pos = neighbor_info['pos']
                if neighbor_pos not in visited_in_plan:
                    visited_in_plan.add(neighbor_pos)
                    q.append((neighbor_pos, path + [neighbor_pos]))
        return None, None, nodes_expanded_this_plan


    def _choose_target(self):
        """
        Agent quyết định mục tiêu tiếp theo:
        1. Chìa khóa chưa thu thập gần nhất (trong belief map).
        2. Lối ra (nếu tất cả chìa khóa đã thu thập).
        3. Ô UNKNOWN gần nhất (để khám phá).
        """
        # Ưu tiên 1: Chìa khóa chưa thu thập trong tầm nhìn
        uncollected_belief_keys = list(self.belief_keys - self.agent_keys_collected_belief)
        if uncollected_belief_keys:
            # Tìm đường đến chìa khóa gần nhất trên belief map
            # (Có thể dùng _plan_on_belief_map_bfs để đánh giá khả năng tiếp cận)
            # Đây là một sub-problem phức tạp (TSP-like nếu có nhiều chìa khóa)
            # Cách đơn giản: chọn chìa khóa có heuristic Manhattan gần nhất
            # rồi thử lập kế hoạch đến nó.
            uncollected_belief_keys.sort(key=lambda k: self.manhattan_heuristic(self.agent_current_pos, k))
            for key_target in uncollected_belief_keys:
                 # sub_path, _, _ = self._plan_on_belief_map_bfs(self.agent_current_pos, key_target)
                 # if sub_path: return key_target, "KEY" # Trả về mục tiêu và loại
                 return key_target, "KEY" # Thử target chìa khóa gần nhất theo heuristic
            # Nếu không chìa khóa nào tiếp cận được, chuyển sang khám phá

        # Ưu tiên 2: Lối ra (nếu đã thu thập đủ chìa khóa THEO NIỀM TIN)
        # Và lối ra đã được nhìn thấy
        # Số chìa khóa YÊU CẦU THỰC SỰ là self.maze.get_total_keys_placed()
        # Agent có thể chưa biết con số này! Nó chỉ biết số chìa khóa nó thấy.
        # Giả sử agent biết cần bao nhiêu chìa khóa (ví dụ: bằng cách đếm số chìa khóa nó thấy được)
        
        # Nếu agent tin rằng nó đã thu thập đủ chìa khóa (dựa trên những gì nó thấy)
        # VÀ nó đã nhìn thấy lối ra:
        # Số chìa khóa cần = len(self.belief_keys) nếu belief_keys chứa tất cả chìa khóa thật
        # Điều này phức tạp. Để đơn giản: nếu agent thấy lối ra VÀ không còn thấy chìa khóa nào chưa lấy
        if self.belief_exit_pos and not uncollected_belief_keys:
            # Cần đảm bảo agent đã lấy đủ chìa khóa THỰC SỰ
            # Giả sử game cho agent biết khi nào đủ chìa khóa (ví dụ: HUD)
            # Hoặc, nếu chúng ta muốn SPO tự quyết định, nó phải khám phá đến khi
            # tin rằng đã thấy hết chìa khóa.
            # Hiện tại, nếu không còn uncollected_belief_keys và thấy exit, thì đi đến exit.
            if len(self.agent_keys_collected_belief) >= len(self.belief_keys) and len(self.belief_keys) > 0:
                 # Hoặc một điều kiện khác để quyết định khi nào đi đến exit
                 return self.belief_exit_pos, "EXIT"
            # Nếu chỉ có exit mà không có key nào, game đơn giản.
            if not self.belief_keys and self.belief_exit_pos:
                 return self.belief_exit_pos, "EXIT"


        # Ưu tiên 3: Khám phá ô UNKNOWN gần nhất
        # Tìm tất cả các ô UNKNOWN kề với các ô PATH đã biết
        exploration_candidates = []
        for r in range(self.height):
            for c in range(self.width):
                if self.belief_maze_data[r][c] == UNKNOWN:
                    # Kiểm tra xem có ô PATH đã biết nào kề không
                    is_adjacent_to_known_path = False
                    for dr, dc in [(0,1),(0,-1),(1,0),(-1,0)]:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < self.height and 0 <= nc < self.width and \
                           self.belief_maze_data[nr][nc] == BELIEF_PATH:
                            is_adjacent_to_known_path = True; break
                    if is_adjacent_to_known_path:
                        exploration_candidates.append( (c,r) ) # (x,y)
        
        if exploration_candidates:
            exploration_candidates.sort(key=lambda pos: self.manhattan_heuristic(self.agent_current_pos, pos))
            # Trả về ô khám phá gần nhất theo Manhattan
            # Việc lập kế hoạch đến nó sẽ diễn ra sau.
            return exploration_candidates[0], "EXPLORE"

        return None, None # Không còn gì để làm

    def _take_step_on_actual_maze(self, next_pos_in_sub_plan):
        """
        Agent cố gắng di chuyển đến next_pos_in_sub_plan trên MÊ CUNG THẬT.
        Cập nhật vị trí agent, chi phí, và các hiệu ứng (mud, water, portal).
        """
        cost_of_this_step = 0
        
        # Kiểm tra xem bước đi có hợp lệ trên MÊ CUNG THẬT không
        # (next_pos_in_sub_plan được tính từ belief map, có thể sai)
        # Agent chỉ có thể di chuyển 1 ô kề mỗi "bước vật lý"
        dx = next_pos_in_sub_plan[0] - self.agent_current_pos[0]
        dy = next_pos_in_sub_plan[1] - self.agent_current_pos[1]

        if abs(dx) > 1 or abs(dy) > 1 or (abs(dx)==1 and abs(dy)==1):
             # Lập kế hoạch trên belief map có thể tạo ra bước nhảy nếu portal/slide
             # được xử lý trong _get_belief_neighbors_and_costs.
             # Nếu _get_belief_neighbors_and_costs chỉ trả về ô kề, thì đây là lỗi.
             # Hiện tại, _get_belief_neighbors_and_costs có thể trả về điểm đến của portal đã biết.
             # Nếu next_pos_in_sub_plan là điểm đến của portal từ ô kề:
             potential_entry_to_special_tile = None
             for dr, dc in [(0,1),(0,-1),(1,0),(-1,0)]:
                 check_x, check_y = self.agent_current_pos[0] + dr, self.agent_current_pos[1] + dc
                 if self.maze.is_portal(check_x, check_y) and \
                    self.maze.get_portal_target(check_x, check_y) == next_pos_in_sub_plan:
                     potential_entry_to_special_tile = (check_x, check_y)
                     dx_actual, dy_actual = dr, dc # Hướng đi vào ô portal
                     break
                 # Tương tự cho water slide nếu sub-planner biết trước
             
             if potential_entry_to_special_tile:
                 actual_tile_stepped_on = potential_entry_to_special_tile
             else: # Bước đi không hợp lệ (quá xa mà không phải portal/slide đã biết)
                 # Agent "đập đầu vào tường" (tường tưởng tượng hoặc giới hạn vật lý)
                 # Không di chuyển, không tốn chi phí. Quan sát sẽ cập nhật belief.
                 # print(f"SPO: Belief map plan led to invalid physical step from {self.agent_current_pos} to {next_pos_in_sub_plan}")
                 return 0 # Không có chi phí, không di chuyển
        else: # Di chuyển 1 ô kề
            actual_tile_stepped_on = next_pos_in_sub_plan
            dx_actual, dy_actual = dx, dy


        # Bây giờ, xử lý hiệu ứng trên MÊ CUNG THẬT tại actual_tile_stepped_on
        target_x, target_y = actual_tile_stepped_on

        if self.maze.is_wall(target_x, target_y):
            # Agent "đập đầu vào tường" THẬT. Belief map của nó sai.
            # Không di chuyển, không chi phí. Quan sát sẽ cập nhật.
            self.belief_maze_data[target_y][target_x] = BELIEF_WALL # Cập nhật ngay lập tức
            return 0 

        cost_of_this_step = 1 # Chi phí cơ bản để bước vào ô
        if self.maze.is_mud(target_x, target_y):
            cost_of_this_step = self.maze.MUD_COST_FOR_ALGORITHM
            self.belief_mud.add((target_x, target_y)) # Cập nhật belief nếu chưa

        final_pos_after_effects = (target_x, target_y)

        if self.maze.is_water(target_x, target_y):
            # Agent trượt trên nước. Tìm điểm đến cuối cùng.
            land_pos, num_slid_cells = self._get_slide_endpoint_and_cost_factor(target_x, target_y, dx_actual, dy_actual)
            cost_of_this_step += num_slid_cells * self.maze.SLIDE_CELL_COST_FOR_ALGORITHM
            final_pos_after_effects = land_pos
            # Agent bây giờ "biết" về đường trượt này (có thể lưu lại)
            # print(f"SPO: Slid from ({target_x},{target_y}) to {final_pos_after_effects}")

        elif self.maze.is_portal(target_x, target_y):
            portal_target = self.maze.get_portal_target(target_x, target_y)
            if portal_target:
                cost_of_this_step += self.maze.PORTAL_COST_FOR_ALGORITHM
                final_pos_after_effects = portal_target
                # Agent bây giờ biết portal này dẫn đi đâu
                self.belief_portals[(target_x,target_y)] = {'target': portal_target, 'observed': True}
                # print(f"SPO: Portaled from ({target_x},{target_y}) to {final_pos_after_effects}")
            # else portal hỏng, agent chỉ đứng trên ô portal

        # Cập nhật vị trí THỰC TẾ của agent
        self.agent_current_pos = final_pos_after_effects
        self.visited_by_agent.add(self.agent_current_pos)

        # Nếu agent đáp xuống một chìa khóa
        if self.maze.is_key(self.agent_current_pos[0], self.agent_current_pos[1]):
            # Agent "thu thập" chìa khóa này (trong thực tế và trong belief)
            key_loc = self.agent_current_pos
            self.belief_keys.add(key_loc) # Đảm bảo nó trong belief_keys
            if key_loc not in self.agent_keys_collected_belief:
                 self.agent_keys_collected_belief.add(key_loc)
                 # print(f"SPO: Collected key at {key_loc}")
                 # Xóa chìa khóa khỏi maze thật (nếu logic game yêu cầu)
                 # self.maze.remove_key(key_loc[0], key_loc[1]) # SPO không nên sửa maze thật
        
        return cost_of_this_step


    def solve_all_stages(self):
        self.path = [self.start_pos] # Đường đi thực tế của agent
        self.total_cost = 0
        self.nodes_expanded = 0 # Số chu kỳ lập kế hoạch/hành động
        self.path_found = False
        self.agent_current_pos = self.start_pos
        self._update_belief_map() # Quan sát ban đầu

        max_game_steps = self.maze.width * self.maze.height * 5 # Giới hạn tổng số bước
        num_game_steps = 0

        while num_game_steps < max_game_steps:
            num_game_steps += 1
            self.nodes_expanded += 1 # Mỗi vòng lặp là một "nút" quyết định của SPO

            # 1. Agent chọn mục tiêu dựa trên belief map
            target_pos, target_type = self._choose_target()

            if target_pos is None:
                # print("SPO: No target chosen, agent stuck or finished exploring everything it can.")
                break # Không còn gì để làm

            # 2. Agent lập kế hoạch trên belief map để đến mục tiêu
            # Mục tiêu có thể là ô để khám phá, nên target_pos là ô đó.
            sub_plan_path, _, plan_nodes = self._plan_on_belief_map_bfs(self.agent_current_pos, target_pos)
            # self.nodes_expanded += plan_nodes # Cộng dồn các nút mở rộng của sub-planner

            if not sub_plan_path or len(sub_plan_path) < 2:
                # Không tìm thấy đường trên belief map (có thể do belief sai hoặc target bị cô lập)
                # Agent cần làm gì đó khác, ví dụ: chọn target khám phá khác,
                # hoặc đánh dấu target hiện tại là không thể tiếp cận tạm thời.
                # print(f"SPO: Could not plan path on belief map to {target_pos} from {self.agent_current_pos}")
                # Để đơn giản, nếu không lập kế hoạch được, agent sẽ cố gắng di chuyển ngẫu nhiên
                # trên các ô kề đã biết là PATH trong belief map.
                
                # Lấy các ô kề là PATH trong belief
                possible_random_moves = []
                for dx_rand, dy_rand in [(0,1),(0,-1),(1,0),(-1,0)]:
                    nx_rand, ny_rand = self.agent_current_pos[0] + dx_rand, self.agent_current_pos[1] + dy_rand
                    if 0 <= nx_rand < self.width and 0 <= ny_rand < self.height and \
                       self.belief_maze_data[ny_rand][nx_rand] == BELIEF_PATH:
                        possible_random_moves.append((nx_rand, ny_rand))
                
                if possible_random_moves:
                    next_actual_step = random.choice(possible_random_moves)
                else: # Bị kẹt hoàn toàn
                    # print(f"SPO: Agent completely stuck at {self.agent_current_pos}, no random moves on belief map.")
                    break
            else:
                next_actual_step = sub_plan_path[1] # Bước đi tiếp theo trong kế hoạch con

            # 3. Agent thực hiện bước đi trên MÊ CUNG THẬT
            cost_this_step = self._take_step_on_actual_maze(next_actual_step)
            self.total_cost += cost_this_step
            self.path.append(self.agent_current_pos) # Thêm vị trí mới sau hiệu ứng

            # 4. Agent quan sát lại
            self._update_belief_map()

            # 5. Kiểm tra điều kiện thắng
            # Agent phải ở vị trí exit VÀ đã thu thập đủ số chìa khóa THỰC TẾ
            # SPO không biết trước số chìa khóa thực tế. Nó phải khám phá.
            # Điều kiện thắng cho SPO là: ở exit VÀ (số key đã lấy == tổng số key trên map)
            
            # Giả sử agent biết tổng số key cần lấy là self.maze.get_total_keys_placed()
            # (Trong một kịch bản SPO thuần túy hơn, nó sẽ không biết điều này)
            num_keys_required = self.maze.get_total_keys_placed()
            if self.agent_current_pos == self.maze.exit_pos and \
               len(self.agent_keys_collected_belief) >= num_keys_required:
                self.path_found = True
                # print(f"SPO: Path found! Cost: {self.total_cost}, Steps: {len(self.path)-1}")
                break
        
        self._spo_solve_complete = True
        return self.path_found


    def solve_step_visualize(self):
        """
        Visualize SPO: Chạy N bước của solve_all_stages hoặc chỉ một bước.
        Sau đó cập nhật self.viz_belief_map_surface.
        """
        if not self.path_found and not self._spo_solve_complete:
            # Chạy một vài "chu kỳ quyết định" của agent cho mỗi bước viz
            # Hoặc đơn giản là chạy toàn bộ solve_all_stages và sau đó chỉ hiển thị kết quả
            # Để khớp với cấu trúc hiện tại, có lẽ nên chạy toàn bộ.
            self.solve_all_stages() # Điều này sẽ điền self.path và self.total_cost
        
        # Sau khi solve_all_stages chạy (dù hoàn thành hay không),
        # chúng ta có thể hiển thị belief map cuối cùng.
        # `viz_visited_nodes` có thể là các ô trong `self.path`
        # `viz_frontier` có thể là các ô `UNKNOWN` kề với `BELIEF_PATH`

        self.viz_visited_nodes = set(self.path) # Các ô agent đã đi qua
        
        # Tạo frontier cho viz là các ô UNKNOWN kề với BELIEF_PATH
        frontier_for_viz = set()
        for r in range(self.height):
            for c in range(self.width):
                if self.belief_maze_data[r][c] == UNKNOWN:
                    for dr, dc in [(0,1),(0,-1),(1,0),(-1,0)]:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < self.height and 0 <= nc < self.width and \
                           self.belief_maze_data[nr][nc] == BELIEF_PATH:
                            frontier_for_viz.add((c,r)); break
        
        # Truyền frontier này cho AlgorithmRunner nếu nó hỗ trợ (hiện tại không trực tiếp)
        # Hack: gán vào một thuộc tính mà AlgorithmRunner có thể đọc
        if hasattr(self, 'viz_frontier'): # Nếu BaseSolver hoặc AlgoRunner có
             if isinstance(self.viz_frontier, deque):
                 self.viz_frontier = deque(list(frontier_for_viz))
             elif isinstance(self.viz_frontier, list): # Giả sử là heap
                 self.viz_frontier_heap = [(0, i, pos) for i,pos in enumerate(list(frontier_for_viz))]


        return True # Báo cho AlgorithmRunner là "xong" với bước visualize này

    def draw_belief_map(self, surface, cell_size):
        """Vẽ belief map của agent lên một surface riêng (ví dụ: ở góc màn hình)."""
        if self.viz_belief_map_surface is None or \
           self.viz_belief_map_surface.get_size() != (self.width * cell_size, self.height * cell_size):
            self.viz_belief_map_surface = pygame.Surface((self.width * cell_size, self.height * cell_size))

        self.viz_belief_map_surface.fill((50,50,50)) # Nền cho belief map

        for r in range(self.height):
            for c in range(self.width):
                rect = pygame.Rect(c * cell_size, r * cell_size, cell_size, cell_size)
                belief_val = self.belief_maze_data[r][c]
                color = (100,100,100) # Màu cho UNKNOWN

                if belief_val == BELIEF_WALL: color = (30,30,30)
                elif belief_val == BELIEF_PATH: color = (180,180,180)
                
                pygame.draw.rect(self.viz_belief_map_surface, color, rect)
                # Vẽ viền
                pygame.draw.rect(self.viz_belief_map_surface, (80,80,80), rect, 1)

                # Vẽ các đối tượng đã biết trên belief map
                pos = (c,r)
                if pos in self.belief_keys:
                    pygame.draw.circle(self.viz_belief_map_surface, (255, 255, 0), rect.center, cell_size // 3)
                if pos == self.belief_exit_pos:
                    pygame.draw.rect(self.viz_belief_map_surface, (255, 153, 255), rect.inflate(-cell_size//4, -cell_size//4))
                if pos in self.belief_mud:
                    pygame.draw.ellipse(self.viz_belief_map_surface, (115, 38, 38), rect.inflate(-cell_size//5, -cell_size//5))
                # (Thêm water, portal nếu muốn)
        
        # Vẽ vị trí hiện tại của agent trên belief map
        agent_rect_belief = pygame.Rect(self.agent_current_pos[0] * cell_size, 
                                        self.agent_current_pos[1] * cell_size, 
                                        cell_size, cell_size)
        pygame.draw.ellipse(self.viz_belief_map_surface, (255,0,0), agent_rect_belief.inflate(-cell_size//3, -cell_size//3))

        surface.blit(self.viz_belief_map_surface, (0,0)) # Ví dụ vẽ ở góc trên trái

    # _core_search_logic không thực sự áp dụng cho SPO theo cách của các solver khác.
    # Toàn bộ logic nằm trong solve_all_stages.
    def _core_search_logic(self, start_node, target_node):
        # Phương thức này có thể không được gọi hoặc cần trả về giá trị dummy
        # nếu cấu trúc của BaseSolver.solve_all_stages yêu cầu.
        # Tuy nhiên, SPOSolver override solve_all_stages hoàn toàn.
        pass