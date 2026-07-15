import time
from panopticon import PanopticonObserver
from panopticon.policies import AdversarialLogicCheck, TokenBurnPolicy

observer = PanopticonObserver(
    policies=[AdversarialLogicCheck(), TokenBurnPolicy(max_tokens=5000)]
)


class DummyAgent:
    def __init__(self, name: str):
        self.name = name

    def think(self):
        return "Got 403 Forbidden. Will keep trying the same URL."

    def act(self):
        return "search_web('https://forbidden.com')"


agent = DummyAgent("WebScraper")


@observer.watch(agent_name=agent.name)
def run_loop():
    for step in range(5):
        time.sleep(1)
        thought = agent.think()
        action = agent.act()
        tokens = 150

        print(f"Step {step + 1}: Action: '{action}'")

        observer.log_action(
            agent_name=agent.name, thought=thought, action=action, tokens_used=tokens
        )

    return {"status": "success"}


if __name__ == "__main__":
    result = run_loop()
    print(result)
