import os
import re
import json
import math
from collections import Counter

try:
    import pandas as pd
except Exception:
    pd = None

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    SKLEARN_AVAILABLE = True
except Exception as e:
    SKLEARN_AVAILABLE = False
    TfidfVectorizer = None
    cosine_similarity = None
    np = None
    print(f"Notice: Optional sklearn/numpy acceleration unavailable ({e}). Using pure-Python similarity engine.")


def _pure_cosine_similarity(text1, text2):
    """Calculates term frequency cosine similarity between two text strings using pure Python."""
    try:
        words1 = [w for w in re.findall(r'[a-zA-Z0-9#+.-]+', text1.lower()) if len(w) > 1]
        words2 = [w for w in re.findall(r'[a-zA-Z0-9#+.-]+', text2.lower()) if len(w) > 1]
        if not words1 or not words2:
            return 0.0
        c1, c2 = Counter(words1), Counter(words2)
        all_words = set(c1.keys()).union(set(c2.keys()))
        dot_prod = sum(c1.get(w, 0) * c2.get(w, 0) for w in all_words)
        mag1 = math.sqrt(sum(v * v for v in c1.values()))
        mag2 = math.sqrt(sum(v * v for v in c2.values()))
        if mag1 == 0.0 or mag2 == 0.0:
            return 0.0
        return float(dot_prod / (mag1 * mag2))
    except Exception:
        return 0.0

# Fallback career paths in case CSV fails to load
DEFAULT_CAREERS = [
    {"Career": "Generative AI Engineer", "Skills": "Python PyTorch Transformers LLMs LangChain LlamaIndex RAG Vector Databases ChromaDB Pinecone Fine-Tuning LoRA Prompt Engineering OpenAI API"},
    {"Career": "LLM Engineer", "Skills": "Python Hugging Face Transformers Quantization vLLM Ollama DeepSpeed LoRA QLoRA RAG Embeddings RLHF"},
    {"Career": "MLOps Engineer", "Skills": "Python Docker Kubernetes Kubeflow MLflow CI/CD Git AWS GCP Triton Model Monitoring DVC"},
    {"Career": "AI Solutions Architect", "Skills": "Python Cloud AWS Bedrock Azure OpenAI GCP Vertex AI Enterprise AI System Design RAG Microservices"},
    {"Career": "Full Stack AI Engineer", "Skills": "Python TypeScript React Next.js FastAPI LangChain Vector Databases Tailwind CSS REST APIs OpenAI API"},
    {"Career": "Cloud DevSecOps Engineer", "Skills": "Python Linux AWS Azure Docker Kubernetes Terraform CI/CD Zero Trust Cloud Security IAM"},
    {"Career": "Data Platform Engineer", "Skills": "Python SQL Snowflake Databricks dbt Apache Spark PySpark Airflow Apache Kafka ETL"},
    {"Career": "Machine Learning Engineer", "Skills": "Python Machine Learning Deep Learning PyTorch TensorFlow Scikit-Learn Feature Engineering"},
    {"Career": "Data Scientist", "Skills": "Python SQL Statistics Machine Learning Data Analysis Pandas NumPy Scikit-Learn"},
    {"Career": "Data Analyst", "Skills": "Python SQL Excel Power BI Tableau Business Intelligence Data Cleaning Dashboarding"},
    {"Career": "Software Engineer", "Skills": "Python Java DSA DBMS OOP System Design Git REST APIs"},
    {"Career": "Civil Engineer", "Skills": "Civil Engineer Civil Engineering AutoCAD CAD Structural Engineering Concrete Design Construction Management Surveying Estimation"}
]


