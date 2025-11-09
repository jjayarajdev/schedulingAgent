"""
VERIFIED Data Extraction Functions
Based on actual API response: 9244 lines for 8 projects = ~1155 lines per project

Key Findings from Actual API Response:
- Each project has 270+ fields spread across flat structure
- Converted dates already exist: "convertedProjectStartScheduledDate" and "convertedProjectEndScheduledDate"
- projectDocument is an array (empty [] or with items)
- service_time_duration_value is in minutes as string "675.0000"
"""

from typing import Dict, Any, List, Optional

def safe_get(obj: Any, *keys, default=None) -> Any:
    """
    Safely navigate nested dictionaries
    Critical for performance - avoids try-except overhead
    """
    result = obj
    for key in keys:
        if isinstance(result, dict):
            result = result.get(key)
            if result is None:
                return default
        else:
            return default
    return result if result is not None else default


def extract_project_from_flat_api(item: Dict) -> Dict[str, Any]:
    """
    VERIFIED extraction from actual API response structure
    
    API Response Structure (flat with prefixes):
    - project_*: Project fields
    - project_category_*: Category fields
    - project_type_*: Type fields
    - installation_address_*: Address fields
    - store_info_*: Store fields
    - user_idata_*: Installer user fields
    - installer_details_*: Installer details
    - service_time_*: Service time fields
    - convertedProjectStartScheduledDate: Pre-formatted date
    - projectDocument: Array of documents
    
    Extracts 1155 lines → ~50 lines (95% reduction)
    """
    
    # Core project info (always present)
    project = {
        "id": str(safe_get(item, "project_project_id", default="")),
        "projectNumber": safe_get(item, "project_project_number", default=""),
        "poNumber": safe_get(item, "project_po_number", default=""),
        "status": safe_get(item, "status_info_status", default=""),
        "category": safe_get(item, "project_category_category", default=""),
        "projectType": safe_get(item, "project_type_project_type", default=""),
    }
    
    # Scheduled dates - use converted dates (already formatted!)
    converted_start = safe_get(item, "convertedProjectStartScheduledDate")
    if converted_start:
        project["scheduledDate"] = converted_start
        project["scheduledEndDate"] = safe_get(item, "convertedProjectEndScheduledDate", default="")
    
    # Installation address - build compact structure
    address = {}
    address1 = safe_get(item, "installation_address_address1", default="")
    if address1:
        address["address1"] = address1
        
        address2 = safe_get(item, "installation_address_address2")
        if address2:
            address["address2"] = address2
            
        city = safe_get(item, "installation_address_city", default="")
        state = safe_get(item, "installation_address_state", default="")
        zipcode = safe_get(item, "installation_address_zipcode", default="")
        
        if city:
            address["city"] = city
        if state:
            address["state"] = state
        if zipcode:
            address["zipcode"] = zipcode
    
    # Only add address if we have any data
    if address:
        project["address"] = address
    
    # Store info
    store_name = safe_get(item, "store_info_store_name", default="")
    store_number = safe_get(item, "store_info_store_number")
    if store_name or store_number is not None:
        project["store"] = {}
        if store_name:
            project["store"]["storeName"] = store_name
        if store_number is not None:
            project["store"]["storeNumber"] = store_number
    
    # Installer/Technician info - only if assigned
    installer_first = safe_get(item, "user_idata_first_name")
    installer_id = safe_get(item, "installer_details_installer_id")
    
    if installer_first and installer_id:
        installer_last = safe_get(item, "user_idata_last_name", default="")
        installer_name = f"{installer_first} {installer_last}".strip()
        
        project["installer"] = {
            "name": installer_name,
            "id": str(installer_id)
        }
        
        # Optional installer details
        installer_bio = safe_get(item, "user_idata_installerbio")
        if installer_bio:
            project["installer"]["bio"] = installer_bio
    
    # Source system
    source_name = safe_get(item, "source_system_source_name")
    if source_name:
        project["sourceSystem"] = source_name
    
    # Date sold - format from ISO to simple date
    date_sold = safe_get(item, "project_date_sold")
    if date_sold:
        # "2025-11-03T10:41:46.000Z" → "2025-11-03"
        project["dateSold"] = date_sold.split("T")[0] if "T" in date_sold else date_sold
    
    # Documents - check if array has items
    project_documents = safe_get(item, "projectDocument", default=[])
    project["hasDocuments"] = isinstance(project_documents, list) and len(project_documents) > 0
    
    # Service time/duration
    service_duration = safe_get(item, "service_time_duration_value")
    service_unit = safe_get(item, "service_time_duration_type", default="minutes")
    if service_duration:
        # Convert "675.0000" → "675 minutes" or "11.25 hours"
        try:
            duration_float = float(service_duration)
            if service_unit == "minute" or service_unit == "minutes":
                # Convert minutes to hours for better readability if >= 60
                if duration_float >= 60:
                    hours = duration_float / 60
                    project["estimatedDuration"] = f"{hours:.1f} hours"
                else:
                    project["estimatedDuration"] = f"{int(duration_float)} minutes"
            else:
                project["estimatedDuration"] = f"{duration_float:.1f} {service_unit}"
        except (ValueError, TypeError):
            project["estimatedDuration"] = f"{service_duration} {service_unit}"
    
    return project


