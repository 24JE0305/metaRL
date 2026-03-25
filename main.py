from envs.custom_env import SimpleEnv
from agents.agent import RandomAgent

def run():
    env = SimpleEnv()
    agent = RandomAgent()

    state = env.reset()

    for step in range(20):
        action = agent.act(state)
        state, reward, done, _ = env.step(action)

        print(f"Step {step}: State={state}, Reward={reward}")

        if done:
            print("Goal reached!")
            break

if __name__ == "__main__":
    run()