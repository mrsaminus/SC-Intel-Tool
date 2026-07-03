from dataclasses import dataclass

from .capture import normalize_region
from .reward_scanner import normalize_match_text
from .regions import OCRRegion


BLUEPRINT_REWARD_TRIGGER = "Blueprint Reward"

STATE_IDLE = "Idle"
STATE_TRIGGER_DETECTED = "TriggerDetected"
STATE_SCANNING = "Scanning"
STATE_MATCHED = "Matched"
STATE_WAITING_FOR_WINDOW_CLOSE = "WaitingForWindowClose"


def detect_blueprint_reward_trigger(text):
    return normalize_match_text(BLUEPRINT_REWARD_TRIGGER) in normalize_match_text(text)


def title_region_from_reward_region(region, height_ratio=0.28, minimum_height=36):
    region = normalize_region(region)
    trigger_height = max(minimum_height, int(region.height * height_ratio))
    trigger_height = min(region.height, trigger_height)
    return OCRRegion(
        profile=region.profile,
        name=f"{region.name} Trigger",
        x=region.x,
        y=region.y,
        width=region.width,
        height=trigger_height,
        monitor=region.monitor,
        resolution=region.resolution,
        description="Blueprint Reward title trigger region.",
    )


@dataclass
class BlueprintRewardWorkflow:
    state: str = STATE_IDLE

    def reset(self):
        self.state = STATE_IDLE

    def trigger_seen(self, text):
        trigger_found = detect_blueprint_reward_trigger(text)
        if self.state == STATE_WAITING_FOR_WINDOW_CLOSE:
            if trigger_found:
                return False
            self.state = STATE_IDLE
            return False

        if not trigger_found:
            self.state = STATE_IDLE
            return False

        self.state = STATE_TRIGGER_DETECTED
        return True

    def start_scanning(self):
        self.state = STATE_SCANNING

    def mark_matched(self):
        self.state = STATE_MATCHED

    def wait_for_window_close(self):
        self.state = STATE_WAITING_FOR_WINDOW_CLOSE

    @property
    def waiting_for_window_close(self):
        return self.state == STATE_WAITING_FOR_WINDOW_CLOSE
