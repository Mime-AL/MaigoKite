"""Known credential paths shared by native policy and ripgrep exclusions.

This is a conservative path guard, not content DLP or a sandbox for arbitrary code.
"""

from fnmatch import fnmatchcase
from pathlib import Path

SENSITIVE_NAMES = (
    ".env", ".env.*", ".ssh", ".aws", ".gnupg", ".azure", ".kube",
    ".netrc", ".npmrc", ".pypirc", "id_rsa*", "id_ed25519*", "id_ecdsa*",
    "*.key", "*.pem", "*.p12", "*.pfx", "credentials.json", "credentials.yaml",
    "service-account*.json", "browser-profiles",
)


def is_sensitive_path(path: Path) -> bool:
    return any(fnmatchcase(part.casefold(), pattern) for part in path.parts for pattern in SENSITIVE_NAMES)


def search_exclusions() -> list[str]:
    # Use ripgrep's existing matcher; do not implement another recursive scanner.
    return [arg for pattern in SENSITIVE_NAMES for glob in (f"!{pattern}", f"!{pattern}/**")
            for arg in ("--iglob", glob)]
