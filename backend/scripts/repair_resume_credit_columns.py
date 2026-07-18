from __future__ import annotations

from app.core.database import SessionLocal
from app.db.models import ActingCredit, ActorProfile
from app.services.resume_pdf_service import ResumePdfService


THEATER_FIXES = {
    "Story Park Sharee Astoria Park/ Youth on Target": ("Story Park", "Sharee", "Astoria Park / Youth on Target", None),
    "So the Ghosts Can Speak Fufune Producers Club": ("So the Ghosts Can Speak", "Foufoune", "Producers Club", None),
    "So the Ghosts Can Speak Foufoune Producers Club": ("So the Ghosts Can Speak", "Foufoune", "Producers Club", None),
    "A Shayna Maidel Stage Directions Niagara University": ("A Shayna Maidel", "Stage Directions", "Niagara University", None),
    "Twelfth Night Feste": ("Twelfth Night", "Feste", None, None),
    "Comedy Cubed: The Celebration Tatiana Coffee House": ("Comedy Cubed: The Celebration", "Tatiana", "Coffee House", None),
    "Utopia Parkway Beggar/Judge": ("Utopia Parkway", "Beggar/Judge", None, None),
    "The Maids Madame Coffee House": ("The Maids", "Madame", "Coffee House", None),
    "RPG Bina Room 100 Productions": ("RPG", "Bina", "Room 100 Productions", None),
    "Stepping Out Andy Dir. Linda Silvestri": ("Stepping Out", "Andy", None, "Linda Silvestri"),
    "Ascent of the Muse Ella (old and young) Dir. Carrie Klewin": (
        "Ascent of the Muse",
        "Ella (old and young)",
        None,
        "Carrie Klewin",
    ),
    "Kiss Me or Cut Off My Head-Video Portion Rosie": (
        "Kiss Me or Cut Off My Head - Video Portion",
        "Rosie",
        None,
        None,
    ),
}

TRAINING_FIXES = {
    "William Esper Acting StudioCompleted 2 year program Deb Jackel/ David Newer": (
        "Completed 2 Year Meisner Program",
        "Deb Jackel / David Newer",
        "William Esper Acting Studio",
        None,
    ),
    "Auditioning for TV/Film Jennifer Rudolph, CD": (
        "TV/Film Audition Procedure",
        "Jennifer Rudolph",
        "Mitchell/Rudolph Casting",
        None,
    ),
    "Viewpoints Acting Technique Deena Roncone": (
        "Viewpoints Acting Training",
        "Deena Roncone",
        "Group Study",
        None,
    ),
    "Shakespeare Study, Character": (
        "Shakespeare Study",
        "Roger Keicher",
        "Group Study",
        None,
    ),
    "Breakdown, Voice and Diction Roger Keicher": (
        "Breakdown, Voice and Diction",
        "Roger Keicher",
        None,
        None,
    ),
    "Beginning Acting Tim Ward": ("Beginning Acting", "Tim Ward", None, None),
    "AA in Theatre Performance Niagara Cty Com. College": (
        "A.A. Theatre Studies",
        None,
        "Niagara County Community College",
        None,
    ),
}

NON_CREDIT_TRAINING_ROWS = {
    "Physical Characteristics / Measurements",
    "Height: 5'4\" Weight: 230 lbs",
}

SKILL_ROW_PREFIXES = (
    "Aerobics,",
    "Soccer,",
    "Improvisation,",
    "Vocal Style:",
)


def main() -> None:
    db = SessionLocal()
    try:
        actor = db.query(ActorProfile).first()
        if not actor:
            print("No actor profile found.")
            return
        changed = 0
        credits = db.query(ActingCredit).filter(ActingCredit.actor_profile_id == actor.id).all()
        for credit in credits:
            raw = _raw_row(credit)
            if credit.category == "Theater" and raw in THEATER_FIXES:
                project, role, theater, director = THEATER_FIXES[raw]
                credit.project_title = project
                credit.role_or_character = role
                credit.role_type = credit.role_type or role
                credit.production_company = theater
                credit.network_or_distributor = None
                credit.director = director or credit.director
                changed += 1
            elif credit.category == "Training" and raw in TRAINING_FIXES:
                program, instructor, institution, year = TRAINING_FIXES[raw]
                credit.class_or_program = program
                credit.instructor = instructor
                credit.institution = institution
                credit.year = year
                changed += 1
            elif credit.category == "Training" and raw in NON_CREDIT_TRAINING_ROWS:
                credit.category = "Other"
                credit.section_enabled = False
                credit.notes = f"{credit.notes or ''} Hidden from resume: non-credit measurement row.".strip()
                changed += 1
            elif credit.category == "Training" and raw.startswith(SKILL_ROW_PREFIXES):
                credit.category = "Special Skills"
                credit.skill_name = raw
                credit.class_or_program = None
                credit.instructor = None
                credit.institution = None
                changed += 1
            if credit.category in {"Television", "New Media"} and credit.production_company and not credit.network_or_distributor:
                credit.network_or_distributor = credit.production_company
                credit.production_company = None
                changed += 1
        db.flush()
        ResumePdfService(db).regenerate_for_actor(actor.id)
        db.commit()
        print(f"Repaired {changed} resume credit field placements.")
    finally:
        db.close()


def _raw_row(credit: ActingCredit) -> str:
    notes = credit.notes or ""
    marker = "Raw row:"
    if marker in notes:
        return notes.split(marker, 1)[1].strip()
    return (credit.project_title or credit.class_or_program or credit.skill_name or "").strip()


if __name__ == "__main__":
    main()
