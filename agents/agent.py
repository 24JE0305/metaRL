import random

class RandomAgent:
    def act(self, state):
        return random.choice([-1, 1])