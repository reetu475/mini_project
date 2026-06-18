# career_recommender.py

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Fallback career paths in case CSV fails to load
DEFAULT_CAREERS = [
    {"Career": "AI Engineer", "Skills": "Python Machine Learning Deep Learning NLP TensorFlow"},
    {"Career": "Data Scientist", "Skills": "Python SQL Statistics Machine Learning"},
    {"Career": "Data Analyst", "Skills": "Python SQL Excel Power BI"},
    {"Career": "ML Engineer", "Skills": "Python Machine Learning TensorFlow"},
    {"Career": "Software Engineer", "Skills": "Python Java DSA DBMS OOP"}
]


def recommend_career(user_skills):
    """
    Matches user skills against career skill profiles using TF-IDF and Cosine Similarity.
    Returns the recommended career name and the matching score (0-100).
    """
    if not user_skills:
        # If no skills are provided, recommend Software Engineer with 0 similarity score
        return "Software Engineer", 0.0

    try:
        df = pd.read_csv("datasets/careers.csv")
    except Exception as e:
        print(f"Warning: Could not load datasets/careers.csv ({e}). Using default career profiles.")
        df = pd.DataFrame(DEFAULT_CAREERS)

    career_skills = df["Skills"].tolist()
    
    # Format user skills list into a single space-separated string document
    user_doc = " ".join(user_skills)
    documents = career_skills + [user_doc]

    try:
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(documents)

        # Compute cosine similarity between last document (user) and all others
        similarity = cosine_similarity(
            tfidf_matrix[-1],
            tfidf_matrix[:-1]
        )

        best_index = similarity.argmax()
        career = df.iloc[best_index]["Career"]
        
        # similarity is a 2D array: similarity[0][best_index]
        score_val = similarity[0][best_index]
        score = round(float(score_val) * 100, 2)
        
        if np.isnan(score) or score <= 0.0:
            score = 0.0
            
        return career, score
    except Exception as e:
        print(f"Error matching career: {e}")
        return "Software Engineer", 0.0


def recommend_career_with_groq(user_skills, user_interests, api_key):
    """Uses Groq to match skills and interests to a career path dynamically."""
    try:
        from groq import Groq
        import json
        import re
        
        client = Groq(api_key=api_key)
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert career recommender. You MUST analyze the candidate's skills and interests, "
                    "recommend the single best career path (e.g. 'Data Scientist', 'DevOps Engineer', 'Embedded Systems Engineer'), "
                    "and calculate a compatibility score between 0 and 100 representing how well their skills match the career. "
                    "You MUST return ONLY a valid JSON object matching this schema:\n"
                    "{\n"
                    '  "career": "Recommended Career Name",\n'
                    '  "score": 85.0\n'
                    "}\n"
                    "Do not wrap it in markdown codeblocks (like ```json), do not write any preamble, intro, or explanation."
                )
            },
            {
                "role": "user",
                "content": f"Candidate Skills: {user_skills}\nCandidate Interests: {user_interests}"
            }
        ]
        completion = client.chat.completions.create(
            messages=messages,
            model="llama-3.1-8b-instant",
            temperature=0.2,
            response_format={"type": "json_object"},
            max_tokens=200
        )
        response_text = completion.choices[0].message.content.strip()
        
        json_match = re.search(r'(\{.*\})', response_text, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group(1))
            career = parsed.get("career", "Software Engineer")
            score = parsed.get("score", 0.0)
            return str(career), round(float(score), 2)
    except Exception as e:
        print(f"Error in Groq career recommendation: {e}. Falling back to TF-IDF.")
        
    return recommend_career(user_skills)


def calculate_compatibility_score(user_skills, target_career):
    """
    Calculates compatibility score between user skills and a specific target career.
    Uses TF-IDF similarity against the career profile if found, otherwise computes similarity
    with the target career name as a proxy representation.
    """
    if not user_skills or not target_career:
        return target_career, 0.0

    try:
        df = pd.read_csv("datasets/careers.csv")
    except Exception as e:
        print(f"Warning: Could not load datasets/careers.csv ({e}). Using default career profiles.")
        df = pd.DataFrame(DEFAULT_CAREERS)

    # Search for target_career in the database
    # Try exact match first
    match = df[df["Career"].str.lower() == target_career.lower()]
    if match.empty:
        # Try substring match
        match = df[df["Career"].str.lower().str.contains(target_career.lower())]
        
    if not match.empty:
        career_profile_skills = match.iloc[0]["Skills"]
        career_name = match.iloc[0]["Career"]
    else:
        # If not found in our database, use the target career name itself as the skills proxy
        career_profile_skills = target_career
        career_name = target_career

    user_doc = " ".join(user_skills)
    documents = [career_profile_skills, user_doc]

    try:
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(documents)
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
        score = round(float(similarity[0][0]) * 100, 2)
        if np.isnan(score) or score <= 0.0:
            score = 0.0
        return career_name, score
    except Exception as e:
        print(f"Error calculating score for specific career: {e}")
        return target_career, 0.0


def calculate_compatibility_score_with_groq(user_skills, target_career, api_key):
    """Uses Groq to calculate the compatibility score between user skills and a specific career."""
    try:
        from groq import Groq
        import json
        import re
        
        client = Groq(api_key=api_key)
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a strict ATS parsing assistant. You MUST calculate a compatibility score between "
                    "0 and 100 based on how well the candidate's skills align with the target career. You MUST return "
                    "ONLY a valid JSON object matching this schema:\n"
                    "{\n"
                    '  "score": 78.5\n'
                    "}\n"
                    "Do not wrap it in markdown codeblocks (like ```json), do not write any preamble, intro, or explanation."
                )
            },
            {
                "role": "user",
                "content": f"Target Career: '{target_career}'\nCandidate Skills: {user_skills}"
            }
        ]
        completion = client.chat.completions.create(
            messages=messages,
            model="llama-3.1-8b-instant",
            temperature=0.0,
            response_format={"type": "json_object"},
            max_tokens=100
        )
        response_text = completion.choices[0].message.content.strip()
        json_match = re.search(r'(\{.*\})', response_text, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group(1))
            score = parsed.get("score", 0.0)
            return round(float(score), 2)
    except Exception as e:
        print(f"Error in Groq specific career match: {e}. Falling back to TF-IDF.")
        
    _, score = calculate_compatibility_score(user_skills, target_career)
    return score


if __name__ == "__main__":
    user_skills = ["Python", "SQL", "Machine Learning"]
    career, score = recommend_career(user_skills)
    print("Skills:", user_skills)
    print("Recommended Career:", career)
    print("Match Score:", score)