def recommend_top_careers(user_skills, top_n=5):
    """
    Matches user skills against all careers in the dataset using a Hybrid Cosine-Overlap formula.
    Returns the top N matching careers with:
    - career: Career Title
    - score: Compatibility score (0.0 to 100.0)
    - matched_skills: Skills from the candidate matching this track
    - missing_skills: High priority skills needed to achieve 100%
    - match_level: 'Primary Recommendation', 'High Potential Fit', 'Strategic Tech Pivot', 'Emerging Tech Track'
    - transition_difficulty: 'Ready Now / High Alignment', '1-2 Months Focused Upskill', 'Strategic Pivot'
    """
    if not user_skills:
        return [{
            "career": "Software Engineer",
            "score": 0.0,
            "matched_skills": [],
            "missing_skills": ["Python", "DSA", "DBMS", "System Design"],
            "match_level": "Primary Recommendation",
            "transition_difficulty": "Foundational Learning"
        }]

    try:
        df = pd.read_csv("datasets/careers.csv")
    except Exception as e:
        print(f"Warning: Could not load datasets/careers.csv ({e}). Using default career profiles.")
        df = pd.DataFrame(DEFAULT_CAREERS)

    career_skills = df["Skills"].tolist()
    user_doc = " ".join(user_skills)
    documents = career_skills + [user_doc]

    cos_sims = {}
    if SKLEARN_AVAILABLE and TfidfVectorizer is not None:
        try:
            vectorizer = TfidfVectorizer()
            tfidf_matrix = vectorizer.fit_transform(documents)
            similarity = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1])
            for idx in range(len(df)):
                cos_sims[idx] = float(similarity[0][idx]) if idx < similarity.shape[1] else 0.0
        except Exception:
            for idx, c_str in enumerate(career_skills):
                cos_sims[idx] = _pure_cosine_similarity(user_doc, str(c_str))
    else:
        for idx, c_str in enumerate(career_skills):
            cos_sims[idx] = _pure_cosine_similarity(user_doc, str(c_str))

    user_words = set()
    for s in user_skills:
        user_words.update(re.findall(r'\w+', s.lower()))

    results = []
    for index, row in df.iterrows():
        career_title = str(row["Career"])
        career_skills_str = str(row["Skills"])
        
        # Word set
        career_words = set(re.findall(r'\w+', career_skills_str.lower()))
        matched_words = career_words.intersection(user_words)
        
        # Identify matched skills from candidate
        matched_s = [s for s in user_skills if any(w in s.lower() for w in career_words)]
        matched_s = list(dict.fromkeys(matched_s))
        
        # Extract individual skill tokens from career
        tokens = [t.strip() for t in re.findall(r'[A-Za-z0-9#+.-]+', career_skills_str) if len(t.strip()) > 1]
        missing_s = [t for t in tokens if t.lower() not in user_words and t.lower() not in ["and", "or", "for", "the", "with"]]
        missing_s = list(dict.fromkeys(missing_s))[:5]
        
        overlap_score = len(matched_words) / max(len(career_words), 1)
        cos_sim = cos_sims.get(index, 0.0)
        
        hybrid_val = (cos_sim * 0.35 + overlap_score * 0.65)
        if hybrid_val > 0:
            final_score = round(min(100.0, 30.0 + (hybrid_val * 70.0)), 1)
        else:
            final_score = 0.0

        results.append({
            "career": career_title,
            "score": final_score,
            "matched_skills": matched_s,
            "missing_skills": missing_s
        })

    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)
    top_matches = results[:top_n]

    for i, item in enumerate(top_matches):
        s = item["score"]
        if i == 0 and s >= 55.0:
            item["match_level"] = "Primary Recommendation"
            item["transition_difficulty"] = "Ready Now / High Alignment"
        elif s >= 75.0:
            item["match_level"] = "High Potential Fit"
            item["transition_difficulty"] = "Direct Match"
        elif s >= 50.0:
            item["match_level"] = "Strategic Tech Pivot"
            item["transition_difficulty"] = "1-2 Months Focused Upskill"
        elif s >= 30.0:
            item["match_level"] = "Emerging Tech Track"
            item["transition_difficulty"] = "2-3 Months Up-skilling"
        else:
            item["match_level"] = "Adjacent Exploration"
            item["transition_difficulty"] = "Comprehensive Training"

    return top_matches


def recommend_career(user_skills):
    """
    Matches user skills against career skill profiles using a Hybrid Overlap-Cosine Similarity formula.
    Returns the recommended career name and the matching score (0-100).
    """
    top = recommend_top_careers(user_skills, top_n=1)
    if top:
        return top[0]["career"], top[0]["score"]
    return "Software Engineer", 0.0


