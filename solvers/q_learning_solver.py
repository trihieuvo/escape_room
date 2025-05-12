import random
import numpy as np
from collections import defaultdict
from .base_solver import BaseSolver
from constants import MUD_COST_ALGO, PORTAL_COST_ALGO, SLIDE_CELL_COST_ALGO

class QLearningSolver(BaseSolver):
    def __init__(self, maze_instance,
                 learning_rate=0.1, discount_factor=0.99,
                 epsilon=1.0, epsilon_decay=0.9995, min_epsilon=0.001,
                 num_episodes=10000):
        super().__init__(maze_instance)

        self.lr = learning_rate
        self.gamma = discount_factor
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.min_epsilon = min_epsilon
        self.num_episodes = num_episodes
        self.MUD_COST_ALGO = MUD_COST_ALGO
        self.PORTAL_COST_ALGO = PORTAL_COST_ALGO
        self.SLIDE_CELL_COST_ALGO = SLIDE_CELL_COST_ALGO

        self.q_table = defaultdict(lambda: [0.0] * 4)
        self.actions = [(0, -1), (0, 1), (-1, 0), (1, 0)] 

        self.key_positions_ordered = sorted(list(self.maze.keys))
        self.num_total_keys_in_maze = len(self.key_positions_ordered)

        self._training_complete = False
        self._current_episode = 0

        self.viz_agent_pos = self.start_pos
        self.viz_collected_keys_during_training_run = set()
        self.viz_current_training_path = [] 
        self.viz_current_runtime_path_idx = 0 

        self.prev_agent_pos_in_episode = None


    def _get_state_representation(self, agent_pos, collected_keys_set):
        key_statuses = [False] * self.num_total_keys_in_maze
        for i, key_pos_orig in enumerate(self.key_positions_ordered):
            if key_pos_orig in collected_keys_set:
                key_statuses[i] = True
        return (agent_pos, tuple(key_statuses))

    def _choose_action(self, state):
        if random.uniform(0, 1) < self.epsilon:
            return random.choice(range(len(self.actions)))
        else:
            q_values_for_state = self.q_table[state]
            if not q_values_for_state or all(q == q_values_for_state[0] for q in q_values_for_state) :
                return random.choice(range(len(self.actions)))

            max_q = np.max(q_values_for_state)
            best_actions_indices = [i for i, q_val in enumerate(q_values_for_state) if q_val == max_q]
            return random.choice(best_actions_indices)


    def _take_action_and_get_reward(self, current_agent_pos, prev_agent_pos, current_collected_keys, action_index):
        action_dy, action_dx = self.actions[action_index] 
        next_potential_x = current_agent_pos[0] + action_dx
        next_potential_y = current_agent_pos[1] + action_dy


        reward = -0.1
        done = False
        next_agent_pos_after_effects = (next_potential_x, next_potential_y)
        newly_collected_keys_set = set(current_collected_keys)
        
        if self.maze.is_wall(next_potential_x, next_potential_y):
            reward = -100.0
            next_agent_pos_after_effects = current_agent_pos
        else:
            if self.maze.is_mud(next_potential_x, next_potential_y):
                reward -= 2.0

            if self.maze.is_water(next_potential_x, next_potential_y):
                land_pos, num_slid_cells = self._get_slide_endpoint_and_cost_factor(
                     next_potential_x, next_potential_y, action_dx, action_dy 
                )
                next_agent_pos_after_effects = land_pos
                reward -= 0.5 * num_slid_cells

            elif self.maze.is_portal(next_potential_x, next_potential_y):
                portal_target = self.maze.get_portal_target(next_potential_x, next_potential_y)
                if portal_target:
                    next_agent_pos_after_effects = portal_target
                    reward -= 0.05
                    if prev_agent_pos is not None and next_agent_pos_after_effects == prev_agent_pos:
                        reward -= 15.0
            
            agent_final_x, agent_final_y = next_agent_pos_after_effects
            key_at_final_pos = (agent_final_x, agent_final_y)

            if key_at_final_pos in self.key_positions_ordered and key_at_final_pos not in newly_collected_keys_set:
                newly_collected_keys_set.add(key_at_final_pos)
                reward += 100.0

            if next_agent_pos_after_effects == self.exit_pos:
                if len(newly_collected_keys_set) >= self.num_total_keys_in_maze:
                    reward += 100.0
                    done = True
                else:
                    reward -= 1.0
        
        return next_agent_pos_after_effects, newly_collected_keys_set, reward, done


    def _train_one_episode(self):
        current_pos = self.start_pos
        self.prev_agent_pos_in_episode = None
        collected_keys = set()
        
        self.viz_current_training_path = [current_pos]
        self.viz_agent_pos = current_pos

        max_steps_per_episode = self.width * self.height 
        for step in range(max_steps_per_episode):
            state = self._get_state_representation(current_pos, collected_keys)
            action_idx = self._choose_action(state)

            next_pos, next_collected_keys, reward, done = \
                self._take_action_and_get_reward(current_pos, self.prev_agent_pos_in_episode, collected_keys, action_idx)

            next_state = self._get_state_representation(next_pos, next_collected_keys)

            old_q_value = self.q_table[state][action_idx]
            next_max_q = np.max(self.q_table[next_state])

            new_q_value = old_q_value + self.lr * (reward + self.gamma * next_max_q - old_q_value)
            self.q_table[state][action_idx] = new_q_value
            
            self.prev_agent_pos_in_episode = current_pos 
            current_pos = next_pos
            collected_keys = next_collected_keys
            
            self.viz_current_training_path.append(current_pos)
            self.viz_agent_pos = current_pos
            if done:
                break
        
        self.viz_visited_nodes = set(self.viz_current_training_path) 

        if self.epsilon > self.min_epsilon:
            self.epsilon *= self.epsilon_decay
            self.epsilon = max(self.min_epsilon, self.epsilon)


    def _core_search_logic(self, start_node, target_node):
        if not self._training_complete: 
             if not self.q_table:

                 original_num_episodes = self.num_episodes
                 self.num_episodes = max(1, original_num_episodes // 100) if original_num_episodes > 0 else 1 # Mini-training
                 for episode_emergency in range(self.num_episodes): self._train_one_episode()
                 self.num_episodes = original_num_episodes 
                 self._training_complete = True 
                 self.epsilon = 0 
        path = [self.start_pos]
        current_pos = self.start_pos
        collected_keys_runtime = set()
        cost = 0
        nodes_expanded_runtime = 0
        
        max_solve_steps = self.width * self.height * 2 
        last_pos_solve = None 

        for step_solve in range(max_solve_steps):
            nodes_expanded_runtime += 1
            current_state_repr = self._get_state_representation(current_pos, collected_keys_runtime)
            
            q_values = self.q_table[current_state_repr]
            if not any(q_values):
                return path, cost, nodes_expanded_runtime, False 

            sorted_actions = np.argsort(q_values)[::-1]
            
            action_taken_this_step = False
            chosen_action_idx = -1

            for action_idx_try in sorted_actions:
                action_dy_try, action_dx_try = self.actions[action_idx_try]
                next_potential_x_try = current_pos[0] + action_dx_try
                next_potential_y_try = current_pos[1] + action_dy_try

                if self.maze.is_wall(next_potential_x_try, next_potential_y_try):
                    continue 

                temp_actual_next_pos = (next_potential_x_try, next_potential_y_try)
                if self.maze.is_water(next_potential_x_try, next_potential_y_try):
                    land_pos_try, _ = self._get_slide_endpoint_and_cost_factor(
                        next_potential_x_try, next_potential_y_try, action_dx_try, action_dy_try
                    )
                    temp_actual_next_pos = land_pos_try
                elif self.maze.is_portal(next_potential_x_try, next_potential_y_try):
                    portal_target_try = self.maze.get_portal_target(next_potential_x_try, next_potential_y_try)
                    if portal_target_try:
                        temp_actual_next_pos = portal_target_try
                
                if temp_actual_next_pos == last_pos_solve and len(sorted_actions) > 1 : 
                    if step_solve < max_solve_steps - 5 : 
                        continue 

                chosen_action_idx = action_idx_try
                action_taken_this_step = True
                break 
            
            if not action_taken_this_step:
                 return path, cost, nodes_expanded_runtime, False

            action_dy, action_dx = self.actions[chosen_action_idx]
            next_potential_x = current_pos[0] + action_dx
            next_potential_y = current_pos[1] + action_dy
            step_cost_this_action = 1

            actual_next_pos = (next_potential_x, next_potential_y)
            
            if self.maze.is_mud(next_potential_x, next_potential_y):
                step_cost_this_action = self.MUD_COST_ALGO

            if self.maze.is_water(next_potential_x, next_potential_y):
                land_pos, num_slid = self._get_slide_endpoint_and_cost_factor(
                    next_potential_x, next_potential_y, action_dx, action_dy
                )
                actual_next_pos = land_pos
                step_cost_this_action += num_slid * self.SLIDE_CELL_COST_ALGO
            elif self.maze.is_portal(next_potential_x, next_potential_y):
                portal_target = self.maze.get_portal_target(next_potential_x, next_potential_y)
                if portal_target:
                    actual_next_pos = portal_target
                    step_cost_this_action += self.PORTAL_COST_ALGO
            
            cost += step_cost_this_action
            last_pos_solve = current_pos 
            current_pos = actual_next_pos
            path.append(current_pos)

            if current_pos in self.key_positions_ordered and current_pos not in collected_keys_runtime:
                collected_keys_runtime.add(current_pos)

            if current_pos == self.exit_pos and len(collected_keys_runtime) >= self.num_total_keys_in_maze:
                return path, cost, nodes_expanded_runtime, True
        
        return path, cost, nodes_expanded_runtime, False


    def solve_all_stages(self):
        self.q_table.clear() 
        self.epsilon = getattr(self, '_original_epsilon', 1.0) 
        if not hasattr(self, '_original_epsilon'): self._original_epsilon = self.epsilon

        self.path = []
        self.total_cost = 0
        self.nodes_expanded = 0 
        self.path_found = False
        self._training_complete = False
        self._current_episode = 0
        self.prev_agent_pos_in_episode = None

        for episode in range(self.num_episodes):
            self._train_one_episode()
            self._current_episode = episode + 1
        
        self._training_complete = True
        self.epsilon = 0 

        final_path, final_cost, solve_steps, found = self._core_search_logic(self.start_pos, self.exit_pos)
        
        self.path = final_path
        self.total_cost = final_cost
        self.nodes_expanded = solve_steps 
        self.path_found = found
        
        return self.path_found


    def solve_step_visualize(self):
        if not self._training_complete:
            episodes_per_viz_step = max(1, self.num_episodes // 100 if self.num_episodes > 0 else 1)
            
            for _ in range(episodes_per_viz_step):
                if self._current_episode < self.num_episodes:
                    self._train_one_episode() 
                    self._current_episode += 1
                else:
                    self._training_complete = True
                    self.epsilon = 0 
                    self.viz_current_runtime_path_idx = 0
                    if hasattr(self, '_solve_run_started_viz'): 
                        delattr(self, '_solve_run_started_viz')
                    break 
            return False 
        
        else:
            if not hasattr(self, '_solve_run_started_viz'):

                self._solve_run_started_viz = True
                self.viz_current_runtime_path_idx = 0
                if not self.path: 
                    self.path_found = False 
                    return True 


            if self.path_found and self.path:
                if self.viz_current_runtime_path_idx < len(self.path):
                    self.viz_agent_pos = self.path[self.viz_current_runtime_path_idx]

                    self.viz_visited_nodes = set(self.path[:self.viz_current_runtime_path_idx + 1]) 
                    self.viz_current_runtime_path_idx +=1
                    return False 
                else:

                    self.viz_visited_nodes = set(self.path) 
                    return True 
            else: 
                self.viz_agent_pos = self.start_pos 
                self.viz_visited_nodes = {self.start_pos} if not self.path else set(self.path)
                return True 