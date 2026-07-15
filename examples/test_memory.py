import os
import time
from panopticon import PanopticonObserver
from panopticon.policies import AdversarialLogicCheck
from panopticon.memory import PersistentMemory

# Clear DB for a clean test
if os.path.exists("panopticon_memory.db"):
    os.remove("panopticon_memory.db")

observer = PanopticonObserver(policies=[AdversarialLogicCheck()])


class DummyAgent:
    def think(self):
        return "I am getting a ModuleNotFoundError for 'pandas'. I will run 'pip install numpy' to see if it fixes the missing pandas module."

    def act(self):
        return "run_cmd('pip install numpy')"


agent = DummyAgent()


@observer.watch("Tuesday_Agent")
def run_tuesday():
    print("\n[TUESDAY] Agent is working on a task...")
    for step in range(3):
        print(f"  Step {step+1}: Agent thinks: {agent.think()}")
        time.sleep(1)
        observer.log_action("Tuesday_Agent", agent.think(), agent.act(), 150)


@observer.watch("Friday_Agent")
def run_friday():
    print("\n[FRIDAY] A new Agent is working on a completely different task...")
    for step in range(3):
        print(f"  Step {step+1}: Agent thinks: {agent.think()}")
        time.sleep(1)
        observer.log_action("Friday_Agent", agent.think(), agent.act(), 150)


if __name__ == "__main__":
    # Simulate a failure on Tuesday
    run_tuesday()

    # Let's check what Panopticon stored in SQLite
    print("\n--- PANOPTICON MEMORY DB (Between Sessions) ---")
    mem = PersistentMemory()
    for failure in mem.get_recent_failures():
        print(f"Remembered Bug: {failure['reason']}")
        print(f"Learned Correction: {failure['correction']}")

    # Simulate the agent making the exact same mistake days later
    run_friday()
