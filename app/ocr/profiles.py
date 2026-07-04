import json
from dataclasses import dataclass, replace

from .regions import OCRRegion
from .settings import OCRSettings


REWARD_SCANNER_PROFILE_KEY = "reward_scanner"
HAULING_CONTRACTS_PROFILE_KEY = "hauling_contracts"
OCR_PROFILES_SETTING_KEY = "ocr.profiles"
OCR_DEFAULT_PROFILE_SETTING_KEY = "ocr.default_profile"
OCR_REGIONS_SETTING_KEY = "ocr.regions"


@dataclass(frozen=True)
class OCRProfile:
    key: str
    name: str
    description: str = ""
    language: str = "eng"
    preprocessing: bool = True
    threshold: int | None = None
    scaling: float = 1.0
    invert_colors: bool = False
    grayscale: bool = True
    parser_type: str = ""
    enabled: bool = True

    def to_settings(self):
        return OCRSettings(
            language=self.language,
            preprocessing=self.preprocessing,
            grayscale=self.grayscale,
            threshold=self.threshold,
            scale=self.scaling,
            invert_colors=self.invert_colors,
        )

    def to_dict(self):
        return {
            "key": self.key,
            "name": self.name,
            "description": self.description,
            "language": self.language,
            "preprocessing": bool(self.preprocessing),
            "threshold": self.threshold,
            "scaling": float(self.scaling or 1.0),
            "invert_colors": bool(self.invert_colors),
            "grayscale": bool(self.grayscale),
            "parser_type": self.parser_type,
            "enabled": bool(self.enabled),
        }

    @classmethod
    def from_dict(cls, data):
        data = data or {}
        threshold = data.get("threshold")
        if threshold in ("", None):
            threshold = None
        return cls(
            key=str(data.get("key") or ""),
            name=str(data.get("name") or data.get("key") or "OCR Profile"),
            description=str(data.get("description") or ""),
            language=str(data.get("language") or "eng"),
            preprocessing=bool(data.get("preprocessing", True)),
            threshold=threshold,
            scaling=float(data.get("scaling") or data.get("scale") or 1.0),
            invert_colors=bool(data.get("invert_colors", False)),
            grayscale=bool(data.get("grayscale", True)),
            parser_type=str(data.get("parser_type") or ""),
            enabled=bool(data.get("enabled", True)),
        )


def built_in_profiles():
    return {
        REWARD_SCANNER_PROFILE_KEY: OCRProfile(
            key=REWARD_SCANNER_PROFILE_KEY,
            name="Reward Scanner",
            description="Default local OCR profile for BP Overview reward matching.",
            language="eng",
            preprocessing=True,
            threshold=None,
            scaling=2.0,
            invert_colors=True,
            grayscale=True,
            parser_type="reward_scanner",
            enabled=True,
        ),
        HAULING_CONTRACTS_PROFILE_KEY: OCRProfile(
            key=HAULING_CONTRACTS_PROFILE_KEY,
            name="Hauling Contracts",
            description="Default local OCR profile for hauling contract text capture.",
            language="eng",
            preprocessing=True,
            threshold=None,
            scaling=2.0,
            invert_colors=True,
            grayscale=True,
            parser_type="hauling_contracts",
            enabled=True,
        ),
    }


def normalize_profile(profile):
    if isinstance(profile, OCRProfile):
        return profile
    return OCRProfileManager().get_profile(profile)


