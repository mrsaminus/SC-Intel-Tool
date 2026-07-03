from app.ocr.blueprint_reward_workflow import (
    STATE_IDLE,
    STATE_TRIGGER_DETECTED,
    STATE_WAITING_FOR_WINDOW_CLOSE,
    BlueprintRewardWorkflow,
    detect_blueprint_reward_trigger,
    title_region_from_reward_region,
)
from app.ocr.regions import OCRRegion


def test_blueprint_reward_trigger_detection_is_case_and_noise_tolerant():
    assert detect_blueprint_reward_trigger("Received Blueprint:")
    assert detect_blueprint_reward_trigger("Received Blueprint")
    assert detect_blueprint_reward_trigger("received blueprint")
    assert detect_blueprint_reward_trigger("  RECEIVED   BLUEPRINT  \nField Recon Helmet")
    assert not detect_blueprint_reward_trigger("Mission reward available")
    assert not detect_blueprint_reward_trigger("Blueprint Reward")


def test_blueprint_reward_trigger_detection_tolerates_small_ocr_errors():
    assert detect_blueprint_reward_trigger("Recieved Blueprint:")
    assert detect_blueprint_reward_trigger("Rece1ved Blueprint:")
    assert detect_blueprint_reward_trigger("Received B1ueprint")


def test_blueprint_reward_workflow_waits_until_trigger_disappears():
    workflow = BlueprintRewardWorkflow()

    assert workflow.trigger_seen("Received Blueprint:")
    assert workflow.state == STATE_TRIGGER_DETECTED

    workflow.start_scanning()
    workflow.mark_matched()
    workflow.wait_for_window_close()
    assert workflow.state == STATE_WAITING_FOR_WINDOW_CLOSE

    assert not workflow.trigger_seen("Received Blueprint:")
    assert workflow.state == STATE_WAITING_FOR_WINDOW_CLOSE

    assert not workflow.trigger_seen("")
    assert workflow.state == STATE_IDLE


def test_title_region_uses_only_top_portion_of_reward_region():
    region = OCRRegion.from_tuple((10, 20, 400, 300), profile="reward_scanner", name="Reward Scanner")

    trigger_region = title_region_from_reward_region(region)

    assert trigger_region.to_tuple() == (10, 20, 400, 84)
    assert trigger_region.name == "Reward Scanner Trigger"
