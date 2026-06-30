# future_proofing.py

import os
import pandas as pd

# Skill Classification Database
# mapping skill name (lowercase) -> (automation_risk [0.0 - 1.0], trend, description)
SKILL_AUTOMATION_DATABASE = {
    # High Resiliency / Low Risk (< 0.3)
    "generative ai": (0.05, "High Growth", "Extremely resilient: Core of the current cognitive technological revolution."),
    "rag": (0.05, "High Growth", "High demand: Key architecture for context-aware AI systems."),
    "machine learning": (0.10, "High Growth", "Resilient: Driving predictive automation across all industries."),
    "deep learning": (0.10, "High Growth", "Resilient: Foundational math for visual, audio, and language models."),
    "nlp": (0.15, "High Growth", "High growth: Crucial for advanced text processing and dialogue."),
    "tensorflow": (0.15, "Stable", "Stable: Standard framework for deep learning deployment."),
    "pytorch": (0.12, "High Growth", "High growth: Preferred library for academic research and model training."),
    "langchain": (0.08, "High Growth", "High growth: Standard framework for building LLM applications."),
    "prompt engineering": (0.20, "High Growth", "Emerging: Essential for directing cognitive outputs, though evolving fast."),
    "ui/ux": (0.18, "High Growth", "Resilient: Requires deep human empathy and visual creativity."),
    "ui/ux design": (0.18, "High Growth", "Resilient: Empathy-driven design remains hard to automate."),
    "figma": (0.20, "High Growth", "High growth: Standard industry tool for digital product design."),
    "product management": (0.12, "High Growth", "Resilient: Requires strategic alignment, empathy, and leadership."),
    "product strategy": (0.10, "High Growth", "Resilient: High-level business strategy is safe from automation."),
    "embedded systems": (0.15, "Stable", "Stable: System-level hardware/software coordination is highly resilient."),
    "microcontrollers": (0.18, "Stable", "Stable: Low-level physical computing requires hands-on engineering."),
    "circuit design": (0.20, "Stable", "Stable: Complex electrical design requires deep physics modeling."),
    "cloud": (0.20, "High Growth", "High growth: Cloud architectures are scaling globally."),
    "aws": (0.20, "High Growth", "High growth: Leading cloud platform infrastructure."),
    "docker": (0.22, "High Growth", "High growth: Standard for containerized application deployment."),
    "kubernetes": (0.20, "High Growth", "High growth: Standard for container orchestration at scale."),
    "dsa": (0.25, "Stable", "Stable: Algorithmic complexity design requires logical engineering."),
    "structural engineering": (0.15, "Stable", "Stable: Safety-critical physical calculations remain human-certified."),
    "concrete design": (0.18, "Stable", "Stable: Materials engineering requires physical site validation."),
    "construction management": (0.20, "Stable", "Stable: Operational site management requires human coordination."),
    "strategy": (0.12, "High Growth", "Resilient: High-level consulting and organizational strategy."),
    "consulting": (0.15, "Stable", "Stable: High-level business advisory requires stakeholder empathy."),
    "talent acquisition": (0.25, "Stable", "Stable: Recruiting people relies heavily on personal relationship-building."),
    "recruitment": (0.28, "Stable", "Stable: Candidate screening can be assisted by AI, but final hiring remains human-centric."),

    # Medium Resiliency / Medium Risk (0.3 - 0.6)
    "python": (0.35, "High Growth", "High growth: Popular syntax, though AI co-pilots easily assist code writing."),
    "java": (0.40, "Stable", "Stable: Enterprise backend language, highly assisted by AI coding tools."),
    "javascript": (0.38, "High Growth", "High growth: Essential for web, though heavily assisted by code automation."),
    "sql": (0.42, "Stable", "Stable: Database querying, highly vulnerable to text-to-SQL AI generators."),
    "mysql": (0.45, "Stable", "Stable: SQL database management, assisted by automated queries."),
    "mongodb": (0.40, "Stable", "Stable: Document database, structured queries are easily assisted."),
    "nodejs": (0.35, "High Growth", "High growth: Standard backend environment, heavily assisted by code models."),
    "react": (0.32, "High Growth", "High growth: Leading frontend library, partially automated by visual code generators."),
    "angular": (0.38, "Stable", "Stable: Enterprise web framework, assisted by template generators."),
    "flask": (0.40, "Stable", "Stable: Lightweight backend framework, easily scripted by AI."),
    "restful apis": (0.35, "Stable", "Stable: Standard network interfaces, easily designed by automated tools."),
    "dbms": (0.45, "Stable", "Stable: Core database concepts remain relevant, but administration is automating."),
    "oop": (0.40, "Stable", "Stable: Standard coding paradigm, code generation handles class designs."),
    "autocad": (0.45, "Stable", "Stable: 2D drafting is highly vulnerable to automated parametric design tools."),
    "cad": (0.42, "Stable", "Stable: Design drafting is transitioning to AI-assisted generative layout modeling."),
    "solidworks": (0.38, "Stable", "Stable: 3D mechanical modeling, increasingly assisted by parametric automation."),
    "thermodynamics": (0.35, "Stable", "Stable: Physical systems calculations are highly structured."),
    "git": (0.30, "Stable", "Stable: Version control tracking is essential for collaboration."),
    "github": (0.30, "Stable", "Stable: Collaboration platform, core to modern software management."),
    "linux": (0.32, "Stable", "Stable: Server operating system management, core utility."),
    "cyber security": (0.30, "High Growth", "High growth: Systems protection is crucial, though automated attacks require AI defense."),
    "cybersecurity": (0.30, "High Growth", "High growth: Crucial defensive field, co-evolving with AI-driven threat detection."),
    "finance": (0.35, "Stable", "Stable: Corporate finance concepts are stable, but data entry is fully automated."),
    "accounting": (0.50, "Declining", "Transitioning: Standard auditing and bookkeeping are highly automated by modern software."),
    "valuation": (0.38, "Stable", "Stable: Financial valuation modeling requires strategic contextual inputs."),
    "surveying": (0.40, "Stable", "Stable: Land measurements are increasingly digitized via drones and GPS."),
    "estimation": (0.45, "Stable", "Stable: Budgeting calculations are moving towards algorithmic models."),

    # Low Resiliency / High Risk (> 0.6)
    "excel": (0.65, "Declining", "Transitioning: Basic spreadsheet manipulation is highly automated by LLM integrations."),
    "power bi": (0.55, "Stable", "Stable: Interactive dashboard building is increasingly automated by prompt-to-dashboard tools."),
    "tableau": (0.55, "Stable", "Stable: Visual dashboard creation, highly assisted by automated data engines."),
    "writing": (0.70, "Declining", "Declining: Basic copywriting and content writing are heavily automated by Generative AI."),
    "copywriting": (0.72, "Declining", "Declining: High risk from automated marketing content generators."),
    "blogging": (0.68, "Declining", "Declining: Standard informational blog posts are heavily generated by LLMs."),
    "editing": (0.65, "Declining", "Transitioning: Basic text polishing and grammar checks are fully automated by NLP tools."),
    "reporting": (0.75, "Declining", "Declining: Automated data pipeline generation renders manual report compiling obsolete."),
    "management": (0.48, "Stable", "Stable: High-level personnel management is safe, but operational tracking is automated.")
}

