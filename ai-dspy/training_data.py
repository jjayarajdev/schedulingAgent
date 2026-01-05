"""
Training Data for DSPy Optimization

Examples derived from real ProjectForce orchestrator usage patterns.
Used by teleprompters to optimize prompts automatically.
"""
import dspy


# =============================================================================
# INTENT CLASSIFICATION EXAMPLES
# =============================================================================

CLASSIFICATION_EXAMPLES = [
    # =========================================================================
    # PROJECT LIST QUERIES
    # =========================================================================
    dspy.Example(
        message="list my projects",
        conversation_summary="",
        intent="scheduling",
        action="list_projects",
        confidence="high",
        reasoning="User explicitly asks to list/show their projects"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="show me my all project",
        conversation_summary="",
        intent="scheduling",
        action="list_projects",
        confidence="high",
        reasoning="User wants to see all their projects"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="Show me all ready-to-schedule projects with project number",
        conversation_summary="",
        intent="scheduling",
        action="list_projects",
        confidence="high",
        reasoning="User wants filtered list of projects by status"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="Show me all the projects assigned to technician Peter PF",
        conversation_summary="",
        intent="scheduling",
        action="list_projects",
        confidence="high",
        reasoning="User wants projects filtered by technician name"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="Show me all the projects that are scheduled for january",
        conversation_summary="",
        intent="scheduling",
        action="list_projects",
        confidence="high",
        reasoning="User wants scheduled projects filtered by month"
    ).with_inputs("message", "conversation_summary"),

    # =========================================================================
    # PROJECT DETAILS/INFORMATION
    # =========================================================================
    dspy.Example(
        message="Show me the status of project 675656565",
        conversation_summary="",
        intent="information",
        action="get_project_details",
        confidence="high",
        reasoning="User asking for status of a specific project by ID"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="Show me the details for project AI-PRO-1000010",
        conversation_summary="",
        intent="information",
        action="get_project_details",
        confidence="high",
        reasoning="User asking for details of a specific project"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="Show me the full details for project number AI-PRO-1000010",
        conversation_summary="",
        intent="information",
        action="get_project_details",
        confidence="high",
        reasoning="User wants complete project information"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="Show me the category of project AI-PRO-1000010",
        conversation_summary="",
        intent="information",
        action="get_project_details",
        confidence="high",
        reasoning="User asking for specific field (category) of a project"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="please provide the schedule tech information and schedule start date and end date for AI-PRO-1000010 project no",
        conversation_summary="",
        intent="information",
        action="get_project_details",
        confidence="high",
        reasoning="User asking for technician and schedule information"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="Retrieve the installation address and technician information for project number 524523452_1",
        conversation_summary="",
        intent="information",
        action="get_project_details",
        confidence="high",
        reasoning="User wants address and technician details for project"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="tell me about my fence project",
        conversation_summary="",
        intent="information",
        action="get_project_details",
        confidence="high",
        reasoning="User wants details about a specific project type"
    ).with_inputs("message", "conversation_summary"),

    # =========================================================================
    # ADDRESS-BASED PROJECT LOOKUP
    # =========================================================================
    dspy.Example(
        message="for this installation address 124 SW Barber Glenn Drive Southwest Barber Glen, FL, Fort White-32038 give me the project no",
        conversation_summary="",
        intent="information",
        action="get_project_details",
        confidence="high",
        reasoning="User looking up project by installation address"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="Retrieve the project number and all related details for the installation address 124 SW Barber Glenn Drive",
        conversation_summary="",
        intent="information",
        action="get_project_details",
        confidence="high",
        reasoning="User wants project info based on address lookup"
    ).with_inputs("message", "conversation_summary"),

    # =========================================================================
    # DOCUMENT QUERIES
    # =========================================================================
    dspy.Example(
        message="Show me the list of related documents for project 524523452",
        conversation_summary="",
        intent="information",
        action="get_project_details",
        confidence="high",
        reasoning="User asking for project documents"
    ).with_inputs("message", "conversation_summary"),

    # =========================================================================
    # SCHEDULING - AVAILABLE DATES
    # =========================================================================
    dspy.Example(
        message="schedule my decking project",
        conversation_summary="",
        intent="scheduling",
        action="get_available_dates",
        confidence="high",
        reasoning="User wants to schedule a specific project type"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="Show me the available dates for scheduling work for project AI-PRO-100007",
        conversation_summary="",
        intent="scheduling",
        action="get_available_dates",
        confidence="high",
        reasoning="User explicitly asking for available scheduling dates"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="Show me the available dates for scheduling tasks for project AI-PRO-1000010",
        conversation_summary="",
        intent="scheduling",
        action="get_available_dates",
        confidence="high",
        reasoning="User asking for available dates to schedule"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="Show me the earliest available appointment date for this project AI-PRO-100007",
        conversation_summary="",
        intent="scheduling",
        action="get_available_dates",
        confidence="high",
        reasoning="User wants earliest available date"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="show me the available dates in January for project AI-PRO-1000010",
        conversation_summary="",
        intent="scheduling",
        action="get_available_dates",
        confidence="high",
        reasoning="User wants dates filtered by month"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="what dates are available for my kitchen sink?",
        conversation_summary="User has a kitchen sink project #9000407",
        intent="scheduling",
        action="get_available_dates",
        confidence="high",
        reasoning="User asking about available dates for scheduling"
    ).with_inputs("message", "conversation_summary"),

    # =========================================================================
    # SCHEDULING - RELATIVE DATE QUERIES
    # =========================================================================
    dspy.Example(
        message="show me next week dates",
        conversation_summary="User scheduling project #9000489",
        intent="scheduling",
        action="get_available_dates",
        confidence="high",
        reasoning="User asking for dates in next week"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="show me next month dates",
        conversation_summary="User scheduling project #9000489",
        intent="scheduling",
        action="get_available_dates",
        confidence="high",
        reasoning="User asking for dates in next month"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="Give me the upcoming week",
        conversation_summary="User viewing available dates",
        intent="scheduling",
        action="get_available_dates",
        confidence="high",
        reasoning="User asking for next week's dates"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="Show me the week after the current week",
        conversation_summary="User scheduling project",
        intent="scheduling",
        action="get_available_dates",
        confidence="high",
        reasoning="User asking for following week's dates"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="Display dates for the next week",
        conversation_summary="",
        intent="scheduling",
        action="get_available_dates",
        confidence="high",
        reasoning="User requesting next week's available dates"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="Can you show me the next available week?",
        conversation_summary="",
        intent="scheduling",
        action="get_available_dates",
        confidence="high",
        reasoning="User asking for next available week"
    ).with_inputs("message", "conversation_summary"),

    # =========================================================================
    # SCHEDULING - TIME SLOTS
    # =========================================================================
    dspy.Example(
        message="i want to schedule project no 675656565 please suggest available today slots",
        conversation_summary="",
        intent="scheduling",
        action="get_time_slots",
        confidence="high",
        reasoning="User asking for today's time slots for specific project"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="I want to schedule project 675656565. Please show me the available time slots for tomorrow / day after tomorrow",
        conversation_summary="",
        intent="scheduling",
        action="get_time_slots",
        confidence="high",
        reasoning="User asking for time slots for specific dates"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="Show me the available time slots on 31st December for project number 12125_09PF05VD_1765791831881",
        conversation_summary="",
        intent="scheduling",
        action="get_time_slots",
        confidence="high",
        reasoning="User asking for time slots on specific date"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="Show me the available time slots on 31st December for project 9000287",
        conversation_summary="",
        intent="scheduling",
        action="get_time_slots",
        confidence="high",
        reasoning="User asking for time slots on specific date"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="show me 23 February slots",
        conversation_summary="User scheduling project #9000489",
        intent="scheduling",
        action="get_time_slots",
        confidence="high",
        reasoning="User asking for slots on a specific date"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="tomorrow",
        conversation_summary="Assistant showed available dates: Jan 5, 6, 7, 8",
        intent="scheduling",
        action="get_time_slots",
        confidence="high",
        reasoning="User selecting a date after seeing available dates"
    ).with_inputs("message", "conversation_summary"),

    # =========================================================================
    # SCHEDULING - BOOKING/CONFIRMATION
    # =========================================================================
    dspy.Example(
        message="i want to schedule my appointments for project AI-PRO-1000010 - can u help?",
        conversation_summary="",
        intent="scheduling",
        action="get_available_dates",
        confidence="high",
        reasoning="User wants help scheduling - start with available dates"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="I want to schedule an appointment for Project No: AI-PRO-1000010. What slots can you book?",
        conversation_summary="",
        intent="scheduling",
        action="get_available_dates",
        confidence="high",
        reasoning="User asking about booking - need to show dates first"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="8 AM please",
        conversation_summary="Assistant showed time slots for Jan 6: 8 AM, 8:30 AM, 1 PM",
        intent="scheduling",
        action="confirm_appointment",
        confidence="high",
        reasoning="User selecting a time slot to confirm appointment"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="yes, book it",
        conversation_summary="Assistant asked to confirm: Decking project Jan 6 at 8 AM",
        intent="scheduling",
        action="confirm_appointment",
        confidence="high",
        reasoning="User confirming the appointment"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="yes",
        conversation_summary="Assistant asked: Would you like to confirm Decking project on Jan 6 at 8 AM?",
        intent="scheduling",
        action="confirm_appointment",
        confidence="high",
        reasoning="User confirming with 'yes' after confirmation prompt"
    ).with_inputs("message", "conversation_summary"),

    # =========================================================================
    # RESCHEDULE / CANCEL
    # =========================================================================
    dspy.Example(
        message="reschedule my washer dryer",
        conversation_summary="",
        intent="scheduling",
        action="reschedule_appointment",
        confidence="high",
        reasoning="User explicitly wants to reschedule"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="cancel the decking appointment",
        conversation_summary="",
        intent="scheduling",
        action="cancel_appointment",
        confidence="high",
        reasoning="User explicitly wants to cancel"
    ).with_inputs("message", "conversation_summary"),

    # =========================================================================
    # WEATHER QUERIES
    # =========================================================================
    dspy.Example(
        message="what's the weather like for tomorrow",
        conversation_summary="User viewing time slots for Jan 6 in Minneapolis",
        intent="information",
        action="get_weather",
        confidence="high",
        reasoning="Weather query during scheduling workflow"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="how is the weather for the day",
        conversation_summary="Scheduling decking project in Minneapolis for Jan 6",
        intent="information",
        action="get_weather",
        confidence="high",
        reasoning="Weather query using context from scheduling"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="how is the weather for given date",
        conversation_summary="User viewing time slots for Jan 6",
        intent="information",
        action="get_weather",
        confidence="high",
        reasoning="Weather query for the date being scheduled"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="how is the weather",
        conversation_summary="User scheduling outdoor project in Minneapolis",
        intent="information",
        action="get_weather",
        confidence="high",
        reasoning="General weather query - use project context"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="if there rain / summer / winter",
        conversation_summary="User scheduling outdoor decking project",
        intent="information",
        action="get_weather",
        confidence="high",
        reasoning="User asking about weather conditions"
    ).with_inputs("message", "conversation_summary"),

    # =========================================================================
    # CHITCHAT / GREETINGS / HELP
    # =========================================================================
    dspy.Example(
        message="hi",
        conversation_summary="",
        intent="chitchat",
        action="greet",
        confidence="high",
        reasoning="Simple greeting"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="what can you help me with?",
        conversation_summary="",
        intent="chitchat",
        action="help",
        confidence="high",
        reasoning="User asking for help/capabilities"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="thank you",
        conversation_summary="Assistant just confirmed appointment",
        intent="chitchat",
        action="general",
        confidence="high",
        reasoning="Gratitude expression"
    ).with_inputs("message", "conversation_summary"),

    # =========================================================================
    # FILTERING AFTER LIST (NOT SCHEDULING)
    # =========================================================================
    dspy.Example(
        message="just the kitchen ones",
        conversation_summary="Assistant listed 10 projects including kitchen, decking, roofing",
        intent="scheduling",
        action="list_projects",
        confidence="high",
        reasoning="User filtering the list, not scheduling"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="show me the decking project",
        conversation_summary="Assistant listed projects",
        intent="information",
        action="get_project_details",
        confidence="high",
        reasoning="User wants to view details, not schedule"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="what's scheduled?",
        conversation_summary="",
        intent="scheduling",
        action="list_projects",
        confidence="high",
        reasoning="Calendar/schedule query - list scheduled projects"
    ).with_inputs("message", "conversation_summary"),

    # =========================================================================
    # COMPLAINTS / FEEDBACK
    # =========================================================================
    dspy.Example(
        message="AI-PRO-1000010 All the information is showing incorrectly. There is no technician assigned, and the installation address is also incorrect.",
        conversation_summary="",
        intent="information",
        action="get_project_details",
        confidence="medium",
        reasoning="User reporting data issue - may need to show current details"
    ).with_inputs("message", "conversation_summary"),

    # =========================================================================
    # PROJECT LIST - PHRASING VARIATIONS
    # =========================================================================
    dspy.Example(
        message="pull up my projects",
        conversation_summary="",
        intent="scheduling",
        action="list_projects",
        confidence="high",
        reasoning="User asking to view their projects"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="fetch all my orders",
        conversation_summary="",
        intent="scheduling",
        action="list_projects",
        confidence="high",
        reasoning="Orders/jobs are synonyms for projects"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="give me a list of my jobs",
        conversation_summary="",
        intent="scheduling",
        action="list_projects",
        confidence="high",
        reasoning="Jobs is synonym for projects"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="what jobs do I have",
        conversation_summary="",
        intent="scheduling",
        action="list_projects",
        confidence="high",
        reasoning="Query about user's projects"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="display my work orders",
        conversation_summary="",
        intent="scheduling",
        action="list_projects",
        confidence="high",
        reasoning="Work orders = projects"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="show projects",
        conversation_summary="",
        intent="scheduling",
        action="list_projects",
        confidence="high",
        reasoning="Simple list request"
    ).with_inputs("message", "conversation_summary"),

    # =========================================================================
    # PROJECT LIST - CATEGORY VARIATIONS
    # =========================================================================
    dspy.Example(
        message="show me my bathroom projects",
        conversation_summary="",
        intent="scheduling",
        action="list_projects",
        confidence="high",
        reasoning="Filtering by bathroom category"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="list flooring jobs",
        conversation_summary="",
        intent="scheduling",
        action="list_projects",
        confidence="high",
        reasoning="Filtering by flooring category"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="show my roofing projects",
        conversation_summary="",
        intent="scheduling",
        action="list_projects",
        confidence="high",
        reasoning="Filtering by roofing category"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="what window projects do I have",
        conversation_summary="",
        intent="scheduling",
        action="list_projects",
        confidence="high",
        reasoning="Filtering by windows category"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="show me HVAC installations",
        conversation_summary="",
        intent="scheduling",
        action="list_projects",
        confidence="high",
        reasoning="Filtering by HVAC category"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="any appliance orders?",
        conversation_summary="",
        intent="scheduling",
        action="list_projects",
        confidence="high",
        reasoning="Filtering by appliance category"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="show exterior door projects",
        conversation_summary="",
        intent="scheduling",
        action="list_projects",
        confidence="high",
        reasoning="Filtering by exterior doors"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="list my countertop installations",
        conversation_summary="",
        intent="scheduling",
        action="list_projects",
        confidence="high",
        reasoning="Filtering by countertop category"
    ).with_inputs("message", "conversation_summary"),

    # =========================================================================
    # PROJECT LIST - STATUS VARIATIONS
    # =========================================================================
    dspy.Example(
        message="show me pending projects",
        conversation_summary="",
        intent="scheduling",
        action="list_projects",
        confidence="high",
        reasoning="Filtering by pending status"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="list completed jobs",
        conversation_summary="",
        intent="scheduling",
        action="list_projects",
        confidence="high",
        reasoning="Filtering by completed status"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="show cancelled orders",
        conversation_summary="",
        intent="scheduling",
        action="list_projects",
        confidence="high",
        reasoning="Filtering by cancelled status"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="projects that are in progress",
        conversation_summary="",
        intent="scheduling",
        action="list_projects",
        confidence="high",
        reasoning="Filtering by in-progress status"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="show me new projects",
        conversation_summary="",
        intent="scheduling",
        action="list_projects",
        confidence="high",
        reasoning="Filtering by new status"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="unscheduled jobs",
        conversation_summary="",
        intent="scheduling",
        action="list_projects",
        confidence="high",
        reasoning="Filtering by unscheduled/new status"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="projects on the books",
        conversation_summary="",
        intent="scheduling",
        action="list_projects",
        confidence="high",
        reasoning="Colloquial for scheduled projects"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="what's already booked",
        conversation_summary="",
        intent="scheduling",
        action="list_projects",
        confidence="high",
        reasoning="Asking for scheduled/booked projects"
    ).with_inputs("message", "conversation_summary"),

    # =========================================================================
    # PROJECT DETAILS - ID FORMAT VARIATIONS
    # =========================================================================
    dspy.Example(
        message="details for 123456",
        conversation_summary="",
        intent="information",
        action="get_project_details",
        confidence="high",
        reasoning="6-digit project ID lookup"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="what is project 12345678",
        conversation_summary="",
        intent="information",
        action="get_project_details",
        confidence="high",
        reasoning="8-digit project ID lookup"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="tell me about AI-PRO-999999",
        conversation_summary="",
        intent="information",
        action="get_project_details",
        confidence="high",
        reasoning="AI-PRO format project lookup"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="project 21083_09PF05VD",
        conversation_summary="",
        intent="information",
        action="get_project_details",
        confidence="high",
        reasoning="Complex underscore format ID"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="show 9000407_1",
        conversation_summary="",
        intent="information",
        action="get_project_details",
        confidence="high",
        reasoning="Project ID with underscore suffix"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="PF-2024-001234",
        conversation_summary="",
        intent="information",
        action="get_project_details",
        confidence="high",
        reasoning="PF prefix format project lookup"
    ).with_inputs("message", "conversation_summary"),

    # =========================================================================
    # PROJECT DETAILS - PHRASING VARIATIONS
    # =========================================================================
    dspy.Example(
        message="give me info on project 9000489",
        conversation_summary="",
        intent="information",
        action="get_project_details",
        confidence="high",
        reasoning="Info request for specific project"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="what's the status of 9000407",
        conversation_summary="",
        intent="information",
        action="get_project_details",
        confidence="high",
        reasoning="Status query for project"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="look up project number 9000489",
        conversation_summary="",
        intent="information",
        action="get_project_details",
        confidence="high",
        reasoning="Project lookup request"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="find project 9000287",
        conversation_summary="",
        intent="information",
        action="get_project_details",
        confidence="high",
        reasoning="Find/search for project"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="pull up order 9000489",
        conversation_summary="",
        intent="information",
        action="get_project_details",
        confidence="high",
        reasoning="Order = project synonym"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="I need details on my dishwasher installation",
        conversation_summary="User has dishwasher project #9000407",
        intent="information",
        action="get_project_details",
        confidence="high",
        reasoning="Asking about specific project by category"
    ).with_inputs("message", "conversation_summary"),

    # =========================================================================
    # SCHEDULING - PHRASING VARIATIONS
    # =========================================================================
    dspy.Example(
        message="book my kitchen project",
        conversation_summary="",
        intent="scheduling",
        action="get_available_dates",
        confidence="high",
        reasoning="Book = schedule"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="set up an appointment for project 9000489",
        conversation_summary="",
        intent="scheduling",
        action="get_available_dates",
        confidence="high",
        reasoning="Set up appointment = schedule"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="arrange installation for my flooring",
        conversation_summary="",
        intent="scheduling",
        action="get_available_dates",
        confidence="high",
        reasoning="Arrange installation = schedule"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="when can you come for the roofing job",
        conversation_summary="",
        intent="scheduling",
        action="get_available_dates",
        confidence="high",
        reasoning="Asking for availability"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="I need to get project 9000407 on the calendar",
        conversation_summary="",
        intent="scheduling",
        action="get_available_dates",
        confidence="high",
        reasoning="Get on calendar = schedule"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="let's schedule the window installation",
        conversation_summary="",
        intent="scheduling",
        action="get_available_dates",
        confidence="high",
        reasoning="Scheduling request for window project"
    ).with_inputs("message", "conversation_summary"),

    # =========================================================================
    # DATE/TIME EXPRESSIONS - ADVANCED
    # =========================================================================
    dspy.Example(
        message="show me dates for the end of January",
        conversation_summary="User scheduling project #9000489",
        intent="scheduling",
        action="get_available_dates",
        confidence="high",
        reasoning="End of month date range request"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="beginning of February",
        conversation_summary="User viewing available dates",
        intent="scheduling",
        action="get_available_dates",
        confidence="high",
        reasoning="Start of month date range"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="late March availability",
        conversation_summary="",
        intent="scheduling",
        action="get_available_dates",
        confidence="high",
        reasoning="End of month availability query"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="first week of February",
        conversation_summary="",
        intent="scheduling",
        action="get_available_dates",
        confidence="high",
        reasoning="Specific week of month request"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="last week of January",
        conversation_summary="",
        intent="scheduling",
        action="get_available_dates",
        confidence="high",
        reasoning="Last week of month request"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="2nd week of March",
        conversation_summary="",
        intent="scheduling",
        action="get_available_dates",
        confidence="high",
        reasoning="Second week of month"
    ).with_inputs("message", "conversation_summary"),

    # =========================================================================
    # AMBIGUOUS TIME QUERIES (without explicit action words)
    # =========================================================================
    dspy.Example(
        message="show me next week",
        conversation_summary="",
        intent="scheduling",
        action="get_available_dates",
        confidence="medium",
        reasoning="Ambiguous but likely wants to see availability for next week"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="show me the week after current week",
        conversation_summary="",
        intent="scheduling",
        action="get_available_dates",
        confidence="medium",
        reasoning="Asking about next week availability without explicit schedule keyword"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="show me the week after the current week",
        conversation_summary="",
        intent="scheduling",
        action="get_available_dates",
        confidence="medium",
        reasoning="Asking about next week - infer scheduling intent"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="what's available next week",
        conversation_summary="",
        intent="scheduling",
        action="get_available_dates",
        confidence="high",
        reasoning="Asking about scheduling availability for next week"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="next week availability",
        conversation_summary="",
        intent="scheduling",
        action="get_available_dates",
        confidence="high",
        reasoning="Availability query for next week"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="what do you have next week",
        conversation_summary="",
        intent="scheduling",
        action="get_available_dates",
        confidence="high",
        reasoning="Asking for available slots next week"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="show me this week",
        conversation_summary="",
        intent="scheduling",
        action="get_available_dates",
        confidence="medium",
        reasoning="Ambiguous but infer availability for current week"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="what about next month",
        conversation_summary="User viewing available dates",
        intent="scheduling",
        action="get_available_dates",
        confidence="high",
        reasoning="Asking for availability in next month"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="show me January",
        conversation_summary="",
        intent="scheduling",
        action="get_available_dates",
        confidence="medium",
        reasoning="Asking to see dates in January - infer scheduling"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="the following week",
        conversation_summary="User viewing dates for Jan 6-10",
        intent="scheduling",
        action="get_available_dates",
        confidence="high",
        reasoning="Navigate to the next week of dates"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="show schedule for the week after the current week",
        conversation_summary="",
        intent="scheduling",
        action="get_available_dates",
        confidence="high",
        reasoning="Explicit schedule keyword with next week timeframe"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="what's open next week",
        conversation_summary="",
        intent="scheduling",
        action="get_available_dates",
        confidence="high",
        reasoning="Open slots query for next week"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="any openings next week",
        conversation_summary="",
        intent="scheduling",
        action="get_available_dates",
        confidence="high",
        reasoning="Availability query using openings synonym"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="this Friday",
        conversation_summary="User scheduling project",
        intent="scheduling",
        action="get_time_slots",
        confidence="high",
        reasoning="Specific day this week"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="next Monday",
        conversation_summary="User scheduling project",
        intent="scheduling",
        action="get_time_slots",
        confidence="high",
        reasoning="Specific day next week"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="the 15th",
        conversation_summary="User viewing January dates",
        intent="scheduling",
        action="get_time_slots",
        confidence="high",
        reasoning="Selecting specific date"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="day after tomorrow",
        conversation_summary="",
        intent="scheduling",
        action="get_time_slots",
        confidence="high",
        reasoning="Relative date expression"
    ).with_inputs("message", "conversation_summary"),

    # =========================================================================
    # TIME PREFERENCES
    # =========================================================================
    dspy.Example(
        message="morning slots please",
        conversation_summary="User viewing time slots for Jan 6",
        intent="scheduling",
        action="get_time_slots",
        confidence="high",
        reasoning="Time preference query"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="anything in the afternoon?",
        conversation_summary="User viewing time slots",
        intent="scheduling",
        action="get_time_slots",
        confidence="high",
        reasoning="Afternoon time preference"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="do you have evening appointments",
        conversation_summary="",
        intent="scheduling",
        action="get_time_slots",
        confidence="high",
        reasoning="Evening availability query"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="earliest available time",
        conversation_summary="User selecting time slot",
        intent="scheduling",
        action="get_time_slots",
        confidence="high",
        reasoning="Earliest time preference"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="latest time slot",
        conversation_summary="User viewing time slots",
        intent="scheduling",
        action="get_time_slots",
        confidence="high",
        reasoning="Latest time preference"
    ).with_inputs("message", "conversation_summary"),

    # =========================================================================
    # CONFIRMATION VARIATIONS
    # =========================================================================
    dspy.Example(
        message="that works",
        conversation_summary="Assistant offered Jan 6 at 8 AM",
        intent="scheduling",
        action="confirm_appointment",
        confidence="high",
        reasoning="Confirming the offered slot"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="perfect",
        conversation_summary="Assistant asked to confirm appointment",
        intent="scheduling",
        action="confirm_appointment",
        confidence="high",
        reasoning="Positive confirmation"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="sounds good",
        conversation_summary="Assistant offered time slot",
        intent="scheduling",
        action="confirm_appointment",
        confidence="high",
        reasoning="Casual confirmation"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="let's do it",
        conversation_summary="Confirming appointment for Jan 6",
        intent="scheduling",
        action="confirm_appointment",
        confidence="high",
        reasoning="Enthusiastic confirmation"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="confirmed",
        conversation_summary="Assistant asked to confirm booking",
        intent="scheduling",
        action="confirm_appointment",
        confidence="high",
        reasoning="Explicit confirmation"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="go ahead and book it",
        conversation_summary="User viewing confirmation screen",
        intent="scheduling",
        action="confirm_appointment",
        confidence="high",
        reasoning="Confirmation with action"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="the first one",
        conversation_summary="Assistant showed slots: 8 AM, 10 AM, 1 PM",
        intent="scheduling",
        action="confirm_appointment",
        confidence="high",
        reasoning="Selecting first option"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="second option",
        conversation_summary="Assistant showed 3 time slots",
        intent="scheduling",
        action="confirm_appointment",
        confidence="high",
        reasoning="Selecting second option"
    ).with_inputs("message", "conversation_summary"),

    # =========================================================================
    # RESCHEDULE VARIATIONS
    # =========================================================================
    dspy.Example(
        message="I need to change my appointment",
        conversation_summary="",
        intent="scheduling",
        action="reschedule_appointment",
        confidence="high",
        reasoning="Change = reschedule"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="can we move the installation date",
        conversation_summary="",
        intent="scheduling",
        action="reschedule_appointment",
        confidence="high",
        reasoning="Move date = reschedule"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="the scheduled time doesn't work anymore",
        conversation_summary="User has scheduled project",
        intent="scheduling",
        action="reschedule_appointment",
        confidence="high",
        reasoning="Implies need to reschedule"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="push back project 9000489",
        conversation_summary="",
        intent="scheduling",
        action="reschedule_appointment",
        confidence="high",
        reasoning="Push back = reschedule later"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="postpone the kitchen install",
        conversation_summary="",
        intent="scheduling",
        action="reschedule_appointment",
        confidence="high",
        reasoning="Postpone = reschedule"
    ).with_inputs("message", "conversation_summary"),

    # =========================================================================
    # CANCEL VARIATIONS
    # =========================================================================
    dspy.Example(
        message="I want to cancel my order",
        conversation_summary="",
        intent="scheduling",
        action="cancel_appointment",
        confidence="high",
        reasoning="Cancel request"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="please cancel project 9000489",
        conversation_summary="",
        intent="scheduling",
        action="cancel_appointment",
        confidence="high",
        reasoning="Explicit cancel with project ID"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="I can't make the appointment",
        conversation_summary="User has scheduled project",
        intent="scheduling",
        action="cancel_appointment",
        confidence="high",
        reasoning="Implies cancellation needed"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="nevermind the installation",
        conversation_summary="",
        intent="scheduling",
        action="cancel_appointment",
        confidence="high",
        reasoning="Informal cancellation"
    ).with_inputs("message", "conversation_summary"),

    # =========================================================================
    # TECHNICIAN FILTER VARIATIONS
    # =========================================================================
    dspy.Example(
        message="projects for technician John Smith",
        conversation_summary="",
        intent="scheduling",
        action="list_projects",
        confidence="high",
        reasoning="Filter by technician name"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="what's assigned to installer Mike",
        conversation_summary="",
        intent="scheduling",
        action="list_projects",
        confidence="high",
        reasoning="Installer = technician filter"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="show jobs for tech ID 12345",
        conversation_summary="",
        intent="scheduling",
        action="list_projects",
        confidence="high",
        reasoning="Filter by technician ID"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="who is the technician for project 9000489",
        conversation_summary="",
        intent="information",
        action="get_project_details",
        confidence="high",
        reasoning="Asking for technician info"
    ).with_inputs("message", "conversation_summary"),

    # =========================================================================
    # NOTES
    # =========================================================================
    dspy.Example(
        message="show notes for project 9000489",
        conversation_summary="",
        intent="scheduling",
        action="list_notes",
        confidence="high",
        reasoning="Notes listing request"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="add a note to project 9000407",
        conversation_summary="",
        intent="scheduling",
        action="add_note",
        confidence="high",
        reasoning="Add note request"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="put a comment on the decking project",
        conversation_summary="",
        intent="scheduling",
        action="add_note",
        confidence="high",
        reasoning="Comment = note"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="what notes are on my kitchen project",
        conversation_summary="",
        intent="scheduling",
        action="list_notes",
        confidence="high",
        reasoning="Notes query by category"
    ).with_inputs("message", "conversation_summary"),

    # =========================================================================
    # COMPOUND/COMPLEX QUERIES
    # =========================================================================
    dspy.Example(
        message="show me my scheduled kitchen projects for next month",
        conversation_summary="",
        intent="scheduling",
        action="list_projects",
        confidence="high",
        reasoning="Multiple filters: scheduled + category + date"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="what roofing jobs are ready to schedule this week",
        conversation_summary="",
        intent="scheduling",
        action="list_projects",
        confidence="high",
        reasoning="Category + status + date filter"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="show me Peter's completed projects from January",
        conversation_summary="",
        intent="scheduling",
        action="list_projects",
        confidence="high",
        reasoning="Technician + status + date filter"
    ).with_inputs("message", "conversation_summary"),

    # =========================================================================
    # TYPOS AND INFORMAL LANGUAGE
    # =========================================================================
    dspy.Example(
        message="shwo me my projects",
        conversation_summary="",
        intent="scheduling",
        action="list_projects",
        confidence="high",
        reasoning="Typo for 'show me my projects'"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="whats on the schedule",
        conversation_summary="",
        intent="scheduling",
        action="list_projects",
        confidence="high",
        reasoning="Informal schedule query"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="gimme project details 9000489",
        conversation_summary="",
        intent="information",
        action="get_project_details",
        confidence="high",
        reasoning="Informal project details request"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="wanna schedule my deck",
        conversation_summary="",
        intent="scheduling",
        action="get_available_dates",
        confidence="high",
        reasoning="Informal scheduling request"
    ).with_inputs("message", "conversation_summary"),

    # =========================================================================
    # FOLLOW-UP / CONTEXTUAL
    # =========================================================================
    dspy.Example(
        message="what about the other one",
        conversation_summary="Assistant showed details for project 9000489, user has 2 projects",
        intent="information",
        action="get_project_details",
        confidence="high",
        reasoning="Follow-up asking about another project"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="schedule that one",
        conversation_summary="Assistant showed project 9000489 details",
        intent="scheduling",
        action="get_available_dates",
        confidence="high",
        reasoning="Scheduling referenced project"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="same project, different date",
        conversation_summary="User just scheduled project for Jan 6",
        intent="scheduling",
        action="reschedule_appointment",
        confidence="high",
        reasoning="Wants to change date for same project"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="actually, let's do the flooring first",
        conversation_summary="User was scheduling kitchen project",
        intent="scheduling",
        action="get_available_dates",
        confidence="high",
        reasoning="Switching to different project"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="go back",
        conversation_summary="User viewing time slots",
        intent="scheduling",
        action="get_available_dates",
        confidence="high",
        reasoning="Navigation back to previous step"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="different date please",
        conversation_summary="User viewing time slots for Jan 6",
        intent="scheduling",
        action="get_available_dates",
        confidence="high",
        reasoning="Wants to see different dates"
    ).with_inputs("message", "conversation_summary"),

    # =========================================================================
    # NEGATIVE/DECLINE RESPONSES
    # =========================================================================
    dspy.Example(
        message="no",
        conversation_summary="Assistant asked: Would you like to confirm this appointment?",
        intent="chitchat",
        action="general",
        confidence="high",
        reasoning="Declining offered action"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="not that one",
        conversation_summary="Assistant suggested time slot",
        intent="scheduling",
        action="get_time_slots",
        confidence="high",
        reasoning="Rejecting suggestion, wants more options"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="none of those work",
        conversation_summary="Assistant showed available dates",
        intent="scheduling",
        action="get_available_dates",
        confidence="high",
        reasoning="Needs different options"
    ).with_inputs("message", "conversation_summary"),

    # =========================================================================
    # WEATHER - MORE VARIATIONS
    # =========================================================================
    dspy.Example(
        message="will it rain on that day",
        conversation_summary="Scheduling outdoor project for Jan 6",
        intent="information",
        action="get_weather",
        confidence="high",
        reasoning="Rain query for scheduled date"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="what's the forecast",
        conversation_summary="User viewing dates for Minneapolis project",
        intent="information",
        action="get_weather",
        confidence="high",
        reasoning="Forecast = weather query"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="is it going to snow",
        conversation_summary="Scheduling roofing project",
        intent="information",
        action="get_weather",
        confidence="high",
        reasoning="Snow query for outdoor work"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="temperature for Jan 6",
        conversation_summary="",
        intent="information",
        action="get_weather",
        confidence="high",
        reasoning="Temperature = weather query"
    ).with_inputs("message", "conversation_summary"),

    # =========================================================================
    # CHITCHAT - EXTENDED
    # =========================================================================
    dspy.Example(
        message="good morning",
        conversation_summary="",
        intent="chitchat",
        action="greet",
        confidence="high",
        reasoning="Morning greeting"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="hey there",
        conversation_summary="",
        intent="chitchat",
        action="greet",
        confidence="high",
        reasoning="Casual greeting"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="I need some help",
        conversation_summary="",
        intent="chitchat",
        action="help",
        confidence="high",
        reasoning="Help request"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="how does this work",
        conversation_summary="",
        intent="chitchat",
        action="help",
        confidence="high",
        reasoning="Asking about system usage"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="thanks for your help",
        conversation_summary="",
        intent="chitchat",
        action="general",
        confidence="high",
        reasoning="Gratitude expression"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="goodbye",
        conversation_summary="",
        intent="chitchat",
        action="general",
        confidence="high",
        reasoning="Farewell"
    ).with_inputs("message", "conversation_summary"),

    dspy.Example(
        message="see you later",
        conversation_summary="",
        intent="chitchat",
        action="general",
        confidence="high",
        reasoning="Casual farewell"
    ).with_inputs("message", "conversation_summary"),
]


