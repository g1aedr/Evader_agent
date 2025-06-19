import requests
import time
import random
from requests.exceptions import RequestException
from typing import Dict, Optional

API_BASE_URL = "http://127.0.0.1:8000"
MAX_RETRIES = 3
RETRY_DELAY = 1
FIRE_INTERVAL = 2
RATE_LIMIT_DELAY = 0.6
MOVE_DELAY = 0.1  # Fastest safe move rate (stays under 5 req/sec)

class GameAgent:
    """Fast random-moving agent that fires periodically and adapts behavior."""

    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.player_id = "evader_agent"
        self.name = "Evader"
        self.last_move_time = 0
        self.last_fire_time = 0
        self.last_request_time = 0
        self.current_direction = random.choice(["right", "left"])
        self.start_time = time.time()
        self.shield_used = False
        self.moves_in_a_row = 0
        self.direction_changed = False

    def _make_request(self, method: str, endpoint: str, json_data: dict = None, retry: bool = True) -> Optional[dict]:
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < 0.5:
            time.sleep(0.5 - time_since_last_request)

        for attempt in range(MAX_RETRIES):
            try:
                url = f"{self.base_url}/{endpoint}"
                response = requests.get(url) if method == "GET" else requests.post(url, json=json_data)
                response.raise_for_status()
                self.last_request_time = time.time()
                return response.json()
            except RequestException as e:
                if hasattr(e, 'response') and e.response and e.response.status_code == 429 and retry:
                    print("⚠️ Rate limit hit. Waiting...")
                    time.sleep(RATE_LIMIT_DELAY)
                    continue
                print(f"Request failed: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                return None
        return None

    def register(self) -> bool:
        response = self._make_request("POST", "register", {
            "player_id": self.player_id,
            "name": self.name
        })
        if response:
            print(f"✅ Registered with ID: {self.player_id}")
            return True
        return False

    def unregister(self) -> bool:
        response = self._make_request("POST", "unregister", {"player_id": self.player_id})
        if response:
            print("👋 Unregistered successfully")
            return True
        return False

    def move(self) -> bool:
        if time.time() - self.last_move_time < MOVE_DELAY:
            return False
        response = self._make_request("POST", "move", {"player_id": self.player_id})
        if response:
            self.last_move_time = time.time()
            self.moves_in_a_row += 1
            return True
        else:
            print("🧱 Hit the wall! Rotating to avoid it.")
            self.moves_in_a_row = 0
            return False

    def rotate(self, direction: str) -> bool:
        response = self._make_request("POST", "rotate", {
            "player_id": self.player_id,
            "direction": direction
        })
        if response:
            self.direction_changed = True
            self.moves_in_a_row = 0  # reset on rotation
        return response is not None

    def fire(self) -> bool:
        if time.time() - self.last_fire_time < FIRE_INTERVAL:
            return False
        response = self._make_request("POST", "fire", {"player_id": self.player_id})
        if response:
            self.last_fire_time = time.time()
            return True
        return False

    def shield(self) -> bool:
        response = self._make_request("POST", "shield", {"player_id": self.player_id})
        return response is not None

    def step(self) -> bool:
        # Activate shield once after 6 seconds
        if not self.shield_used and time.time() - self.start_time > 6:
            if self.shield():
                print("🛡️ Shield activated!")
                self.shield_used = True

        self.fire()

        moved = self.move()
        if not moved:
            turn = random.choice(["left", "right"])
            print(f"🔁 Rotating {turn} after wall hit.")
            self.rotate(turn)
        else:
            if self.moves_in_a_row >= 5 and not self.direction_changed:
                if random.random() < 0.5:
                    turn = random.choice(["left", "right"])
                    print(f"🎯 5 straight moves → randomly rotating {turn}.")
                    self.rotate(turn)
                else:
                    print("🎲 5 straight moves → decided not to rotate.")
                self.moves_in_a_row = 0  # reset regardless
            self.direction_changed = False  # reset flag each step

        return True

def main():
    agent = GameAgent()

    for attempt in range(MAX_RETRIES):
        print(f"Registering attempt {attempt + 1}...")
        if agent.register():
            break
        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_DELAY)
    else:
        print("❌ Could not register after retries.")
        return

    try:
        print("Agent running. Press Ctrl+C to stop.")
        while True:
            if not agent.step():
                print("❌ Step failed.")
                break
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n🛑 Interrupted.")
    finally:
        agent.unregister()

if __name__ == "__main__":
    main()
