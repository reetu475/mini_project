# skill_extractor.py

import re
import pandas as pd

# Try to load spaCy NLP package and the English pipeline model
try:
    import spacy
    nlp = spacy.load("en_core_web_sm")
    SPACY_AVAILABLE = True
    print("spaCy NLP engine (en_core_web_sm) loaded successfully.")
except Exception as e:
    print(f"Warning: Could not load spaCy or en_core_web_sm ({e}). Falling back to pure regex.")
    nlp = None
    SPACY_AVAILABLE = False

# Hardcoded fallback list in case CSV fails to load
DEFAULT_SKILLS = [
    "Python", "Java", "C", "C++", "JavaScript", "React", "NodeJS", 
    "SQL", "MySQL", "MongoDB", "Machine Learning", "Deep Learning", 
    "NLP", "TensorFlow", "PyTorch", "Computer Vision", "Power BI", 
    "Tableau", "Excel", "AWS", "Azure", "Docker", "Kubernetes", 
    "Linux", "Networking", "Cyber Security", "DSA", "DBMS", "OOP", 
    "Cloud", "Cyber", "AI", "Artificial Intelligence", "Cybersecurity",
    "Finance", "Accounting", "Financial Modeling", "Valuation", "Figma",
    "UI/UX", "Design", "Wireframing", "Prototyping", "Recruitment", "HR",
    "CAD", "SolidWorks", "AutoCAD", "Thermodynamics", "Writing", "Blogging",
    "Civil Engineering", "Civil Engineer", "Structural Engineering", "Concrete Design",
    "Construction Management", "Surveying", "Soil Mechanics", "Quantity Surveying",
    "Estimation", "Geotechnical Engineering"
]

try:
    skills_df = pd.read_csv("datasets/skills.csv")
    skills_list = skills_df["Skill"].dropna().str.strip().tolist()
    SKILLS = list(set([s for s in skills_list if s.lower() != "skill"]))
except Exception as e:
    print(f"Warning: Could not load datasets/skills.csv ({e}). Using default skills list.")
    SKILLS = DEFAULT_SKILLS


def extract_skills(text):
    """
    Extracts known skills from freeform input text.
    Uses spaCy NLP parser to extract noun chunks and named entities for higher linguistic precision.
    """
    if not text or not isinstance(text, str):
        return []
        
    found_skills = set()
    text_lower = text.lower()

    # 1. NLP Processing: Parse text with spaCy if available
    if SPACY_AVAILABLE and nlp:
        try:
            doc = nlp(text)
            # Extract noun chunks (phrases) and named entities (proper nouns, tools, languages)
            noun_chunks = [chunk.text.lower() for chunk in doc.noun_chunks]
            named_entities = [ent.text.lower() for ent in doc.ents]
            
            # Join the parsed linguistic components
            parsed_text = " | ".join(noun_chunks + named_entities)
        except Exception as e:
            print(f"spaCy NLP parsing error: {e}")
            parsed_text = text_lower
    else:
        parsed_text = text_lower

    # 2. Match known skills within the parsed linguistic units
    for skill in SKILLS:
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        
        # Match against either the NLP parsed chunks or the raw text
        if re.search(pattern, parsed_text) or re.search(pattern, text_lower):
            found_skills.add(skill)

    return list(found_skills)


def extract_skills_with_groq(text, api_key):
    """Uses Groq to extract skills dynamically from freeform text."""
    try:
        from groq import Groq
        import json
        
        client = Groq(api_key=api_key)
        prompt = f"""
You are a skill extraction engine. Extract a list of professional skills, technologies, tools, or methodologies from this text: "{text}".
Return ONLY a JSON list of strings. Do not include any explanation or markdown formatting. 
Example response: ["Embedded Systems", "MATLAB", "Circuit Design"]
"""
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
            temperature=0.0,
            max_tokens=200
        )
        response_text = completion.choices[0].message.content.strip()
        
        # Clean up response in case it contains markdown formatting
        json_match = re.search(r'(\[.*\])', response_text, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group(1))
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed]
    except Exception as e:
        print(f"Error in Groq skill extraction: {e}. Falling back to spaCy.")
    
    # Fallback to local spaCy/regex matching
    return extract_skills(text)


if __name__ == "__main__":
    test_text = "I am an ECE student specializing in embedded systems, microcontrollers, and circuit design."
    skills = extract_skills(test_text)
    print("Test Input:", test_text)
    print("Extracted Skills (via spaCy NLP):", skills)