def calculate_future_proof_score(user_skills):
    """
    Computes a composite Future-Proofing Resilience Score (0 to 100%) for a user's skills.
    Categorizes the skills into: Low, Medium, and High Automation Risk.
    """
    if not user_skills:
        return 50.0, [], [], []

    total_risk = 0.0
    matched_count = 0
    
    low_risk_skills = []     # Risk < 30% (Future-Proof)
    medium_risk_skills = []  # Risk 30% - 60% (Transitioning)
    high_risk_skills = []    # Risk > 60% (High Automation Risk)
    
    for skill in user_skills:
        skill_lower = skill.lower().strip()
        
        # 1. Match skill in database
        if skill_lower in SKILL_AUTOMATION_DATABASE:
            risk, trend, desc = SKILL_AUTOMATION_DATABASE[skill_lower]
        else:
            # Substring fallback check
            found = False
            for db_k, db_v in SKILL_AUTOMATION_DATABASE.items():
                if db_k in skill_lower or skill_lower in db_k:
                    risk, trend, desc = db_v
                    found = True
                    break
            if not found:
                # Default for unknown skills: Medium Risk (40%)
                risk, trend, desc = 0.40, "Stable", "Unclassified skill. Evaluated as standard operational capability."
        
        total_risk += risk
        matched_count += 1
        
        # Categorize
        skill_entry = {"name": skill, "risk": round(risk * 100, 1), "trend": trend, "desc": desc}
        if risk < 0.30:
            low_risk_skills.append(skill_entry)
        elif risk <= 0.60:
            medium_risk_skills.append(skill_entry)
        else:
            high_risk_skills.append(skill_entry)

    # Calculate average risk
    avg_risk = total_risk / max(matched_count, 1)
    resilience_score = max(0.0, min(100.0, (1.0 - avg_risk) * 100.0))
    
    # Apply small high-growth bonus (up to +10%) if they have key futuristic skills
    bonus = 0.0
    high_growth_keys = ["generative ai", "rag", "langchain", "machine learning", "deep learning", "cybersecurity"]
    for skill in user_skills:
        if skill.lower().strip() in high_growth_keys:
            bonus += 2.0
    resilience_score = min(100.0, resilience_score + bonus)
    
    return round(resilience_score, 2), low_risk_skills, medium_risk_skills, high_risk_skills

