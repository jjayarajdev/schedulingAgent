"""
Post-Filtering Module for ProjectForce Orchestrator

Handles filtering of project lists with:
- Inclusion filters (status, category, technician, address)
- Exclusion filters (negation support)
- Ordinal selection (applied last)
"""
import logging
import re
from typing import Any, Dict, List, Optional, Set

from config_loader import (
    get_schedulable_statuses_safe,
    get_scheduled_statuses_safe,
    get_all_category_buckets_safe,
    find_category_bucket_for_keyword,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def _norm(s: Any) -> str:
    """Normalize for case/whitespace-insensitive comparisons."""
    if s is None:
        return ""
    return re.sub(r"\s+", " ", str(s).strip().lower())


def _get_field(obj: Dict[str, Any], candidates: List[str]) -> Any:
    """Retrieve first available field from dict using multiple candidate keys."""
    for k in candidates:
        if k in obj:
            return obj.get(k)
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# DYNAMIC CONFIG ACCESSORS
# ═══════════════════════════════════════════════════════════════════════════════

def _get_schedulable_statuses() -> Set[str]:
    """Get schedulable statuses from external config."""
    return get_schedulable_statuses_safe()


def _get_scheduled_statuses() -> Set[str]:
    """Get scheduled statuses from external config."""
    return get_scheduled_statuses_safe()


def _get_category_buckets() -> Dict[str, Set[str]]:
    """Get category buckets from external config."""
    return get_all_category_buckets_safe()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN FILTER FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

def apply_project_filters(
    projects: List[Dict[str, Any]],
    params: Optional[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Apply semantic filters to a list of project records.

    Supported inclusion params:
    - status: "schedulable", "scheduled", or exact status value
    - category: bucket name or exact category
    - projectType: exact type value
    - technician_name: filter by assigned technician/installer
    - address: filter by installation address

    Supported exclusion params (negation):
    - exclude_status: list of statuses to exclude (supports "schedulable", "scheduled")
    - exclude_category: list of categories/buckets to exclude
    - exclude_technician: list of technician names to exclude

    Ordinal selection (applied LAST, after all filters):
    - ordinal: "first", "second", "last", or integer (1-indexed)
      * "2nd kitchen project" -> filter by kitchen, then get 2nd
    """
    if not params:
        return projects

    out = projects

    # ════════════════════════════════════════════════════════════════════════════
    # CONFLICT RESOLUTION: If both inclusion and exclusion exist, prefer exclusion
    # ════════════════════════════════════════════════════════════════════════════
    has_exclude_status = params.get("exclude_status")
    has_exclude_category = params.get("exclude_category")
    has_exclude_technician = params.get("exclude_technician")
    has_exclude_address = params.get("exclude_address")

    # ════════════════════════════════════════════════════════════════════════════
    # INCLUSION FILTERS (skip if corresponding exclusion exists)
    # ════════════════════════════════════════════════════════════════════════════

    # ---- STATUS FILTER ----
    status = params.get("status")
    if status and not has_exclude_status:  # Skip if exclude_status exists
        out = _apply_status_filter(out, status)
    elif status and has_exclude_status:
        logger.warning(f"[FILTER] Skipping status inclusion filter - exclusion takes precedence")

    # ---- CATEGORY FILTER ----
    category = params.get("category")
    if category and not has_exclude_category:  # Skip if exclude_category exists
        out = _apply_category_filter(out, category)
    elif category and has_exclude_category:
        logger.warning(f"[FILTER] Skipping category inclusion filter - exclusion takes precedence")

    # ---- PROJECT TYPE FILTER ----
    project_type = params.get("projectType")
    if project_type:
        out = _apply_project_type_filter(out, project_type)

    # ---- TECHNICIAN/INSTALLER FILTER ----
    technician_name = params.get("technician_name")
    if technician_name and not has_exclude_technician:  # Skip if exclude_technician exists
        out = _apply_technician_filter(out, technician_name)
    elif technician_name and has_exclude_technician:
        logger.warning(f"[FILTER] Skipping technician inclusion filter - exclusion takes precedence")

    # ---- ADDRESS FILTER ----
    address = params.get("address")
    if address and not has_exclude_address:  # Skip if exclude_address exists
        out = _apply_address_filter(out, address)
    elif address and has_exclude_address:
        logger.warning(f"[FILTER] Skipping address inclusion filter - exclusion takes precedence")

    # ════════════════════════════════════════════════════════════════════════════
    # EXCLUSION FILTERS (negation support)
    # ════════════════════════════════════════════════════════════════════════════

    # ---- EXCLUDE STATUS ----
    exclude_status = params.get("exclude_status")
    if exclude_status:
        out = _apply_exclude_status_filter(out, exclude_status)

    # ---- EXCLUDE CATEGORY ----
    exclude_category = params.get("exclude_category")
    if exclude_category:
        out = _apply_exclude_category_filter(out, exclude_category)

    # ---- EXCLUDE TECHNICIAN ----
    exclude_technician = params.get("exclude_technician")
    if exclude_technician:
        out = _apply_exclude_technician_filter(out, exclude_technician)

    # ---- EXCLUDE ADDRESS ----
    exclude_address = params.get("exclude_address")
    if exclude_address:
        out = _apply_exclude_address_filter(out, exclude_address)

    # ════════════════════════════════════════════════════════════════════════════
    # ORDINAL SELECTION (applied LAST, after all filters)
    # ════════════════════════════════════════════════════════════════════════════
    ordinal = params.get("ordinal")
    if ordinal and out:
        out = _apply_ordinal_selection(out, ordinal)

    return out


# ═══════════════════════════════════════════════════════════════════════════════
# INCLUSION FILTER IMPLEMENTATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def _apply_status_filter(projects: List[Dict], status: str) -> List[Dict]:
    """Filter projects by status."""
    s = _norm(status)
    schedulable_statuses = _get_schedulable_statuses()
    scheduled_statuses = _get_scheduled_statuses()

    if s == "schedulable":
        return [
            p for p in projects
            if _get_field(p, ["Status", "status"]) in schedulable_statuses
            or _norm(_get_field(p, ["Status", "status"])) in {_norm(x) for x in schedulable_statuses}
        ]
    elif s == "scheduled":
        return [
            p for p in projects
            if _get_field(p, ["Status", "status"]) in scheduled_statuses
            or _norm(_get_field(p, ["Status", "status"])) in {_norm(x) for x in scheduled_statuses}
        ]
    else:
        return [
            p for p in projects
            if _norm(_get_field(p, ["Status", "status"])) == s
        ]


def _apply_category_filter(projects: List[Dict], category: str) -> List[Dict]:
    """Filter projects by category."""
    c = _norm(category)
    category_buckets = _get_category_buckets()

    def _matches_bucket(proj_category: str, bucket_keywords: set) -> bool:
        """Check if project category contains any bucket keyword or vice versa."""
        pc = _norm(proj_category)
        for kw in bucket_keywords:
            if kw in pc or pc in kw:
                return True
        return False

    if c in category_buckets:
        # Direct bucket name match
        allowed = category_buckets[c]
        logger.info(f"[FILTER] Using bucket '{c}' with {len(allowed)} keywords")
        return [
            p for p in projects
            if _matches_bucket(_get_field(p, ["Category", "category"]) or "", allowed)
        ]
    else:
        # Check if term is a keyword in any bucket
        resolved_bucket = find_category_bucket_for_keyword(c)
        if resolved_bucket and resolved_bucket in category_buckets:
            allowed = category_buckets[resolved_bucket]
            logger.info(f"[FILTER] Resolved keyword '{c}' to bucket '{resolved_bucket}'")
            return [
                p for p in projects
                if _matches_bucket(_get_field(p, ["Category", "category"]) or "", allowed)
            ]
        else:
            # Fall back to partial match
            logger.info(f"[FILTER] No bucket match for '{c}', using partial match")
            return [
                p for p in projects
                if c in _norm(_get_field(p, ["Category", "category"]) or "")
            ]


def _apply_project_type_filter(projects: List[Dict], project_type: str) -> List[Dict]:
    """Filter projects by type."""
    pt = _norm(project_type)
    return [
        p for p in projects
        if _norm(_get_field(p, ["Type", "type", "projectType"])) == pt
    ]


def _get_technician_name(project: Dict) -> str:
    """Extract technician/installer name from project using various field names."""
    # Try nested installer object
    installer = project.get('installer', {})
    if isinstance(installer, dict):
        name = installer.get('name', '')
        if name:
            return name

    # Try nested technician object
    technician = project.get('technician', {})
    if isinstance(technician, dict):
        name = technician.get('name', '')
        if name:
            return name

    # Try dashboard format (user_idata_first_name, user_idata_last_name)
    first = project.get('user_idata_first_name') or project.get('installer_first_name') or ''
    last = project.get('user_idata_last_name') or project.get('installer_last_name') or ''
    if first or last:
        return f"{first} {last}".strip()

    # Try direct technician_name field
    tech_name = project.get('technician_name') or project.get('installerName') or ''
    if tech_name:
        return tech_name

    return ''


def _apply_technician_filter(projects: List[Dict], technician_name: str) -> List[Dict]:
    """Filter projects by technician/installer name."""
    tn = _norm(technician_name)
    logger.info(f"[FILTER] Filtering by technician_name: '{technician_name}'")

    result = [p for p in projects if tn in _norm(_get_technician_name(p))]
    logger.info(f"[FILTER] After technician filter: {len(result)} projects")
    return result


def _apply_address_filter(projects: List[Dict], address: str) -> List[Dict]:
    """Filter projects by address."""
    addr = _norm(address)
    logger.info(f"[FILTER] Filtering by address: '{address}'")

    def _get_address_string(project: Dict) -> str:
        addr_field = project.get('address', project.get('Address', ''))
        if isinstance(addr_field, str):
            return addr_field
        if isinstance(addr_field, dict):
            parts = [
                addr_field.get('street', ''),
                addr_field.get('address', ''),
                addr_field.get('address1', ''),
                addr_field.get('addressLine1', ''),
                addr_field.get('line1', ''),
                addr_field.get('city', ''),
                addr_field.get('state', ''),
                addr_field.get('zip', ''),
                addr_field.get('zipCode', ''),
                addr_field.get('postalCode', ''),
            ]
            return ' '.join(p for p in parts if p)
        return ''

    # Debug logging
    if projects:
        sample_addr = projects[0].get('address', projects[0].get('Address', 'NO_ADDRESS_FIELD'))
        logger.info(f"[FILTER] Sample address format: {type(sample_addr).__name__} = {sample_addr}")

    result = [p for p in projects if addr in _norm(_get_address_string(p))]
    logger.info(f"[FILTER] After address filter: {len(result)} projects")
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# EXCLUSION FILTER IMPLEMENTATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def _apply_exclude_status_filter(projects: List[Dict], exclude_status) -> List[Dict]:
    """Exclude projects with specified statuses."""
    if isinstance(exclude_status, str):
        exclude_status = [exclude_status]

    excluded = {_norm(s) for s in exclude_status}

    # Expand "schedulable" and "scheduled" to their status sets
    if "schedulable" in excluded:
        excluded.update(_norm(s) for s in _get_schedulable_statuses())
    if "scheduled" in excluded:
        excluded.update(_norm(s) for s in _get_scheduled_statuses())

    logger.info(f"[FILTER] Excluding statuses: {exclude_status}")
    result = [
        p for p in projects
        if _norm(_get_field(p, ["Status", "status"])) not in excluded
    ]
    logger.info(f"[FILTER] After exclude_status: {len(result)} projects")
    return result


def _apply_exclude_category_filter(projects: List[Dict], exclude_category) -> List[Dict]:
    """Exclude projects with specified categories."""
    if isinstance(exclude_category, str):
        exclude_category = [exclude_category]

    excluded_cats = {_norm(c) for c in exclude_category}
    category_buckets = _get_category_buckets()

    # Expand bucket names to their keywords
    expanded_exclusions = set()
    for cat in excluded_cats:
        if cat in category_buckets:
            expanded_exclusions.update(_norm(kw) for kw in category_buckets[cat])
        else:
            expanded_exclusions.add(cat)

    logger.info(f"[FILTER] Excluding categories: {exclude_category} (expanded: {len(expanded_exclusions)} terms)")

    def _category_excluded(proj_category: str) -> bool:
        pc = _norm(proj_category)
        for excl in expanded_exclusions:
            if excl in pc or pc in excl:
                return True
        return False

    result = [
        p for p in projects
        if not _category_excluded(_get_field(p, ["Category", "category"]) or "")
    ]
    logger.info(f"[FILTER] After exclude_category: {len(result)} projects")
    return result


def _apply_exclude_technician_filter(projects: List[Dict], exclude_technician) -> List[Dict]:
    """Exclude projects with specified technicians."""
    if isinstance(exclude_technician, str):
        exclude_technician = [exclude_technician]

    excluded_techs = {_norm(t) for t in exclude_technician}
    logger.info(f"[FILTER] Excluding technicians: {exclude_technician}")

    def _technician_excluded(proj_tech: str) -> bool:
        if not proj_tech:
            return False  # Don't exclude unassigned projects
        pt = _norm(proj_tech)
        for excl in excluded_techs:
            if excl in pt or pt in excl:
                return True
        return False

    result = [
        p for p in projects
        if not _technician_excluded(_get_technician_name(p))
    ]
    logger.info(f"[FILTER] After exclude_technician: {len(result)} projects")
    return result


def _apply_exclude_address_filter(projects: List[Dict], exclude_address) -> List[Dict]:
    """Exclude projects at specified addresses."""
    if isinstance(exclude_address, str):
        exclude_address = [exclude_address]

    excluded_addrs = {_norm(a) for a in exclude_address}
    logger.info(f"[FILTER] Excluding addresses: {exclude_address}")

    def _address_excluded(proj_addr: str) -> bool:
        if not proj_addr:
            return False
        pa = _norm(proj_addr)
        for excl in excluded_addrs:
            if excl in pa or pa in excl:
                return True
        return False

    def _get_address_string(project: Dict) -> str:
        # Try multiple field names
        addr = (
            project.get('address') or
            project.get('Address') or
            project.get('installation_address_address1') or
            project.get('addressLine1') or
            ''
        )
        if isinstance(addr, str):
            return addr
        if isinstance(addr, dict):
            return addr.get('address1', '') or addr.get('street', '') or addr.get('line1', '')
        return ''

    result = [
        p for p in projects
        if not _address_excluded(_get_address_string(p))
    ]
    logger.info(f"[FILTER] After exclude_address: {len(result)} projects")
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# ORDINAL SELECTION
# ═══════════════════════════════════════════════════════════════════════════════

ORDINAL_MAP = {
    "first": 1, "1st": 1,
    "second": 2, "2nd": 2,
    "third": 3, "3rd": 3,
    "fourth": 4, "4th": 4,
    "fifth": 5, "5th": 5,
    "sixth": 6, "6th": 6,
    "seventh": 7, "7th": 7,
    "eighth": 8, "8th": 8,
    "ninth": 9, "9th": 9,
    "tenth": 10, "10th": 10,
    "last": -1,
}


def _apply_ordinal_selection(projects: List[Dict], ordinal) -> List[Dict]:
    """Apply ordinal selection to filtered results."""
    if not projects:
        return projects

    # Convert ordinal to index
    if isinstance(ordinal, int):
        idx = ordinal
    elif isinstance(ordinal, str):
        idx = ORDINAL_MAP.get(ordinal.lower())
        if idx is None:
            try:
                idx = int(ordinal)
            except ValueError:
                idx = None

    if idx is None:
        return projects

    logger.info(f"[FILTER] Applying ordinal '{ordinal}' (index={idx}) to {len(projects)} filtered results")

    if idx == -1:
        # Last item
        result = [projects[-1]]
    elif 1 <= idx <= len(projects):
        # 1-indexed to 0-indexed
        result = [projects[idx - 1]]
    else:
        logger.warning(f"[FILTER] Ordinal {idx} out of range for {len(projects)} results")
        result = []

    logger.info(f"[FILTER] After ordinal selection: {len(result)} project(s)")
    return result
