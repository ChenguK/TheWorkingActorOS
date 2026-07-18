SUBMISSION_STATUSES = (
    "Submitted",
    "Requested",
    "Self-Tape Callback",
    "In-Person Callback",
    "Pinned",
    "Booked",
    "Passed",
    "No Response",
)

OPEN_SUBMISSION_STATUSES = ("Submitted", "Requested", "Self-Tape Callback", "In-Person Callback", "Pinned")
CALLBACK_STATUSES = ("Requested", "Self-Tape Callback", "In-Person Callback", "Pinned", "Booked")
OUTCOME_STATUSES = ("Requested", "Self-Tape Callback", "In-Person Callback", "Pinned", "Booked", "Passed", "No Response")

SELF_TAPE_STATUSES = ("Not Started", "In Progress", "Completed")

CALENDAR_EVENT_TYPES = (
    "Submission Due",
    "Self-Tape Due",
    "Virtual Callback",
    "In-Person Callback",
    "Fitting",
    "Shoot",
    "Meeting",
    "Other",
)

MAIN_BREAKDOWN_CLASSIFICATIONS = (
    "Acting Role",
    "Background Role",
    "Voiceover Role",
    "Theater Role",
    "Commercial Role",
)

BREAKDOWN_CLASSIFICATIONS = (*MAIN_BREAKDOWN_CLASSIFICATIONS, "Non-Acting Job", "Crew Job", "Unknown")

SOURCE_RESEARCH_STATUSES = ("Suggested", "Researching", "Approved", "Rejected", "Active", "Paused", "Deleted")

MATERIAL_TYPES = ("Headshot", "Reel", "Slate", "Resume")

ROLE_TYPES_INCLUDED_DEFAULT = (
    "Lead",
    "Supporting",
    "Principal",
    "Guest Star",
    "Co-Star",
    "Recurring",
    "Series Regular",
    "Voiceover",
    "Commercial Principal",
    "Theater Principal",
)

ROLE_TYPES_EXCLUDED_DEFAULT = (
    "Background",
    "Extra",
    "Ensemble",
    "Brand Ambassador",
    "Class",
    "Workshop",
    "Seminar",
    "Crew",
    "Staff Job",
    "Internship",
    "Administrative Job",
)

CAREER_TASK_PRIORITIES = ("Low", "Medium", "High")
CAREER_TASK_STATUSES = ("Not Started", "In Progress", "Partially Completed", "Completed")
CAREER_TASK_IMPACTS = ("Low", "Medium", "High")
