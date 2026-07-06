from app.ocr.blueprint_reward_workflow import (
    BLUEPRINT_SCAN_INTERVAL_MS,
    STATE_IDLE,
    STATE_TRIGGER_DETECTED,
    STATE_WAITING_FOR_WINDOW_CLOSE,
    BlueprintRewardWorkflow,
    blueprint_name_candidate_present,
    crop_notification_toast,
    detect_blueprint_reward_trigger,
    detect_notification_toast,
    title_region_from_reward_region,
)
from app.ocr.regions import OCRRegion
from PIL import Image, ImageDraw


def toast_image():
    image = Image.new("RGB", (360, 140), color=(8, 9, 11))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((44, 48, 316, 92), radius=14, fill=(126, 126, 126))
    draw.ellipse((58, 58, 78, 78), fill=(205, 205, 205))
    draw.rectangle((92, 61, 290, 66), fill=(215, 215, 215))
    draw.rectangle((92, 74, 240, 79), fill=(188, 188, 188))
    return image


def test_blueprint_reward_trigger_detection_is_case_and_noise_tolerant():
    assert detect_blueprint_reward_trigger("Received Blueprint:")
    assert detect_blueprint_reward_trigger("Received Blueprint")
    assert detect_blueprint_reward_trigger("received blueprint")
    assert detect_blueprint_reward_trigger("Received Blue print")
    assert detect_blueprint_reward_trigger("  RECEIVED   BLUEPRINT  \nField Recon Helmet")
    assert not detect_blueprint_reward_trigger("Mission reward available")
    assert not detect_blueprint_reward_trigger("Blueprint Reward")


def test_blueprint_reward_trigger_detection_tolerates_small_ocr_errors():
    assert detect_blueprint_reward_trigger("Recieved Blueprint:")
    assert detect_blueprint_reward_trigger("Rece1ved Blueprint:")
    assert detect_blueprint_reward_trigger("Received B1ueprint")


def test_blueprint_reward_name_candidate_detection_handles_missing_name():
    assert blueprint_name_candidate_present("Received Blueprint: Field Recon Helmet")
    assert blueprint_name_candidate_present("Received Blueprint:\nField Recon Helmet")
    assert blueprint_name_candidate_present("Recieved Blueprint Field Recon Helmet")
    assert not blueprint_name_candidate_present("Received Blueprint:")
    assert not blueprint_name_candidate_present("Received Blueprint")


def test_visual_notification_toast_detection_finds_centered_gray_container():
    detection = detect_notification_toast(toast_image())

    assert detection.detected
    assert detection.crop_box is not None
    assert detection.crop_box[0] < 60
    assert detection.crop_box[2] > 300


def test_visual_notification_toast_detection_ignores_plain_frames():
    image = Image.new("RGB", (360, 140), color=(8, 9, 11))

    detection = detect_notification_toast(image)

    assert not detection.detected
    assert detection.crop_box is None


def test_notification_toast_crop_uses_detected_box():
    image = toast_image()
    detection = detect_notification_toast(image)
    cropped = crop_notification_toast(image, detection)

    assert cropped.size[0] < image.size[0]
    assert cropped.size[1] < image.size[1]


def test_blueprint_scan_interval_is_not_subsecond():
    assert BLUEPRINT_SCAN_INTERVAL_MS >= 1000


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


def test_blueprint_reward_workflow_can_wait_after_visual_toast_without_text_trigger():
    workflow = BlueprintRewardWorkflow()

    assert workflow.visual_toast_seen()
    assert workflow.state == STATE_TRIGGER_DETECTED

    workflow.wait_for_window_close()
    assert workflow.state == STATE_WAITING_FOR_WINDOW_CLOSE
    assert not workflow.visual_toast_seen()
    assert workflow.state == STATE_WAITING_FOR_WINDOW_CLOSE

    assert not workflow.trigger_seen("")
    assert workflow.state == STATE_IDLE


def test_title_region_uses_only_top_portion_of_reward_region():
    region = OCRRegion.from_tuple((10, 20, 400, 300), profile="reward_scanner", name="Reward Scanner")

    trigger_region = title_region_from_reward_region(region)

    assert trigger_region.to_tuple() == (10, 20, 400, 84)
    assert trigger_region.name == "Reward Scanner Trigger"