def recommend_top_careers_with_groq(user_skills, user_interests, api_key=None, top_n=4):
    """
    Leverages Groq LLM to suggest top matching careers and modern AI/tech pathways.
    Returns a list of structured suggestion dictionaries.
    """
    fallback_recs = recommend_top_careers(user_skills, top_n=top_n)
    
    from resume_parser import DEFAULT_GROQ_KEY
    if not api_key:
        api_key = os.getenv("GROQ_API_KEY") or DEFAULT_GROQ_KEY
    if not api_key:
        return fallback_recs

    try:
        from groq import Groq
        from resume_parser import get_groq_chat_model
        client = Groq(api_key=api_key)
        model_name = get_groq_chat_model(client)

        prompt = f"""You are an elite Tech Career Advisor specializing in modern technologies (Generative AI, LLMs, MLOps, Cloud DevSecOps, Data Platform, Cyber, Full Stack).
Candidate Skills: {user_skills}
Interests/Goals: {user_interests}

Suggest the top {top_n} career tracks for this candidate. Include their primary fit and high-potential modern AI/tech pivots.
Return ONLY a valid JSON list of objects matching this exact schema:
[
  {{
    "career": "Career Title",
    "score": 88.5,
    "rationale": "1 concise sentence why their background fits",
    "matched_skills": ["Skill1", "Skill2"],
    "missing_skills": ["GapSkill1", "GapSkill2"],
    "match_level": "Primary Recommendation",
    "transition_difficulty": "Ready Now"
  }}
]
No markdown, no intro. Pure JSON list."""

        completion = None
        for attempt in range(2):
            try:
                completion = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=model_name,
                    temperature=0.2,
                    max_tokens=340 if attempt == 0 else 220,
                    response_format={"type": "json_object"}
                )
                break
            except Exception as req_err:
                err_str = str(req_err).lower()
                if ("429" in err_str or "rate_limit" in err_str) and attempt == 0:
                    import time
                    time.sleep(1.5)
                    continue
                else:
                    raise req_err

        response_text = completion.choices[0].message.content.strip()
        json_match = re.search(r'(\[.*\])', response_text, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group(1))
            if isinstance(parsed, list) and len(parsed) > 0:
                return parsed
        # If wrapped in an object like {"careers": [...]}
        json_obj = re.search(r'(\{.*\})', response_text, re.DOTALL)
        if json_obj:
            obj = json.loads(json_obj.group(1))
            for k in ["careers", "suggestions", "paths", "recommendations"]:
                if k in obj and isinstance(obj[k], list) and len(obj[k]) > 0:
                    return obj[k]
    except Exception as e:
        print(f"Notice in Groq top careers recommendation: {e}. Falling back to hybrid model.")

    return fallback_recs


def recommend_career_with_groq(user_skills, user_interests, api_key=None):
    """Uses Groq to match skills and interests to a career path dynamically."""
    top = recommend_top_careers_with_groq(user_skills, user_interests, api_key, top_n=1)
    if top:
        c = top[0].get("career", "Software Engineer")
        s = top[0].get("score", 0.0)
        return str(c), round(float(s), 2)
    return recommend_career(user_skills)


def calculate_compatibility_score(user_skills, target_career):
    """
    Calculates compatibility score between user skills and a specific target career.
    Uses a Hybrid Overlap-Cosine Similarity formula.
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
        if SKLEARN_AVAILABLE and TfidfVectorizer is not None:
            vectorizer = TfidfVectorizer()
            tfidf_matrix = vectorizer.fit_transform(documents)
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
            cos_sim = float(similarity[0][0])
        else:
            cos_sim = _pure_cosine_similarity(user_doc, career_profile_skills)
    except Exception:
        cos_sim = _pure_cosine_similarity(user_doc, career_profile_skills)
        
    try:
        # Calculate overlap
        career_words = set(re.findall(r'\w+', career_profile_skills.lower()))
        user_words = set()
        for s in user_skills:
            user_words.update(re.findall(r'\w+', s.lower()))
            
        intersection = career_words.intersection(user_words)
        overlap_score = len(intersection) / max(len(career_words), 1)
        
        hybrid_val = (cos_sim * 0.3 + overlap_score * 0.7)
        if hybrid_val > 0:
            score = round(30.0 + (hybrid_val * 70.0), 2)
        else:
            score = 0.0
            
        if math.isnan(score) or score <= 0.0:
            score = 0.0
        return career_name, score
    except Exception as e:
        print(f"Error calculating score for specific career: {e}")
        return target_career, 0.0


def calculate_compatibility_score_with_groq(user_skills, target_career, api_key):
    """Uses Groq to calculate the compatibility score between user skills and a specific career."""
    try:
        from groq import Groq
        from resume_parser import get_groq_chat_model, DEFAULT_GROQ_KEY
        import json
        import re
        
        if not api_key:
            api_key = os.getenv("GROQ_API_KEY") or DEFAULT_GROQ_KEY
        client = Groq(api_key=api_key)
        model_name = get_groq_chat_model(client)
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
            model=model_name,
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