from database.db import SessionLocal, create_tables_sync
from database.models import University, Course, Unit, Topic


def seed():
    create_tables_sync()
    db = SessionLocal()
    try:
        # Check if already seeded
        if db.query(University).filter(University.name == "University of Nairobi").first():
            print("Database already seeded.")
            return

        uon = University(name="University of Nairobi")
        db.add(uon)
        db.flush()

        mbchb = Course(name="MBChB", university_id=uon.id)
        db.add(mbchb)
        db.flush()

        # Year 1 Units and Topics
        y1_units = {
            "Human Anatomy": ["Upper Limb", "Head and Neck", "Thorax", "Abdomen", "Lower Limb", "Neuroanatomy"],
            "Physiology I": ["Cardiovascular", "Respiratory", "Renal", "Endocrine"],
            "Biochemistry": ["Carbohydrates", "Proteins", "Lipids", "Enzymes"],
            "Behavioural Science": ["Personality", "Stress", "Communication Skills"],
            "IT in Medicine": ["Data Management", "Medical Informatics"],
        }

        # Year 2 Units and Topics
        y2_units = {
            "Microbiology": ["Bacteriology", "Virology", "Parasitology", "Mycology"],
            "Immunology": ["Innate Immunity", "Adaptive Immunity", "Vaccines"],
            "Pathology I": ["Cellular Injury", "Inflammation", "Neoplasia"],
            "Physiology II": ["Reproductive", "Gastrointestinal", "Neurophysiology"],
        }

        # Year 3 Units and Topics
        y3_units = {
            "Pathology II": ["Systemic Pathology", "Hematology", "Immunopathology"],
            "Clinical Pharmacology I": ["Autonomic Drugs", "Antibiotics", "Analgesics"],
            "General Surgery I": ["Wound Healing", "Fluid Therapy", "Trauma Basics"],
            "Internal Medicine I": ["Cardiovascular Diseases", "Respiratory Diseases"],
        }

        def add_units(year: int, mapping: dict):
            for unit_name, topics in mapping.items():
                unit = Unit(name=unit_name, course_id=mbchb.id, year=year)
                db.add(unit)
                db.flush()
                for t in topics:
                    db.add(Topic(name=t, unit_id=unit.id))

        add_units(1, y1_units)
        add_units(2, y2_units)
        add_units(3, y3_units)

        db.commit()
        print("Seeded: UoN → MBChB (Years 1–3)")
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_tables_sync()
    seed()