def get_shield_skills(target_career, user_skills):
    """
    Identifies high-value, low-risk (future-proof) skills from the target career profile
    that the user is currently missing, representing their best upskilling 'shield'.
    """
    try:
        df = pd.read_csv("datasets/careers.csv")
    except Exception:
        # Fallback dictionary if CSV fails
        from career_recommender import DEFAULT_CAREERS
        df = pd.DataFrame(DEFAULT_CAREERS)

    # Find the target career profile in datasets
    match = df[df["Career"].str.lower() == target_career.lower()]
    if match.empty:
        match = df[df["Career"].str.lower().str.contains(target_career.lower())]
        
    if match.empty:
        return []

    career_skills_str = match.iloc[0]["Skills"]
    # Split skills by space/commas
    import re
    career_skills = [s.strip() for s in re.split(r'[, ]+', career_skills_str) if s.strip()]
    
    # Find which required skills the user is missing
    user_skills_lower = [s.lower().strip() for s in user_skills]
    missing_career_skills = []
    for cs in career_skills:
        is_missing = True
        for us in user_skills_lower:
            if us in cs.lower() or cs.lower() in us:
                is_missing = False
                break
        if is_missing and cs not in missing_career_skills:
            missing_career_skills.append(cs)

    # Classify missing skills to select the lowest risk / highest value ones
    shield_candidates = []
    for cs in missing_career_skills:
        cs_lower = cs.lower()
        if cs_lower in SKILL_AUTOMATION_DATABASE:
            risk, trend, desc = SKILL_AUTOMATION_DATABASE[cs_lower]
        else:
            risk, trend, desc = 0.40, "Stable", ""
            
        # Select low-to-medium risk skills as shields
        if risk < 0.45:
            shield_candidates.append({
                "name": cs,
                "risk": round(risk * 100, 1),
                "trend": trend,
                "desc": desc if desc else "Highly valuable skill for the target career path."
            })
            
    # Sort by risk (lowest risk first)
    shield_candidates.sort(key=lambda x: x["risk"])
    return shield_candidates[:3]  # Return top 3 shield recommendations
