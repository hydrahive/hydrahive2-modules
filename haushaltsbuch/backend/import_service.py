"""Stable service API for bank import routes.

Implementation is split by responsibility to keep each module focused.
"""

from .categorize_service import accept_suggestions as accept_suggestions
from .categorize_service import suggest_categories as suggest_categories
from .import_completion import complete_batch as complete_batch
from .import_completion import reverse_batch as reverse_batch
from .import_inbox import create_batch as create_batch
from .import_inbox import delete_batch as delete_batch
from .import_inbox import get_batch as get_batch
from .import_inbox import list_batches as list_batches
from .import_rows import update_row as update_row
from .import_persistence import create_profile as create_profile
from .import_persistence import delete_profile as delete_profile
from .import_persistence import list_profiles as list_profiles
from .import_persistence import update_profile as update_profile
from .import_persistence import validate_upload_target as validate_upload_target

__all__ = [
    "accept_suggestions",
    "complete_batch",
    "create_batch",
    "create_profile",
    "delete_batch",
    "delete_profile",
    "get_batch",
    "list_batches",
    "list_profiles",
    "reverse_batch",
    "suggest_categories",
    "update_profile",
    "update_row",
    "validate_upload_target",
]
