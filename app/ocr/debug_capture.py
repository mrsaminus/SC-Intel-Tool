import json
import re
import shutil
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.paths import get_active_data_dir
from app.version import APP_VERSION


OCR_DEBUG_ENABLED_SETTING_KEY = "ocr.debug.enabled"
OCR_DEBUG_DIR_NAME = "ocr_debug"
DEFAULT_RETENTION_PER_WORKFLOW = 50


def default_ocr_debug_enabled():
    version = str(APP_VERSION).lower()
    return "alpha" in version or "beta" in version


def is_ocr_debug_enabled():
    try:
        from app.database import get_app_setting

        default = "1" if default_ocr_debug_enabled() else "0"
        value = get_app_setting(OCR_DEBUG_ENABLED_SETTING_KEY, default)
    except Exception:
        return default_ocr_debug_enabled()

    return str(value).strip().lower() in {"1", "true", "yes", "on", "enabled"}


def set_ocr_debug_enabled(enabled):
    from app.database import set_app_setting

    set_app_setting(OCR_DEBUG_ENABLED_SETTING_KEY, "1" if enabled else "0")


def get_ocr_debug_root(create=False):
    root = get_active_data_dir() / OCR_DEBUG_DIR_NAME
    if create:
        root.mkdir(parents=True, exist_ok=True)
    return root


def clear_ocr_debug_captures(workflow=None):
    root = get_ocr_debug_root(create=False)
    target = root / sanitize_workflow_name(workflow) if workflow else root
    if not target.exists():
        return 0

    session_count = count_debug_capture_sessions(workflow=workflow)
    shutil.rmtree(target)
    return session_count


def get_ocr_debug_summary(workflow=None):
    root = get_ocr_debug_root(create=False)
    target = root / sanitize_workflow_name(workflow) if workflow else root
    return {
        "path": root,
        "capture_count": count_debug_capture_sessions(workflow=workflow),
        "disk_bytes": folder_size(target),
    }


def count_debug_capture_sessions(workflow=None):
    return len(list(iter_debug_capture_sessions(workflow=workflow)))


def iter_debug_capture_sessions(workflow=None):
    root = get_ocr_debug_root(create=False)
    if not root.exists():
        return []

    workflow_dirs = [root / sanitize_workflow_name(workflow)] if workflow else [
        path for path in root.iterdir() if path.is_dir()
    ]
    sessions = []
    for workflow_dir in workflow_dirs:
        if not workflow_dir.exists():
            continue
        sessions.extend(path for path in workflow_dir.iterdir() if path.is_dir())
    return sorted(sessions, key=lambda path: path.name)


def folder_size(path):
    path = Path(path)
    if not path.exists():
        return 0
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            try:
                total += item.stat().st_size
            except OSError:
                continue
    return total


def format_debug_size(byte_count):
    byte_count = int(byte_count or 0)
    units = ("B", "KB", "MB", "GB")
    value = float(byte_count)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}" if unit != "B" else f"{byte_count} B"
        value /= 1024
    return f"{byte_count} B"


def start_ocr_debug_session(workflow, metadata=None, retention=DEFAULT_RETENTION_PER_WORKFLOW):
    if not is_ocr_debug_enabled():
        return None
    return OCRDebugCaptureStore(retention=retention).start_session(workflow, metadata=metadata)


class OCRDebugCaptureStore:
    def __init__(self, root=None, retention=DEFAULT_RETENTION_PER_WORKFLOW):
        self.root = Path(root) if root else get_ocr_debug_root(create=True)
        self.retention = max(1, int(retention or DEFAULT_RETENTION_PER_WORKFLOW))

    def start_session(self, workflow, metadata=None):
        workflow_name = sanitize_workflow_name(workflow)
        workflow_dir = self.root / workflow_name
        workflow_dir.mkdir(parents=True, exist_ok=True)
        session_path = self._next_session_path(workflow_dir)
        session_path.mkdir(parents=True, exist_ok=True)
        session = OCRDebugSession(
            workflow=workflow_name,
            path=session_path,
            metadata={
                "workflow": workflow_name,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "app_version": APP_VERSION,
            },
        )
        if metadata:
            session.update_metadata(metadata)
        else:
            session.write_metadata()
        self.cleanup_retention(workflow_name)
        return session

    def cleanup_retention(self, workflow):
        workflow_dir = self.root / sanitize_workflow_name(workflow)
        if not workflow_dir.exists():
            return 0
        sessions = sorted(
            (path for path in workflow_dir.iterdir() if path.is_dir()),
            key=lambda path: path.name,
        )
        stale = sessions[:-self.retention]
        for path in stale:
            shutil.rmtree(path, ignore_errors=True)
        return len(stale)

    @staticmethod
    def _next_session_path(workflow_dir):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S_%f")
        candidate = workflow_dir / timestamp
        index = 1
        while candidate.exists():
            candidate = workflow_dir / f"{timestamp}_{index:03d}"
            index += 1
        return candidate


class OCRDebugSession:
    def __init__(self, workflow, path, metadata=None):
        self.workflow = sanitize_workflow_name(workflow)
        self.path = Path(path)
        self.metadata = dict(metadata or {})

    def save_image(self, filename, image):
        if image is None or not hasattr(image, "save"):
            self.update_metadata({f"{safe_metadata_key(filename)}_saved": False})
            return False
        target = self.path / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        image.save(target, format="PNG")
        self.update_metadata({
            f"{safe_metadata_key(filename)}_saved": True,
            f"{safe_metadata_key(filename)}_path": filename,
        })
        return True

    def save_text(self, filename, text):
        target = self.path / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(str(text or ""), encoding="utf-8")
        self.update_metadata({
            f"{safe_metadata_key(filename)}_saved": True,
            f"{safe_metadata_key(filename)}_path": filename,
        })

    def update_metadata(self, values):
        if values:
            self.metadata.update(json_safe(values))
        self.write_metadata()

    def write_metadata(self):
        self.path.mkdir(parents=True, exist_ok=True)
        (self.path / "metadata.json").write_text(
            json.dumps(json_safe(self.metadata), indent=2, sort_keys=True),
            encoding="utf-8",
        )


def sanitize_workflow_name(value):
    text = str(value or "ocr").strip().lower()
    text = re.sub(r"[^a-z0-9_-]+", "_", text)
    return text.strip("_") or "ocr"


def safe_metadata_key(filename):
    return re.sub(r"[^a-z0-9]+", "_", str(filename).lower()).strip("_")


def json_safe(value):
    if is_dataclass(value):
        return json_safe(asdict(value))
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "to_dict"):
        try:
            return json_safe(value.to_dict())
        except Exception:
            return str(value)
    return str(value)