# =============================================================================
# ENTITY EXTRACTION EXAMPLES
# =============================================================================

ENTITY_EXAMPLES = [
    # Standard project ID formats
    dspy.Example(
        message="schedule project 9000489",
        action="get_available_dates",
        available_projects='[{"id": "9000489", "category": "Decking", "status": "Ready To Schedule"}]',
        workflow_context="{}",
        project_id="9000489",
        category="Decking",
        date="",
        time="",
        location="",
        status_filter=""
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    # AI-PRO format project IDs
    dspy.Example(
        message="Show me the details for project AI-PRO-1000010",
        action="get_project_details",
        available_projects="[]",
        workflow_context="{}",
        project_id="AI-PRO-1000010",
        category="",
        date="",
        time="",
        location="",
        status_filter=""
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    # Complex project ID format
    dspy.Example(
        message="Show me the available time slots on 31st December for project number 12125_09PF05VD_1765791831881",
        action="get_time_slots",
        available_projects="[]",
        workflow_context="{}",
        project_id="12125_09PF05VD_1765791831881",
        category="",
        date="2025-12-31",
        time="",
        location="",
        status_filter=""
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    # Underscore project ID
    dspy.Example(
        message="Retrieve the installation address and technician information for project number 524523452_1",
        action="get_project_details",
        available_projects="[]",
        workflow_context="{}",
        project_id="524523452_1",
        category="",
        date="",
        time="",
        location="",
        status_filter=""
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    # Technician filter
    dspy.Example(
        message="Show me all the projects assigned to technician Peter PF",
        action="list_projects",
        available_projects="[]",
        workflow_context="{}",
        project_id="",
        category="",
        date="",
        time="",
        location="",
        status_filter="",
        technician_name="Peter PF"
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    # Date with month name
    dspy.Example(
        message="show me the available dates in January for project AI-PRO-1000010",
        action="get_available_dates",
        available_projects="[]",
        workflow_context="{}",
        project_id="AI-PRO-1000010",
        category="",
        date="January",
        time="",
        location="",
        status_filter=""
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    # Relative date - today
    dspy.Example(
        message="i want to schedule project no 675656565 please suggest available today slots",
        action="get_time_slots",
        available_projects="[]",
        workflow_context="{}",
        project_id="675656565",
        category="",
        date="today",
        time="",
        location="",
        status_filter=""
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    # Relative date - tomorrow
    dspy.Example(
        message="I want to schedule project 675656565. Please show me the available time slots for tomorrow / day after tomorrow",
        action="get_time_slots",
        available_projects="[]",
        workflow_context="{}",
        project_id="675656565",
        category="",
        date="tomorrow",
        time="",
        location="",
        status_filter=""
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    # Relative date - next week
    dspy.Example(
        message="show me next week dates",
        action="get_available_dates",
        available_projects="[]",
        workflow_context='{"project_id": "9000489"}',
        project_id="9000489",
        category="",
        date="next week",
        time="",
        location="",
        status_filter=""
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    # Relative date - next month
    dspy.Example(
        message="show me next month dates",
        action="get_available_dates",
        available_projects="[]",
        workflow_context='{"project_id": "9000489"}',
        project_id="9000489",
        category="",
        date="next month",
        time="",
        location="",
        status_filter=""
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    # Status filter - scheduled
    dspy.Example(
        message="Show me all the projects that are scheduled for january",
        action="list_projects",
        available_projects="[]",
        workflow_context="{}",
        project_id="",
        category="",
        date="January",
        time="",
        location="",
        status_filter="scheduled"
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    # Status filter - ready to schedule
    dspy.Example(
        message="Show me all ready-to-schedule projects with project number",
        action="list_projects",
        available_projects="[]",
        workflow_context="{}",
        project_id="",
        category="",
        date="",
        time="",
        location="",
        status_filter="ready to schedule"
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    # Date selection
    dspy.Example(
        message="January 6th",
        action="get_time_slots",
        available_projects="[]",
        workflow_context='{"project_id": "9000489", "city": "Minneapolis", "state": "MN"}',
        project_id="9000489",
        category="",
        date="2026-01-06",
        time="",
        location="",
        status_filter=""
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    # Time selection
    dspy.Example(
        message="8 AM",
        action="confirm_appointment",
        available_projects="[]",
        workflow_context='{"project_id": "9000489", "date": "2026-01-06"}',
        project_id="9000489",
        category="",
        date="2026-01-06",
        time="8:00 AM",
        location="",
        status_filter=""
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    # Weather with location
    dspy.Example(
        message="what's the weather in Chicago",
        action="get_weather",
        available_projects="[]",
        workflow_context="{}",
        project_id="",
        category="",
        date="",
        time="",
        location="Chicago, IL",
        status_filter=""
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    # Address-based lookup
    dspy.Example(
        message="for this installation address 124 SW Barber Glenn Drive Fort White-32038 give me the project no",
        action="get_project_details",
        available_projects="[]",
        workflow_context="{}",
        project_id="",
        category="",
        date="",
        time="",
        location="124 SW Barber Glenn Drive, Fort White, FL 32038",
        status_filter=""
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    # =========================================================================
    # MORE PROJECT ID FORMATS
    # =========================================================================
    dspy.Example(
        message="details for PF-2024-001234",
        action="get_project_details",
        available_projects="[]",
        workflow_context="{}",
        project_id="PF-2024-001234",
        category="",
        date="",
        time="",
        location="",
        status_filter=""
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    dspy.Example(
        message="schedule project 21083_09PF05VD",
        action="get_available_dates",
        available_projects="[]",
        workflow_context="{}",
        project_id="21083_09PF05VD",
        category="",
        date="",
        time="",
        location="",
        status_filter=""
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    dspy.Example(
        message="what's the status of 9000407_1",
        action="get_project_details",
        available_projects="[]",
        workflow_context="{}",
        project_id="9000407_1",
        category="",
        date="",
        time="",
        location="",
        status_filter=""
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    # =========================================================================
    # CATEGORY EXTRACTION
    # =========================================================================
    dspy.Example(
        message="show me my kitchen projects",
        action="list_projects",
        available_projects="[]",
        workflow_context="{}",
        project_id="",
        category="Kitchen",
        date="",
        time="",
        location="",
        status_filter=""
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    dspy.Example(
        message="list bathroom installations",
        action="list_projects",
        available_projects="[]",
        workflow_context="{}",
        project_id="",
        category="Bathroom",
        date="",
        time="",
        location="",
        status_filter=""
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    dspy.Example(
        message="flooring jobs",
        action="list_projects",
        available_projects="[]",
        workflow_context="{}",
        project_id="",
        category="Flooring",
        date="",
        time="",
        location="",
        status_filter=""
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    dspy.Example(
        message="schedule my roofing project",
        action="get_available_dates",
        available_projects='[{"id": "9000500", "category": "Roofing", "status": "Ready To Schedule"}]',
        workflow_context="{}",
        project_id="9000500",
        category="Roofing",
        date="",
        time="",
        location="",
        status_filter=""
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    dspy.Example(
        message="window installations ready to schedule",
        action="list_projects",
        available_projects="[]",
        workflow_context="{}",
        project_id="",
        category="Windows",
        date="",
        time="",
        location="",
        status_filter="ready to schedule"
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    # =========================================================================
    # DATE EXTRACTION - RELATIVE
    # =========================================================================
    dspy.Example(
        message="show me slots for day after tomorrow",
        action="get_time_slots",
        available_projects="[]",
        workflow_context='{"project_id": "9000489"}',
        project_id="9000489",
        category="",
        date="day after tomorrow",
        time="",
        location="",
        status_filter=""
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    dspy.Example(
        message="end of January dates",
        action="get_available_dates",
        available_projects="[]",
        workflow_context='{"project_id": "9000489"}',
        project_id="9000489",
        category="",
        date="end of January",
        time="",
        location="",
        status_filter=""
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    dspy.Example(
        message="first week of February",
        action="get_available_dates",
        available_projects="[]",
        workflow_context='{"project_id": "9000489"}',
        project_id="9000489",
        category="",
        date="first week of February",
        time="",
        location="",
        status_filter=""
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    dspy.Example(
        message="this Friday",
        action="get_time_slots",
        available_projects="[]",
        workflow_context='{"project_id": "9000489"}',
        project_id="9000489",
        category="",
        date="this Friday",
        time="",
        location="",
        status_filter=""
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    dspy.Example(
        message="next Monday slots",
        action="get_time_slots",
        available_projects="[]",
        workflow_context='{"project_id": "9000489"}',
        project_id="9000489",
        category="",
        date="next Monday",
        time="",
        location="",
        status_filter=""
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    # =========================================================================
    # DATE EXTRACTION - SPECIFIC
    # =========================================================================
    dspy.Example(
        message="slots for February 14",
        action="get_time_slots",
        available_projects="[]",
        workflow_context='{"project_id": "9000489"}',
        project_id="9000489",
        category="",
        date="2026-02-14",
        time="",
        location="",
        status_filter=""
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    dspy.Example(
        message="March 1st availability",
        action="get_time_slots",
        available_projects="[]",
        workflow_context='{"project_id": "9000489"}',
        project_id="9000489",
        category="",
        date="2026-03-01",
        time="",
        location="",
        status_filter=""
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    dspy.Example(
        message="the 25th",
        action="get_time_slots",
        available_projects="[]",
        workflow_context='{"project_id": "9000489", "date_context": "viewing January dates"}',
        project_id="9000489",
        category="",
        date="2026-01-25",
        time="",
        location="",
        status_filter=""
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    # =========================================================================
    # TIME EXTRACTION
    # =========================================================================
    dspy.Example(
        message="10:30 AM",
        action="confirm_appointment",
        available_projects="[]",
        workflow_context='{"project_id": "9000489", "date": "2026-01-06"}',
        project_id="9000489",
        category="",
        date="2026-01-06",
        time="10:30 AM",
        location="",
        status_filter=""
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    dspy.Example(
        message="2 PM please",
        action="confirm_appointment",
        available_projects="[]",
        workflow_context='{"project_id": "9000489", "date": "2026-01-06"}',
        project_id="9000489",
        category="",
        date="2026-01-06",
        time="2:00 PM",
        location="",
        status_filter=""
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    dspy.Example(
        message="afternoon slot",
        action="get_time_slots",
        available_projects="[]",
        workflow_context='{"project_id": "9000489", "date": "2026-01-06"}',
        project_id="9000489",
        category="",
        date="2026-01-06",
        time="afternoon",
        location="",
        status_filter=""
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    dspy.Example(
        message="morning appointment",
        action="get_time_slots",
        available_projects="[]",
        workflow_context='{"project_id": "9000489", "date": "2026-01-06"}',
        project_id="9000489",
        category="",
        date="2026-01-06",
        time="morning",
        location="",
        status_filter=""
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    # =========================================================================
    # STATUS FILTER VARIATIONS
    # =========================================================================
    dspy.Example(
        message="completed projects",
        action="list_projects",
        available_projects="[]",
        workflow_context="{}",
        project_id="",
        category="",
        date="",
        time="",
        location="",
        status_filter="completed"
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    dspy.Example(
        message="cancelled orders",
        action="list_projects",
        available_projects="[]",
        workflow_context="{}",
        project_id="",
        category="",
        date="",
        time="",
        location="",
        status_filter="cancelled"
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    dspy.Example(
        message="jobs in progress",
        action="list_projects",
        available_projects="[]",
        workflow_context="{}",
        project_id="",
        category="",
        date="",
        time="",
        location="",
        status_filter="in progress"
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    dspy.Example(
        message="pending installations",
        action="list_projects",
        available_projects="[]",
        workflow_context="{}",
        project_id="",
        category="",
        date="",
        time="",
        location="",
        status_filter="pending"
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    dspy.Example(
        message="new projects",
        action="list_projects",
        available_projects="[]",
        workflow_context="{}",
        project_id="",
        category="",
        date="",
        time="",
        location="",
        status_filter="new"
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    dspy.Example(
        message="projects on the books",
        action="list_projects",
        available_projects="[]",
        workflow_context="{}",
        project_id="",
        category="",
        date="",
        time="",
        location="",
        status_filter="scheduled"
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    # =========================================================================
    # TECHNICIAN NAME EXTRACTION
    # =========================================================================
    dspy.Example(
        message="show John Smith's projects",
        action="list_projects",
        available_projects="[]",
        workflow_context="{}",
        project_id="",
        category="",
        date="",
        time="",
        location="",
        status_filter="",
        technician_name="John Smith"
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    dspy.Example(
        message="projects assigned to installer Mike Johnson",
        action="list_projects",
        available_projects="[]",
        workflow_context="{}",
        project_id="",
        category="",
        date="",
        time="",
        location="",
        status_filter="",
        technician_name="Mike Johnson"
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    dspy.Example(
        message="what does technician Sarah have scheduled",
        action="list_projects",
        available_projects="[]",
        workflow_context="{}",
        project_id="",
        category="",
        date="",
        time="",
        location="",
        status_filter="scheduled",
        technician_name="Sarah"
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    # =========================================================================
    # COMPOUND ENTITY EXTRACTION
    # =========================================================================
    dspy.Example(
        message="scheduled kitchen projects for next week",
        action="list_projects",
        available_projects="[]",
        workflow_context="{}",
        project_id="",
        category="Kitchen",
        date="next week",
        time="",
        location="",
        status_filter="scheduled"
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    dspy.Example(
        message="Peter's completed roofing jobs",
        action="list_projects",
        available_projects="[]",
        workflow_context="{}",
        project_id="",
        category="Roofing",
        date="",
        time="",
        location="",
        status_filter="completed",
        technician_name="Peter"
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    dspy.Example(
        message="flooring installations ready to schedule this month",
        action="list_projects",
        available_projects="[]",
        workflow_context="{}",
        project_id="",
        category="Flooring",
        date="this month",
        time="",
        location="",
        status_filter="ready to schedule"
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    # =========================================================================
    # CONTEXT-BASED ENTITY EXTRACTION
    # =========================================================================
    dspy.Example(
        message="schedule that one",
        action="get_available_dates",
        available_projects='[{"id": "9000489", "category": "Decking"}]',
        workflow_context='{"last_mentioned_project": "9000489"}',
        project_id="9000489",
        category="Decking",
        date="",
        time="",
        location="",
        status_filter=""
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    dspy.Example(
        message="the second one",
        action="get_project_details",
        available_projects='[{"id": "9000489", "category": "Decking"}, {"id": "9000407", "category": "Kitchen"}]',
        workflow_context="{}",
        project_id="9000407",
        category="Kitchen",
        date="",
        time="",
        location="",
        status_filter=""
    ).with_inputs("message", "action", "available_projects", "workflow_context"),

    dspy.Example(
        message="first option",
        action="confirm_appointment",
        available_projects="[]",
        workflow_context='{"project_id": "9000489", "date": "2026-01-06", "available_slots": ["8:00 AM", "10:00 AM", "1:00 PM"]}',
        project_id="9000489",
        category="",
        date="2026-01-06",
        time="8:00 AM",
        location="",
        status_filter=""
    ).with_inputs("message", "action", "available_projects", "workflow_context"),
]


# =============================================================================
# WEATHER CONTEXT EXAMPLES
# =============================================================================

WEATHER_CONTEXT_EXAMPLES = [
    dspy.Example(
        message="what's the weather like",
        workflow_context='{"project_id": "9000489", "city": "Minneapolis", "state": "MN", "date": "2026-01-06", "category": "Decking"}',
        conversation_summary="User viewing time slots for Decking project on Jan 6",
        location="Minneapolis, MN",
        target_date="2026-01-06",
        reasoning="Using city/state and date from current scheduling workflow"
    ).with_inputs("message", "workflow_context", "conversation_summary"),

    dspy.Example(
        message="how is the weather for the day",
        workflow_context='{"project_id": "9000407", "city": "Chicago", "state": "IL", "date": "2026-01-10"}',
        conversation_summary="",
        location="Chicago, IL",
        target_date="2026-01-10",
        reasoning="Extracted location and date from workflow context"
    ).with_inputs("message", "workflow_context", "conversation_summary"),

    dspy.Example(
        message="how is the weather for given date",
        workflow_context='{"project_id": "9000489", "city": "Minneapolis", "state": "MN", "date": "2026-01-05"}',
        conversation_summary="User viewing time slots for Jan 5",
        location="Minneapolis, MN",
        target_date="2026-01-05",
        reasoning="Using date from workflow context (given date)"
    ).with_inputs("message", "workflow_context", "conversation_summary"),

    dspy.Example(
        message="how is the weather",
        workflow_context='{"project_id": "9000489", "city": "Minneapolis", "state": "MN", "category": "Decking"}',
        conversation_summary="User scheduling outdoor decking project",
        location="Minneapolis, MN",
        target_date="",
        reasoning="General weather query - using project location"
    ).with_inputs("message", "workflow_context", "conversation_summary"),

    dspy.Example(
        message="if there rain / summer / winter",
        workflow_context='{"project_id": "9000489", "city": "Minneapolis", "state": "MN", "date": "2026-01-06", "category": "Decking"}',
        conversation_summary="Scheduling outdoor decking project",
        location="Minneapolis, MN",
        target_date="2026-01-06",
        reasoning="Weather conditions query for outdoor project"
    ).with_inputs("message", "workflow_context", "conversation_summary"),

    dspy.Example(
        message="weather for my decking project",
        workflow_context='{"project_mapping": {"9000489": {"city": "Minneapolis", "state": "MN", "category": "Decking"}}}',
        conversation_summary="User has decking project #9000489",
        location="Minneapolis, MN",
        target_date="",
        reasoning="Found decking project in mapping, extracted location"
    ).with_inputs("message", "workflow_context", "conversation_summary"),
]


# =============================================================================
# ACTION GUARD EXAMPLES
# =============================================================================

GUARD_EXAMPLES = [
    # Should NOT correct - explicit schedule request
    dspy.Example(
        message="schedule my project",
        classified_action="get_available_dates",
        workflow_stage="none",
        previous_action="",
        final_action="get_available_dates",
        was_corrected=False,
        guard_reason=""
    ).with_inputs("message", "classified_action", "workflow_stage", "previous_action"),

    # Should correct - filtering after list
    dspy.Example(
        message="just the kitchen ones",
        classified_action="get_available_dates",
        workflow_stage="listing_projects",
        previous_action="list_projects",
        final_action="list_projects",
        was_corrected=True,
        guard_reason="'just X' pattern is filtering, not scheduling"
    ).with_inputs("message", "classified_action", "workflow_stage", "previous_action"),

    # Should correct - show me is viewing, not scheduling
    dspy.Example(
        message="show me the decking project",
        classified_action="get_available_dates",
        workflow_stage="listing_projects",
        previous_action="list_projects",
        final_action="get_project_details",
        was_corrected=True,
        guard_reason="'show me X' is viewing details, not scheduling"
    ).with_inputs("message", "classified_action", "workflow_stage", "previous_action"),

    # Should correct - date selection goes to time slots
    dspy.Example(
        message="January 6th",
        classified_action="get_available_dates",
        workflow_stage="awaiting_date_selection",
        previous_action="get_available_dates",
        final_action="get_time_slots",
        was_corrected=True,
        guard_reason="User selecting date from available dates - get time slots"
    ).with_inputs("message", "classified_action", "workflow_stage", "previous_action"),

    # Should correct - reschedule confirmation
    dspy.Example(
        message="yes",
        classified_action="general",
        workflow_stage="awaiting_reschedule_offer_confirmation",
        previous_action="reschedule_appointment",
        final_action="reschedule_appointment",
        was_corrected=True,
        guard_reason="User confirmed reschedule offer"
    ).with_inputs("message", "classified_action", "workflow_stage", "previous_action"),

    # Should correct - time selection goes to confirm
    dspy.Example(
        message="8 AM please",
        classified_action="get_time_slots",
        workflow_stage="awaiting_time_selection",
        previous_action="get_time_slots",
        final_action="confirm_appointment",
        was_corrected=True,
        guard_reason="User selecting time slot - confirm appointment"
    ).with_inputs("message", "classified_action", "workflow_stage", "previous_action"),

    # Should NOT correct - explicit details request
    dspy.Example(
        message="Show me the status of project 675656565",
        classified_action="get_project_details",
        workflow_stage="none",
        previous_action="",
        final_action="get_project_details",
        was_corrected=False,
        guard_reason=""
    ).with_inputs("message", "classified_action", "workflow_stage", "previous_action"),
]


# =============================================================================
# DATE INTERPRETER EXAMPLES
# =============================================================================
# Convert natural language date expressions to specific date ranges

DATE_INTERPRETER_EXAMPLES = [
    # Relative week expressions
    dspy.Example(
        phrase="next week",
        current_date="2026-01-03",
        start_date="2026-01-05",
        end_date="2026-01-11",
        interpretation="The week starting Monday Jan 5 through Sunday Jan 11"
    ).with_inputs("phrase", "current_date"),

    dspy.Example(
        phrase="the week after the current week",
        current_date="2026-01-03",
        start_date="2026-01-05",
        end_date="2026-01-11",
        interpretation="Same as next week - the following week"
    ).with_inputs("phrase", "current_date"),

    dspy.Example(
        phrase="this week",
        current_date="2026-01-03",
        start_date="2026-01-03",
        end_date="2026-01-05",
        interpretation="Remaining days of current week (Fri-Sun)"
    ).with_inputs("phrase", "current_date"),

    dspy.Example(
        phrase="next month",
        current_date="2026-01-15",
        start_date="2026-02-01",
        end_date="2026-02-28",
        interpretation="The entire month of February"
    ).with_inputs("phrase", "current_date"),

    dspy.Example(
        phrase="end of January",
        current_date="2026-01-10",
        start_date="2026-01-25",
        end_date="2026-01-31",
        interpretation="Last week of January"
    ).with_inputs("phrase", "current_date"),

    dspy.Example(
        phrase="beginning of February",
        current_date="2026-01-15",
        start_date="2026-02-01",
        end_date="2026-02-07",
        interpretation="First week of February"
    ).with_inputs("phrase", "current_date"),

    dspy.Example(
        phrase="first week of February",
        current_date="2026-01-20",
        start_date="2026-02-02",
        end_date="2026-02-08",
        interpretation="First full week of February (Mon-Sun)"
    ).with_inputs("phrase", "current_date"),

    dspy.Example(
        phrase="last week of January",
        current_date="2026-01-10",
        start_date="2026-01-26",
        end_date="2026-01-31",
        interpretation="Final week of January"
    ).with_inputs("phrase", "current_date"),

    dspy.Example(
        phrase="2nd week of March",
        current_date="2026-02-15",
        start_date="2026-03-09",
        end_date="2026-03-15",
        interpretation="Second full week of March"
    ).with_inputs("phrase", "current_date"),

    # Day-specific expressions
    dspy.Example(
        phrase="tomorrow",
        current_date="2026-01-03",
        start_date="2026-01-04",
        end_date="2026-01-04",
        interpretation="Saturday January 4"
    ).with_inputs("phrase", "current_date"),

    dspy.Example(
        phrase="day after tomorrow",
        current_date="2026-01-03",
        start_date="2026-01-05",
        end_date="2026-01-05",
        interpretation="Sunday January 5"
    ).with_inputs("phrase", "current_date"),

    dspy.Example(
        phrase="this Friday",
        current_date="2026-01-06",
        start_date="2026-01-10",
        end_date="2026-01-10",
        interpretation="Friday of current week"
    ).with_inputs("phrase", "current_date"),

    dspy.Example(
        phrase="next Monday",
        current_date="2026-01-03",
        start_date="2026-01-05",
        end_date="2026-01-05",
        interpretation="Monday of the coming week"
    ).with_inputs("phrase", "current_date"),

    dspy.Example(
        phrase="next Tuesday",
        current_date="2026-01-03",
        start_date="2026-01-07",
        end_date="2026-01-07",
        interpretation="Tuesday January 7"
    ).with_inputs("phrase", "current_date"),

    # Month expressions
    dspy.Example(
        phrase="sometime in February",
        current_date="2026-01-15",
        start_date="2026-02-01",
        end_date="2026-02-28",
        interpretation="Any date in February - show full month"
    ).with_inputs("phrase", "current_date"),

    dspy.Example(
        phrase="late March",
        current_date="2026-02-01",
        start_date="2026-03-20",
        end_date="2026-03-31",
        interpretation="Last 10-12 days of March"
    ).with_inputs("phrase", "current_date"),

    dspy.Example(
        phrase="early April",
        current_date="2026-03-15",
        start_date="2026-04-01",
        end_date="2026-04-10",
        interpretation="First 10 days of April"
    ).with_inputs("phrase", "current_date"),

    dspy.Example(
        phrase="mid February",
        current_date="2026-01-20",
        start_date="2026-02-10",
        end_date="2026-02-20",
        interpretation="Middle of February"
    ).with_inputs("phrase", "current_date"),

    # Specific dates
    dspy.Example(
        phrase="January 15th",
        current_date="2026-01-03",
        start_date="2026-01-15",
        end_date="2026-01-15",
        interpretation="Specific date: January 15, 2026"
    ).with_inputs("phrase", "current_date"),

    dspy.Example(
        phrase="the 25th",
        current_date="2026-01-10",
        start_date="2026-01-25",
        end_date="2026-01-25",
        interpretation="25th of current month (January)"
    ).with_inputs("phrase", "current_date"),

    dspy.Example(
        phrase="February 14",
        current_date="2026-01-20",
        start_date="2026-02-14",
        end_date="2026-02-14",
        interpretation="Valentine's Day - February 14"
    ).with_inputs("phrase", "current_date"),

    # ==========================================================================
    # DATE RANGE EXPRESSIONS - Shared month format
    # ==========================================================================
    dspy.Example(
        phrase="between 12 and 20 January",
        current_date="2026-01-05",
        start_date="2026-01-12",
        end_date="2026-01-20",
        interpretation="Date range within January: 12th to 20th"
    ).with_inputs("phrase", "current_date"),

    dspy.Example(
        phrase="between 12th and 20th January",
        current_date="2026-01-05",
        start_date="2026-01-12",
        end_date="2026-01-20",
        interpretation="Date range within January with ordinals"
    ).with_inputs("phrase", "current_date"),

    dspy.Example(
        phrase="from 5th to 15th February",
        current_date="2026-01-15",
        start_date="2026-02-05",
        end_date="2026-02-15",
        interpretation="Date range within February: 5th to 15th"
    ).with_inputs("phrase", "current_date"),

    dspy.Example(
        phrase="between 1st and 10th March",
        current_date="2026-02-01",
        start_date="2026-03-01",
        end_date="2026-03-10",
        interpretation="First 10 days of March"
    ).with_inputs("phrase", "current_date"),

    # ==========================================================================
    # DATE RANGE EXPRESSIONS - Cross-month ranges
    # ==========================================================================
    dspy.Example(
        phrase="between 20 January and 8 March",
        current_date="2026-01-05",
        start_date="2026-01-20",
        end_date="2026-03-08",
        interpretation="Cross-month range from late January to early March"
    ).with_inputs("phrase", "current_date"),

    dspy.Example(
        phrase="from January 25 to February 10",
        current_date="2026-01-10",
        start_date="2026-01-25",
        end_date="2026-02-10",
        interpretation="Cross-month range spanning January and February"
    ).with_inputs("phrase", "current_date"),

    dspy.Example(
        phrase="between Feb 15 and March 20",
        current_date="2026-01-20",
        start_date="2026-02-15",
        end_date="2026-03-20",
        interpretation="Cross-month range from mid-February to mid-March"
    ).with_inputs("phrase", "current_date"),

    # ==========================================================================
    # WEEK EXPRESSIONS - "for" instead of "of"
    # ==========================================================================
    dspy.Example(
        phrase="3rd week for feb",
        current_date="2026-01-15",
        start_date="2026-02-16",
        end_date="2026-02-22",
        interpretation="Third week of February (for = of)"
    ).with_inputs("phrase", "current_date"),

    dspy.Example(
        phrase="2nd week for January",
        current_date="2025-12-20",
        start_date="2026-01-06",
        end_date="2026-01-12",
        interpretation="Second week of January (for = of)"
    ).with_inputs("phrase", "current_date"),

    dspy.Example(
        phrase="4th week for march",
        current_date="2026-02-15",
        start_date="2026-03-23",
        end_date="2026-03-29",
        interpretation="Fourth week of March (for = of)"
    ).with_inputs("phrase", "current_date"),

    dspy.Example(
        phrase="1st week for April",
        current_date="2026-03-01",
        start_date="2026-04-06",
        end_date="2026-04-12",
        interpretation="First full week of April (for = of)"
    ).with_inputs("phrase", "current_date"),

    # ==========================================================================
    # ALTERNATIVE WEEK PHRASINGS
    # ==========================================================================
    dspy.Example(
        phrase="week after current week",
        current_date="2026-01-05",
        start_date="2026-01-12",
        end_date="2026-01-18",
        interpretation="Same as next week - the week after this one"
    ).with_inputs("phrase", "current_date"),

    dspy.Example(
        phrase="week after this week",
        current_date="2026-01-07",
        start_date="2026-01-12",
        end_date="2026-01-18",
        interpretation="Next week starting Monday"
    ).with_inputs("phrase", "current_date"),

    dspy.Example(
        phrase="the following week",
        current_date="2026-01-03",
        start_date="2026-01-05",
        end_date="2026-01-11",
        interpretation="Next week - the week that follows"
    ).with_inputs("phrase", "current_date"),

    dspy.Example(
        phrase="coming week",
        current_date="2026-01-03",
        start_date="2026-01-05",
        end_date="2026-01-11",
        interpretation="The upcoming week"
    ).with_inputs("phrase", "current_date"),

    # ==========================================================================
    # ORDINAL WEEK IN MONTH - Alternative phrasings
    # ==========================================================================
    dspy.Example(
        phrase="3rd week available dates for feb",
        current_date="2026-01-15",
        start_date="2026-02-16",
        end_date="2026-02-22",
        interpretation="Third week of February"
    ).with_inputs("phrase", "current_date"),

    dspy.Example(
        phrase="show me 2nd week in January",
        current_date="2025-12-20",
        start_date="2026-01-06",
        end_date="2026-01-12",
        interpretation="Second week of January"
    ).with_inputs("phrase", "current_date"),

    dspy.Example(
        phrase="4th week dates for February",
        current_date="2026-01-20",
        start_date="2026-02-23",
        end_date="2026-02-28",
        interpretation="Fourth week of February (last week)"
    ).with_inputs("phrase", "current_date"),
]


# =============================================================================
# CONTEXT RESOLVER EXAMPLES
# =============================================================================
# Resolve pronouns, references, and ambiguous entities

CONTEXT_RESOLVER_EXAMPLES = [
    # Pronoun resolution - "it"
    dspy.Example(
        message="reschedule it",
        conversation_history="User discussed project 9000489 (Decking). Assistant showed details.",
        resolved_message="reschedule project 9000489",
        resolved_entities='{"project_id": "9000489", "category": "Decking"}',
        resolution_type="pronoun",
        confidence="high"
    ).with_inputs("message", "conversation_history"),

    dspy.Example(
        message="schedule it for next week",
        conversation_history="User has Kitchen project #9000407. Just viewed details.",
        resolved_message="schedule project 9000407 for next week",
        resolved_entities='{"project_id": "9000407", "category": "Kitchen"}',
        resolution_type="pronoun",
        confidence="high"
    ).with_inputs("message", "conversation_history"),

    dspy.Example(
        message="cancel it",
        conversation_history="User scheduled Roofing project #9000500 for Jan 10.",
        resolved_message="cancel project 9000500",
        resolved_entities='{"project_id": "9000500", "category": "Roofing"}',
        resolution_type="pronoun",
        confidence="high"
    ).with_inputs("message", "conversation_history"),

    # Demonstrative resolution - "that one", "this one"
    dspy.Example(
        message="schedule that one",
        conversation_history="Assistant listed 3 projects: Decking #9000489, Kitchen #9000407, Flooring #9000510. User asked about the Decking project.",
        resolved_message="schedule project 9000489",
        resolved_entities='{"project_id": "9000489", "category": "Decking"}',
        resolution_type="demonstrative",
        confidence="high"
    ).with_inputs("message", "conversation_history"),

    dspy.Example(
        message="the first one",
        conversation_history="Assistant showed 3 time slots: 8 AM, 10 AM, 1 PM",
        resolved_message="8 AM",
        resolved_entities='{"time": "8:00 AM"}',
        resolution_type="ordinal",
        confidence="high"
    ).with_inputs("message", "conversation_history"),

    dspy.Example(
        message="the second option",
        conversation_history="Available dates: Jan 6, Jan 7, Jan 8",
        resolved_message="January 7",
        resolved_entities='{"date": "2026-01-07"}',
        resolution_type="ordinal",
        confidence="high"
    ).with_inputs("message", "conversation_history"),

    dspy.Example(
        message="what about the other one",
        conversation_history="User has 2 projects: Decking #9000489 and Kitchen #9000407. Just viewed Decking details.",
        resolved_message="show details for project 9000407",
        resolved_entities='{"project_id": "9000407", "category": "Kitchen"}',
        resolution_type="contrast",
        confidence="high"
    ).with_inputs("message", "conversation_history"),

    # Category-based resolution
    dspy.Example(
        message="schedule the decking",
        conversation_history="User has Decking project #9000489 in Minneapolis",
        resolved_message="schedule project 9000489",
        resolved_entities='{"project_id": "9000489", "category": "Decking", "city": "Minneapolis"}',
        resolution_type="category",
        confidence="high"
    ).with_inputs("message", "conversation_history"),

    dspy.Example(
        message="what's the status of my kitchen project",
        conversation_history="User has Kitchen project #9000407",
        resolved_message="show status of project 9000407",
        resolved_entities='{"project_id": "9000407", "category": "Kitchen"}',
        resolution_type="category",
        confidence="high"
    ).with_inputs("message", "conversation_history"),

    # Implicit project context
    dspy.Example(
        message="show me morning slots",
        conversation_history="User viewing time slots for project #9000489 on Jan 6",
        resolved_message="show morning slots for project 9000489 on January 6",
        resolved_entities='{"project_id": "9000489", "date": "2026-01-06", "time_preference": "morning"}',
        resolution_type="implicit",
        confidence="high"
    ).with_inputs("message", "conversation_history"),

    dspy.Example(
        message="different date please",
        conversation_history="User scheduling project #9000489, was viewing slots for Jan 6",
        resolved_message="show available dates for project 9000489",
        resolved_entities='{"project_id": "9000489"}',
        resolution_type="implicit",
        confidence="high"
    ).with_inputs("message", "conversation_history"),

    # Ambiguous - needs clarification
    dspy.Example(
        message="schedule it",
        conversation_history="User has 3 projects: Decking, Kitchen, Flooring. No specific project discussed.",
        resolved_message="schedule it",
        resolved_entities='{"ambiguous": true, "candidates": ["9000489", "9000407", "9000510"]}',
        resolution_type="ambiguous",
        confidence="low"
    ).with_inputs("message", "conversation_history"),

    dspy.Example(
        message="that one",
        conversation_history="Assistant listed 5 projects. No specific one mentioned.",
        resolved_message="that one",
        resolved_entities='{"ambiguous": true, "needs_clarification": true}',
        resolution_type="ambiguous",
        confidence="low"
    ).with_inputs("message", "conversation_history"),

    # Date context resolution
    dspy.Example(
        message="how's the weather",
        conversation_history="Scheduling project #9000489 in Minneapolis for Jan 6",
        resolved_message="weather for Minneapolis on January 6",
        resolved_entities='{"city": "Minneapolis", "state": "MN", "date": "2026-01-06"}',
        resolution_type="implicit",
        confidence="high"
    ).with_inputs("message", "conversation_history"),

    # Same project, different action
    dspy.Example(
        message="same project different date",
        conversation_history="User just scheduled project #9000489 for Jan 6 at 8 AM",
        resolved_message="reschedule project 9000489 to different date",
        resolved_entities='{"project_id": "9000489", "action": "reschedule"}',
        resolution_type="coreference",
        confidence="high"
    ).with_inputs("message", "conversation_history"),
]


# =============================================================================
# RESPONSE STYLE EXAMPLES
# =============================================================================
# Adapt response tone and format to channel (voice/sms/chat)

RESPONSE_STYLE_EXAMPLES = [
    # Voice channel - conversational, natural
    dspy.Example(
        raw_response="Available dates: January 6, January 7, January 8, January 9. Which date works for you?",
        channel="voice",
        context="Scheduling Decking project",
        styled_response="I found several dates available next week. Would January 6th, 7th, 8th, or 9th work best for your decking installation?",
        style_notes="Conversational tone, natural flow, no bullet points"
    ).with_inputs("raw_response", "channel", "context"),

    dspy.Example(
        raw_response="Project #9000489: Decking. Status: Ready To Schedule. Address: 123 Main St, Minneapolis, MN. Category: Decking.",
        channel="voice",
        context="User asked for project details",
        styled_response="Your decking project is ready to schedule! It's at 123 Main Street in Minneapolis. Would you like me to find some available dates?",
        style_notes="Friendly, suggests next action, omits project number in speech"
    ).with_inputs("raw_response", "channel", "context"),

    dspy.Example(
        raw_response="Appointment confirmed: Project 9000489, January 6, 2026 at 8:00 AM.",
        channel="voice",
        context="User just confirmed appointment",
        styled_response="Perfect! Your decking installation is all set for January 6th at 8 AM. Is there anything else I can help you with?",
        style_notes="Enthusiastic confirmation, offers further assistance"
    ).with_inputs("raw_response", "channel", "context"),

    dspy.Example(
        raw_response="Time slots for January 6: 8:00 AM, 8:30 AM, 9:00 AM, 10:00 AM, 1:00 PM, 2:00 PM",
        channel="voice",
        context="User viewing available time slots",
        styled_response="For January 6th, I have morning slots at 8, 8:30, 9, and 10 AM, or afternoon at 1 or 2 PM. What time works best?",
        style_notes="Group times logically, conversational"
    ).with_inputs("raw_response", "channel", "context"),

    # SMS channel - ultra concise, abbreviated
    dspy.Example(
        raw_response="Available dates: January 6, January 7, January 8, January 9. Which date works for you?",
        channel="sms",
        context="Scheduling Decking project",
        styled_response="Dates avail: Jan 6-9. Reply w/ date choice.",
        style_notes="Maximum brevity, abbreviations OK"
    ).with_inputs("raw_response", "channel", "context"),

    dspy.Example(
        raw_response="Project #9000489: Decking. Status: Ready To Schedule. Address: 123 Main St, Minneapolis, MN.",
        channel="sms",
        context="User asked for project details",
        styled_response="Decking #9000489\nStatus: Ready\n123 Main St, Minneapolis",
        style_notes="Minimal, structured, no fluff"
    ).with_inputs("raw_response", "channel", "context"),

    dspy.Example(
        raw_response="Appointment confirmed: Project 9000489, January 6, 2026 at 8:00 AM.",
        channel="sms",
        context="User just confirmed appointment",
        styled_response="Confirmed! Jan 6 @ 8AM. Reply HELP for assistance.",
        style_notes="Short confirmation with help option"
    ).with_inputs("raw_response", "channel", "context"),

    dspy.Example(
        raw_response="Time slots for January 6: 8:00 AM, 8:30 AM, 9:00 AM, 10:00 AM, 1:00 PM, 2:00 PM",
        channel="sms",
        context="User viewing available time slots",
        styled_response="Jan 6 slots: 8/8:30/9/10AM, 1/2PM. Reply w/ time.",
        style_notes="Compact time list"
    ).with_inputs("raw_response", "channel", "context"),

    # Chat channel - balanced, structured
    dspy.Example(
        raw_response="Available dates: January 6, January 7, January 8, January 9. Which date works for you?",
        channel="chat",
        context="Scheduling Decking project",
        styled_response="Here are the available dates for your Decking project:\n\n• **Jan 6** (Monday)\n• **Jan 7** (Tuesday)\n• **Jan 8** (Wednesday)\n• **Jan 9** (Thursday)\n\nWhich date works best for you?",
        style_notes="Markdown formatting, structured list, includes day names"
    ).with_inputs("raw_response", "channel", "context"),

    dspy.Example(
        raw_response="Project #9000489: Decking. Status: Ready To Schedule. Address: 123 Main St, Minneapolis, MN. Category: Decking.",
        channel="chat",
        context="User asked for project details",
        styled_response="**Project Details**\n\n| Field | Value |\n|-------|-------|\n| Project # | 9000489 |\n| Type | Decking |\n| Status | Ready To Schedule |\n| Address | 123 Main St, Minneapolis, MN |",
        style_notes="Markdown table for structured data"
    ).with_inputs("raw_response", "channel", "context"),

    dspy.Example(
        raw_response="Appointment confirmed: Project 9000489, January 6, 2026 at 8:00 AM.",
        channel="chat",
        context="User just confirmed appointment",
        styled_response="✅ **Appointment Confirmed!**\n\n• **Project:** Decking (#9000489)\n• **Date:** January 6, 2026\n• **Time:** 8:00 AM\n\nYou'll receive a confirmation email shortly.",
        style_notes="Emoji for visual feedback, structured confirmation"
    ).with_inputs("raw_response", "channel", "context"),

    # Error handling by channel
    dspy.Example(
        raw_response="Error: No available slots found for the requested date.",
        channel="voice",
        context="User trying to schedule",
        styled_response="I'm sorry, but there aren't any available slots on that date. Would you like me to check a different day?",
        style_notes="Apologetic, offers alternative"
    ).with_inputs("raw_response", "channel", "context"),

    dspy.Example(
        raw_response="Error: No available slots found for the requested date.",
        channel="sms",
        context="User trying to schedule",
        styled_response="No slots on that date. Try diff date?",
        style_notes="Brief, actionable"
    ).with_inputs("raw_response", "channel", "context"),

    dspy.Example(
        raw_response="Error: No available slots found for the requested date.",
        channel="chat",
        context="User trying to schedule",
        styled_response="⚠️ No available slots found for that date.\n\nWould you like to:\n• Try a different date\n• See the next available opening",
        style_notes="Clear options with emoji indicator"
    ).with_inputs("raw_response", "channel", "context"),
]


# =============================================================================
# SLOT RANKER EXAMPLES
# =============================================================================
# Rank time slots based on user preferences and context

SLOT_RANKER_EXAMPLES = [
    # Morning preference
    dspy.Example(
        available_slots='["8:00 AM", "8:30 AM", "10:00 AM", "1:00 PM", "2:00 PM", "3:00 PM"]',
        user_preference="morning",
        weather_info="",
        project_type="Indoor - Kitchen",
        ranked_slots='["8:00 AM", "8:30 AM", "10:00 AM", "1:00 PM", "2:00 PM", "3:00 PM"]',
        recommendation="8:00 AM",
        ranking_reason="User prefers morning - earliest morning slot recommended"
    ).with_inputs("available_slots", "user_preference", "weather_info", "project_type"),

    # Afternoon preference
    dspy.Example(
        available_slots='["8:00 AM", "9:00 AM", "1:00 PM", "2:00 PM", "3:30 PM"]',
        user_preference="afternoon",
        weather_info="",
        project_type="Flooring",
        ranked_slots='["1:00 PM", "2:00 PM", "3:30 PM", "8:00 AM", "9:00 AM"]',
        recommendation="1:00 PM",
        ranking_reason="User prefers afternoon - earliest afternoon slot recommended"
    ).with_inputs("available_slots", "user_preference", "weather_info", "project_type"),

    # Weather-aware for outdoor project
    dspy.Example(
        available_slots='["8:00 AM", "10:00 AM", "1:00 PM", "3:00 PM"]',
        user_preference="",
        weather_info="Rain expected in afternoon, clear morning",
        project_type="Outdoor - Decking",
        ranked_slots='["8:00 AM", "10:00 AM", "1:00 PM", "3:00 PM"]',
        recommendation="8:00 AM",
        ranking_reason="Outdoor project with afternoon rain forecast - morning slots preferred"
    ).with_inputs("available_slots", "user_preference", "weather_info", "project_type"),

    dspy.Example(
        available_slots='["9:00 AM", "11:00 AM", "2:00 PM", "4:00 PM"]',
        user_preference="",
        weather_info="Morning fog, clearing by noon, sunny afternoon",
        project_type="Outdoor - Roofing",
        ranked_slots='["2:00 PM", "4:00 PM", "11:00 AM", "9:00 AM"]',
        recommendation="2:00 PM",
        ranking_reason="Roofing work better in clear conditions - afternoon recommended"
    ).with_inputs("available_slots", "user_preference", "weather_info", "project_type"),

    # Earliest available
    dspy.Example(
        available_slots='["10:00 AM", "11:30 AM", "2:00 PM"]',
        user_preference="earliest",
        weather_info="",
        project_type="Appliance Installation",
        ranked_slots='["10:00 AM", "11:30 AM", "2:00 PM"]',
        recommendation="10:00 AM",
        ranking_reason="User wants earliest - first available slot"
    ).with_inputs("available_slots", "user_preference", "weather_info", "project_type"),

    # Latest available
    dspy.Example(
        available_slots='["8:00 AM", "10:00 AM", "3:00 PM", "4:30 PM"]',
        user_preference="latest",
        weather_info="",
        project_type="Window Installation",
        ranked_slots='["4:30 PM", "3:00 PM", "10:00 AM", "8:00 AM"]',
        recommendation="4:30 PM",
        ranking_reason="User wants latest - last available slot"
    ).with_inputs("available_slots", "user_preference", "weather_info", "project_type"),

    # Hot weather consideration for outdoor
    dspy.Example(
        available_slots='["8:00 AM", "10:00 AM", "12:00 PM", "2:00 PM", "4:00 PM"]',
        user_preference="",
        weather_info="High of 95°F, hottest 12-3 PM",
        project_type="Outdoor - Decking",
        ranked_slots='["8:00 AM", "10:00 AM", "4:00 PM", "12:00 PM", "2:00 PM"]',
        recommendation="8:00 AM",
        ranking_reason="Hot day - early morning best for outdoor work, avoid peak heat"
    ).with_inputs("available_slots", "user_preference", "weather_info", "project_type"),

    # Cold weather consideration
    dspy.Example(
        available_slots='["8:00 AM", "10:00 AM", "1:00 PM", "3:00 PM"]',
        user_preference="",
        weather_info="Low of 20°F in morning, warming to 35°F by afternoon",
        project_type="Outdoor - Roofing",
        ranked_slots='["1:00 PM", "3:00 PM", "10:00 AM", "8:00 AM"]',
        recommendation="1:00 PM",
        ranking_reason="Cold morning - afternoon better for outdoor roofing when warmer"
    ).with_inputs("available_slots", "user_preference", "weather_info", "project_type"),

    # Indoor project - weather doesn't matter
    dspy.Example(
        available_slots='["9:00 AM", "11:00 AM", "2:00 PM"]',
        user_preference="",
        weather_info="Thunderstorms all day",
        project_type="Indoor - Kitchen Remodel",
        ranked_slots='["9:00 AM", "11:00 AM", "2:00 PM"]',
        recommendation="9:00 AM",
        ranking_reason="Indoor project - weather doesn't affect work, earliest slot recommended"
    ).with_inputs("available_slots", "user_preference", "weather_info", "project_type"),

    # Combined preference and weather
    dspy.Example(
        available_slots='["8:00 AM", "10:00 AM", "1:00 PM", "3:00 PM"]',
        user_preference="afternoon",
        weather_info="Rain clearing by 2 PM",
        project_type="Outdoor - Fence Installation",
        ranked_slots='["3:00 PM", "1:00 PM", "10:00 AM", "8:00 AM"]',
        recommendation="3:00 PM",
        ranking_reason="User prefers afternoon + rain clears by 2 PM - 3 PM is optimal"
    ).with_inputs("available_slots", "user_preference", "weather_info", "project_type"),
]


def get_all_examples():
    """Return all training examples as a dict."""
    return {
        'classification': CLASSIFICATION_EXAMPLES,
        'entity_extraction': ENTITY_EXAMPLES,
        'weather_context': WEATHER_CONTEXT_EXAMPLES,
        'action_guard': GUARD_EXAMPLES,
        'date_interpreter': DATE_INTERPRETER_EXAMPLES,
        'context_resolver': CONTEXT_RESOLVER_EXAMPLES,
        'response_style': RESPONSE_STYLE_EXAMPLES,
        'slot_ranker': SLOT_RANKER_EXAMPLES,
    }


def get_trainset(example_type: str = 'classification'):
    """Get training set for a specific module."""
    examples = get_all_examples()
    return examples.get(example_type, [])


def print_stats():
    """Print training data statistics."""
    examples = get_all_examples()
    print("Training Data Statistics:")
    print("-" * 40)
    for name, data in examples.items():
        print(f"  {name}: {len(data)} examples")
    print("-" * 40)
    print(f"  Total: {sum(len(d) for d in examples.values())} examples")


if __name__ == "__main__":
    print_stats()
