from openenv.core import Env

class SimpleEnv(Env):
    def reset(self):
        self.state = 0
        return self.state

    def step(self, action):
        # action: +1 or -1
        self.state += action

        reward = 1 if self.state == 5 else 0
        done = self.state >= 5

        return self.state, reward, done, {}