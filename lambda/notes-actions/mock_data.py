"""
Mock API responses for Notes Actions
Based on real API responses from core/tools.py analysis
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any
import uuid

# In-memory mock notes database
MOCK_NOTES_DB: Dict[str, List[Dict]] = {}

def get_mock_add_note(project_id: str, note_text: str, author: str = "Agent") -> Dict[str, Any]:
    """
    Mock response for Add Note API
    POST /project-notes/add/{client_id}
    """
    # Generate note
    note = {
        "note_id": str(uuid.uuid4()),
        "project_id": project_id,
        "note_text": note_text,
        "author": author,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # Store in mock database
    if project_id not in MOCK_NOTES_DB:
        MOCK_NOTES_DB[project_id] = []
    MOCK_NOTES_DB[project_id].append(note)

    return {
        "status": "success",
        "message": f"✅ [MOCK] Note added successfully to project {project_id}",
        "data": note
    }

def get_mock_list_notes(project_id: str) -> Dict[str, Any]:
    """
    Mock response for List Notes API
    GET /project-notes/list/{client_id}?project_id={project_id}

    Note: This API endpoint may not exist in PF360.
    Using mock data for development.
    """
    # Get notes from mock database or return sample notes
    notes = MOCK_NOTES_DB.get(project_id, [])

    # If no notes in database, return some sample notes
    if not notes:
        notes = [
            {
                "note_id": "note-001",
                "project_id": project_id,
                "note_text": "Customer requested morning appointment",
                "author": "Sales Team",
                "created_at": (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S")
            },
            {
                "note_id": "note-002",
                "project_id": project_id,
                "note_text": "Need to confirm access to installation area",
                "author": "Scheduling Team",
                "created_at": (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
            },
            {
                "note_id": "note-003",
                "project_id": project_id,
                "note_text": "Customer confirmed appointment for next week",
                "author": "Agent",
                "created_at": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
            }
        ]

    return {
        "status": "success",
        "data": {
            "project_id": project_id,
            "notes": notes,
            "total_count": len(notes)
        }
    }

def reset_mock_notes_db():
    """Reset the mock notes database (useful for testing)"""
    global MOCK_NOTES_DB
    MOCK_NOTES_DB = {}

# Example usage for testing
if __name__ == "__main__":
    import json

    print("=== Add Note ===")
    add_result = get_mock_add_note("12345", "Test note from agent", "Test Agent")
    print(json.dumps(add_result, indent=2))

    print("\n=== List Notes (with added note) ===")
    list_result = get_mock_list_notes("12345")
    print(json.dumps(list_result, indent=2))

    print("\n=== List Notes (different project) ===")
    list_result2 = get_mock_list_notes("12347")
    print(json.dumps(list_result2, indent=2))

    print("\n=== Reset Database ===")
    reset_mock_notes_db()
    print("Mock database reset")

    print("\n=== List Notes (after reset) ===")
    list_result3 = get_mock_list_notes("12345")
    print(json.dumps(list_result3, indent=2))
