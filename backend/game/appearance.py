"""
game/appearance.py — DiceBear Adventurer Avatar System
Implements all valid options from DiceBear Adventurer API v9.x
"""
import re
from typing import Optional, List, Dict, Any

# ── DICEBEAR ADVENTURER OPTIONS DEFINITIONS ──────────────────────────────────
# All options and their constraints per DiceBear documentation

DICEBEAR_OPTIONS = {
    # Core appearance options
    "base": {
        "type": "array",
        "values": ["default"],
        "description": "Avatar base style"
    },
    "seed": {
        "type": "string",
        "description": "Determines initial PRNG value for consistency"
    },
    "size": {
        "type": "integer",
        "min": 1,
        "description": "Avatar output size in pixels"
    },
    
    # Transform options
    "flip": {
        "type": "boolean",
        "description": "Flip avatar horizontally"
    },
    "rotate": {
        "type": "integer",
        "min": 0,
        "max": 360,
        "description": "Rotate avatar 0-360 degrees"
    },
    "scale": {
        "type": "integer",
        "min": 0,
        "max": 200,
        "description": "Scale avatar content 0-200%"
    },
    "translateX": {
        "type": "integer",
        "min": -100,
        "max": 100,
        "description": "Translate X axis -100 to 100"
    },
    "translateY": {
        "type": "integer",
        "min": -100,
        "max": 100,
        "description": "Translate Y axis -100 to 100"
    },
    
    # Clipping & IDs
    "clip": {
        "type": "boolean",
        "description": "Clip avatar to circle"
    },
    "randomizeIds": {
        "type": "boolean",
        "description": "Randomize SVG/XML IDs to avoid collisions"
    },
    "radius": {
        "type": "integer",
        "min": 0,
        "max": 50,
        "description": "Corner radius for clipping"
    },
    
    # Facial features - arrays with specific variants
    "earrings": {
        "type": "array",
        "values": [f"variant{i:02d}" for i in range(1, 7)],  # variant01-06
        "description": "Earring variants (selected variants always appear, empty = no earrings)"
    },
    
    "eyebrows": {
        "type": "array",
        "values": [f"variant{i:02d}" for i in range(1, 16)],  # variant01-15
        "description": "Eyebrow variants"
    },
    
    "eyes": {
        "type": "array",
        "values": [f"variant{i:02d}" for i in range(1, 27)],  # variant01-26
        "description": "Eye variants"
    },
    
    "features": {
        "type": "array",
        "values": ["birthmark", "blush", "freckles", "mustache"],
        "description": "Facial features (selected features always appear, empty = no features)"
    },
    
    "glasses": {
        "type": "array",
        "values": [f"variant{i:02d}" for i in range(1, 6)],  # variant01-05
        "description": "Glasses variants (selected variants always appear, empty = no glasses)"
    },
    
    "hair": {
        "type": "array",
        "values": [f"long{i:02d}" for i in range(1, 27)] + [f"short{i:02d}" for i in range(1, 20)],  # long01-26, short01-19
        "description": "Hair styles (exactly one style always selected, options: long01-long26, short01-short19)"
    },
    "hairColor": {
        "type": "array",
        "pattern": "^(transparent|[a-fA-F0-9]{6})$",
        "description": "Hair color(s) as hex or 'transparent' (deterministic when set)"
    },
    
    "mouth": {
        "type": "array",
        "values": [f"variant{i:02d}" for i in range(1, 31)],  # variant01-30
        "description": "Mouth variants"
    },
    
    "skinColor": {
        "type": "array",
        "pattern": "^(transparent|[a-fA-F0-9]{6})$",
        "description": "Skin color(s) as hex or 'transparent'"
    },
}

# ── VALIDATORS ───────────────────────────────────────────────────────────────

def validate_hex_color(value: str) -> bool:
    """Validate hex color format: transparent or 6 hex digits."""
    if value == "transparent":
        return True
    return bool(re.match(r"^[a-fA-F0-9]{6}$", value))

def validate_integer_range(value: int, min_val: int, max_val: int) -> bool:
    """Validate integer is within range."""
    return min_val <= value <= max_val

