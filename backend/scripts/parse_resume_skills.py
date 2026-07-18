from __future__ import annotations

from app.core.database import SessionLocal
from app.db.models import ActingCredit, ActorProfile
from app.services.resume_pdf_service import ResumePdfService
from app.services.skill_parser_service import SkillParserService


def main() -> None:
    db = SessionLocal()
    try:
        actor = db.query(ActorProfile).first()
        if not actor:
            print("No actor profile found.")
            return
        parser = SkillParserService()
        source_values = list(actor.skills or []) + list(actor.accents or [])
        aggregate_rows = (
            db.query(ActingCredit)
            .filter(ActingCredit.actor_profile_id == actor.id)
            .filter(ActingCredit.category == "Special Skills")
            .all()
        )
        rows_to_remove = []
        for row in aggregate_rows:
            if row.skill_name:
                source_values.append(row.skill_name)
                if "," in row.skill_name:
                    rows_to_remove.append(row)
                else:
                    row.skill_category = parser.category_for(row.skill_name)
                    row.proficiency = row.proficiency or parser.parse_items([row.skill_name])[0].proficiency
        parsed = parser.parse_items(source_values)
        existing = {
            (row.skill_name or "").strip().lower()
            for row in aggregate_rows
            if row.skill_name and row not in rows_to_remove
        }
        created = 0
        for index, skill in enumerate(parsed):
            if skill.name.lower() in existing:
                continue
            db.add(
                ActingCredit(
                    actor_profile_id=actor.id,
                    category="Special Skills",
                    display_order=index,
                    skill_name=skill.name,
                    skill_category=skill.category,
                    proficiency=skill.proficiency,
                    notes="Parsed from resume Special Skills section.",
                )
            )
            created += 1
        for row in rows_to_remove:
            db.delete(row)
        actor.skills = sorted(set(parser.actor_skills(parsed)))
        actor.accents = sorted(set(parser.accents(parsed)))
        db.flush()
        ResumePdfService(db).regenerate_for_actor(actor.id)
        db.commit()
        print(
            f"Parsed {len(parsed)} skills. Created {created} categorized skill rows. "
            f"Removed {len(rows_to_remove)} aggregate skill rows."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