def format_projects_for_ui(projects: List[Dict], customer_id: str = "") -> Dict[str, Any]:
    """
    Format project list exactly as UI expects
    Agent receives this ready for display - NO additional work needed
    
    Matches scheduling_collaborator.txt lines 121-129 format
    """
    project_count = len(projects)
    
    if project_count == 0:
        return {
            "message": "No projects found for this customer.",
            "projects": []
        }
    
    # Get common info from first project for message
    first_project = projects[0] if projects else {}
    category = first_project.get("category", "")
    project_type = first_project.get("projectType", "")
    
    # Get address for message
    address_str = ""
    if "address" in first_project:
        addr = first_project["address"]
        addr1 = addr.get("address1", "")
        city = addr.get("city", "")
        if addr1 and city:
            address_str = f" at {addr1}, {city}"
    
    # Build descriptive message
    if category and project_type:
        message = f"You have {project_count} {category} {project_type} project{'s' if project_count != 1 else ''}{address_str}:"
    elif category:
        message = f"You have {project_count} {category} project{'s' if project_count != 1 else ''}{address_str}:"
    else:
        message = f"You have {project_count} project{'s' if project_count != 1 else ''}{address_str}:"
    
    return {
        "message": message,
        "projects": projects
    }


def calculate_payload_reduction(raw_api_response: Dict) -> Dict[str, Any]:
    """
    Calculate actual payload reduction from optimization
    Useful for monitoring and metrics
    """
    import json
    
    raw_data = raw_api_response.get("data", [])
    
    # Original size
    original_json = json.dumps(raw_api_response, separators=(',', ':'))
    original_size = len(original_json)
    original_lines = original_json.count('\n')
    
    # Optimized size
    projects = [extract_project_from_flat_api(item) for item in raw_data]
    optimized_response = format_projects_for_ui(projects)
    optimized_json = json.dumps(optimized_response, separators=(',', ':'))
    optimized_size = len(optimized_json)
    optimized_lines = optimized_json.count('\n')
    
    reduction_percentage = ((original_size - optimized_size) / original_size * 100) if original_size > 0 else 0
    
    return {
        "original_size_bytes": original_size,
        "original_lines": original_lines,
        "optimized_size_bytes": optimized_size,
        "optimized_lines": optimized_lines,
        "reduction_bytes": original_size - optimized_size,
        "reduction_percentage": round(reduction_percentage, 2),
        "project_count": len(projects)
    }


# Example usage for testing
if __name__ == "__main__":
    import json
    
    # Load the actual API response
    with open('/mnt/user-data/uploads/apiresponse.json', 'r') as f:
        api_response = json.load(f)
    
    print("=" * 80)
    print("ACTUAL API RESPONSE ANALYSIS")
    print("=" * 80)
    
    # Analyze payload reduction
    stats = calculate_payload_reduction(api_response)
    
    print(f"\n📊 Payload Statistics:")
    print(f"   Original size: {stats['original_size_bytes']:,} bytes ({stats['original_lines']:,} lines)")
    print(f"   Optimized size: {stats['optimized_size_bytes']:,} bytes ({stats['optimized_lines']:,} lines)")
    print(f"   Reduction: {stats['reduction_bytes']:,} bytes ({stats['reduction_percentage']}%)")
    print(f"   Projects: {stats['project_count']}")
    
    # Extract and format projects
    raw_data = api_response.get("data", [])
    projects = [extract_project_from_flat_api(item) for item in raw_data]
    formatted = format_projects_for_ui(projects)
    
    print(f"\n📦 Formatted Output:")
    print(json.dumps(formatted, indent=2))
    
    print(f"\n✅ Per-project average:")
    print(f"   Original: {stats['original_size_bytes'] // stats['project_count']:,} bytes/project")
    print(f"   Optimized: {stats['optimized_size_bytes'] // stats['project_count']:,} bytes/project")
    print(f"   Reduction: {(stats['original_size_bytes'] - stats['optimized_size_bytes']) // stats['project_count']:,} bytes/project")