def validate_appearance_field(field: str, value: Any) -> tuple[bool, Optional[str]]:
    """
    Validate a single appearance field against DiceBear spec.
    Returns (is_valid, error_message).
    """
    if field not in DICEBEAR_OPTIONS:
        return False, f"Unknown field: {field}"
    
    spec = DICEBEAR_OPTIONS[field]
    field_type = spec.get("type")
    
    # String fields (seed)
    if field_type == "string":
        if not isinstance(value, str):
            return False, f"{field} must be a string"
        return True, None
    
    # Boolean fields
    if field_type == "boolean":
        if not isinstance(value, bool):
            return False, f"{field} must be a boolean"
        return True, None
    
    # Integer fields with range
    if field_type == "integer":
        if not isinstance(value, int):
            return False, f"{field} must be an integer"
        min_val = spec.get("min", float("-inf"))
        max_val = spec.get("max", float("inf"))
        if not validate_integer_range(value, min_val, max_val):
            return False, f"{field} must be between {min_val} and {max_val}, got {value}"
        return True, None
    
    # Array fields
    if field_type == "array":
        if not isinstance(value, list):
            return False, f"{field} must be an array"
        
        allowed_values = spec.get("values")
        pattern = spec.get("pattern")
        
        if allowed_values:
            # Exact values required
            for item in value:
                if item not in allowed_values:
                    return False, f"{field}: '{item}' not in allowed values {allowed_values}"
        elif pattern:
            # Pattern matching (hex colors)
            for item in value:
                if not re.match(pattern, str(item)):
                    return False, f"{field}: '{item}' does not match pattern {pattern}"
        
        return True, None
    
    # Range arrays (e.g., backgroundRotation)
    if field_type == "array_range":
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            return False, f"{field} must be [min, max] array"
        if not all(isinstance(v, int) for v in value):
            return False, f"{field} values must be integers"
        if value[0] > value[1]:
            return False, f"{field}: min must be <= max"
        return True, None
    
    return False, f"Unknown type for {field}"

def validate_appearance(appearance: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate entire appearance dict.
    Returns (is_valid, error_message).
    """
    if not isinstance(appearance, dict):
        return False, "appearance must be a dictionary"
    
    for field, value in appearance.items():
        if field not in DICEBEAR_OPTIONS:
            return False, f"Unknown field: {field}"
        
        is_valid, error_msg = validate_appearance_field(field, value)
        if not is_valid:
            return False, error_msg
    
    return True, None

# ── DEFAULT APPEARANCE ───────────────────────────────────────────────────────
DEFAULT_APPEARANCE = {
    "seed": "default",
    "base": ["default"],
    "scale": 100,
    "radius": 0,
    "translateX": 0,
    "translateY": 0,
    "clip": True,
    "randomizeIds": False,
    "flip": False,
    "rotate": 0,
    "earrings": [],
    "eyebrows": ["variant01"],
    "eyes": ["variant01"],
    "features": [],
    "glasses": [],
    "hair": ["long01"],
    "hairColor": ["0e0e0e"],
    "mouth": ["variant01"],
    "skinColor": ["9e5622"],
}

def get_appearance_options() -> Dict[str, Any]:
    """Return all available appearance options for frontend."""
    return DICEBEAR_OPTIONS

def build_avatar_url(appearance: Dict[str, Any], character_id: int | str) -> str:
    """
    Build DiceBear API URL from appearance dict.
    Avatar background is always black per specification.
    Handles seed generation and URL parameter encoding.
    """
    base_url = "https://api.dicebear.com/9.x/adventurer/svg"
    
    # Use character_id as seed if not explicitly set
    params = appearance.copy()
    if not params.get("seed"):
        params["seed"] = str(character_id)
    
    # Remove any background-related parameters
    params.pop("backgroundColor", None)
    params.pop("backgroundType", None)
    params.pop("backgroundRotation", None)
    
    # Always use black background
    params["backgroundColor"] = "000000"
    
    # DiceBear has low DEFAULT probabilities for optional features:
    #   earringsProbability = 10 (default) — earrings may not appear without this fix
    #   glassesProbability  = 10 (default)
    #   featuresProbability = 5  (default)
    # We must set these to 100 when variants are selected, or 0 when empty.
    PROB_FIELDS = {
        "earrings": "earringsProbability",
        "glasses":  "glassesProbability",
        "features": "featuresProbability",
    }

    # Build query string (DiceBear uses comma-separated values for arrays)
    query_parts = []
    for key, value in params.items():
        if value is None:
            continue

        if isinstance(value, bool):
            query_parts.append(f"{key}={str(value).lower()}")
        elif isinstance(value, list):
            if len(value) == 0:
                # Empty array — set probability=0 so DiceBear never shows this feature
                if key in PROB_FIELDS:
                    query_parts.append(f"{PROB_FIELDS[key]}=0")
                continue
            str_values = [str(v) for v in value]
            query_parts.append(f"{key}={','.join(str_values)}")
            # Non-empty — set probability=100 so selected variants always appear
            if key in PROB_FIELDS:
                query_parts.append(f"{PROB_FIELDS[key]}=100")
        else:
            query_parts.append(f"{key}={value}")

    return f"{base_url}?{'&'.join(query_parts)}"

def sanitize_appearance(appearance: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove any invalid fields and coerce types where safe.
    """
    sanitized = {}
    for field, value in appearance.items():
        if field not in DICEBEAR_OPTIONS:
            continue
        
        is_valid, _ = validate_appearance_field(field, value)
        if is_valid:
            sanitized[field] = value
    
    return sanitized