class OCRProfileManager:
    def __init__(self):
        self._built_ins = built_in_profiles()

    def list_profiles(self, include_disabled=False):
        profiles = dict(self._built_ins)
        for key, override in _load_profile_overrides().items():
            if key in self._built_ins:
                profiles[key] = replace(self._built_ins[key], enabled=override.enabled)
            else:
                profiles[key] = override
        ordered = []
        for key in self._built_ins:
            profile = profiles.pop(key, None)
            if profile and (include_disabled or profile.enabled):
                ordered.append(profile)
        for profile in sorted(profiles.values(), key=lambda item: item.name.lower()):
            if include_disabled or profile.enabled:
                ordered.append(profile)
        return ordered

    def get_profile(self, key=None):
        key = key or self.get_default_profile_key()
        for profile in self.list_profiles(include_disabled=True):
            if profile.key == key:
                return profile
        return self._built_ins[REWARD_SCANNER_PROFILE_KEY]

    def get_default_profile_key(self):
        key = _get_app_setting(OCR_DEFAULT_PROFILE_SETTING_KEY, REWARD_SCANNER_PROFILE_KEY)
        if any(profile.key == key for profile in self.list_profiles(include_disabled=True)):
            return key
        return REWARD_SCANNER_PROFILE_KEY

    def set_default_profile(self, key):
        profile = self.get_profile(key)
        _set_app_setting(OCR_DEFAULT_PROFILE_SETTING_KEY, profile.key)
        return profile

    def save_profile(self, profile):
        if not isinstance(profile, OCRProfile) and hasattr(profile, "to_dict"):
            profile = OCRProfile.from_dict(profile.to_dict())
        elif not isinstance(profile, OCRProfile):
            profile = OCRProfile.from_dict(profile)
        overrides = _load_profile_overrides()
        overrides[profile.key] = profile
        _set_json_setting(
            OCR_PROFILES_SETTING_KEY,
            {key: value.to_dict() for key, value in overrides.items()},
        )
        return profile

    def save_profile_settings(self, key, settings):
        profile = self.get_profile(key)
        settings = settings if isinstance(settings, OCRSettings) else OCRSettings.from_dict(settings)
        updated = replace(
            profile,
            language=settings.language,
            preprocessing=settings.preprocessing,
            threshold=settings.threshold,
            scaling=settings.scale,
            invert_colors=settings.invert_colors,
            grayscale=settings.grayscale,
        )
        return self.save_profile(updated)

    def list_regions(self, profile_key=None):
        regions = _load_json_setting(OCR_REGIONS_SETTING_KEY, [])
        loaded = []
        for row in regions if isinstance(regions, list) else []:
            try:
                region = OCRRegion.from_dict(row)
            except (TypeError, ValueError):
                continue
            if profile_key and region.profile != profile_key:
                continue
            loaded.append(region)
        return loaded

    def get_region(self, profile_key, name):
        for region in self.list_regions(profile_key=profile_key):
            if region.name == name:
                return region
        return None

    def save_region(self, region):
        if not isinstance(region, OCRRegion) and hasattr(region, "to_dict"):
            region = OCRRegion.from_dict(region.to_dict())
        elif not isinstance(region, OCRRegion):
            region = OCRRegion.from_dict(region)
        regions = [
            existing
            for existing in self.list_regions()
            if not (existing.profile == region.profile and existing.name == region.name)
        ]
        regions.append(region)
        _set_json_setting(OCR_REGIONS_SETTING_KEY, [item.to_dict() for item in regions])
        return region

    def clear_region(self, profile_key, name):
        regions = [
            existing
            for existing in self.list_regions()
            if not (existing.profile == profile_key and existing.name == name)
        ]
        _set_json_setting(OCR_REGIONS_SETTING_KEY, [item.to_dict() for item in regions])


def _load_profile_overrides():
    payload = _load_json_setting(OCR_PROFILES_SETTING_KEY, {})
    if not isinstance(payload, dict):
        return {}
    profiles = {}
    for key, data in payload.items():
        if not isinstance(data, dict):
            continue
        row = dict(data)
        row.setdefault("key", key)
        try:
            profile = OCRProfile.from_dict(row)
        except (TypeError, ValueError):
            continue
        if profile.key:
            profiles[profile.key] = profile
    return profiles


def _load_json_setting(key, default):
    raw_value = _get_app_setting(key, "")
    if not raw_value:
        return default
    try:
        return json.loads(raw_value)
    except (TypeError, json.JSONDecodeError):
        return default


def _set_json_setting(key, value):
    _set_app_setting(key, json.dumps(value, sort_keys=True, ensure_ascii=True))


def _get_app_setting(key, default=""):
    from app.database import get_app_setting

    return get_app_setting(key, default)


def _set_app_setting(key, value):
    from app.database import set_app_setting

    set_app_setting(key, value)
