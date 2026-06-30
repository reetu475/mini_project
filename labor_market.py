# labor_market.py

import os
import pandas as pd
import re

MOCK_MARKET_DATA = {
    "AI Engineer": {
        "median_salary": "14.5 LPA",
        "demand_growth": "+22% YoY",
        "top_cities": ["Bangalore", "Hyderabad", "Pune"],
        "demand_level": "Very High"
    },
    "Data Scientist": {
        "median_salary": "11.8 LPA",
        "demand_growth": "+18% YoY",
        "top_cities": ["Bangalore", "Hyderabad", "Mumbai"],
        "demand_level": "Very High"
    },
    "Data Analyst": {
        "median_salary": "6.8 LPA",
        "demand_growth": "+12% YoY",
        "top_cities": ["Bangalore", "Delhi NCR", "Hyderabad"],
        "demand_level": "High"
    },
    "ML Engineer": {
        "median_salary": "12.5 LPA",
        "demand_growth": "+20% YoY",
        "top_cities": ["Bangalore", "Hyderabad", "Chennai"],
        "demand_level": "Very High"
    },
    "Software Engineer": {
        "median_salary": "8.0 LPA",
        "demand_growth": "+10% YoY",
        "top_cities": ["Bangalore", "Hyderabad", "Pune"],
        "demand_level": "High"
    },
    "Financial Analyst": {
        "median_salary": "7.5 LPA",
        "demand_growth": "+8% YoY",
        "top_cities": ["Mumbai", "Bangalore", "Gurugram"],
        "demand_level": "Moderate"
    },
    "Digital Marketer": {
        "median_salary": "5.2 LPA",
        "demand_growth": "+14% YoY",
        "top_cities": ["Mumbai", "Delhi NCR", "Bangalore"],
        "demand_level": "High"
    },
    "UI/UX Designer": {
        "median_salary": "8.5 LPA",
        "demand_growth": "+16% YoY",
        "top_cities": ["Bangalore", "Mumbai", "Pune"],
        "demand_level": "High"
    },
    "HR Specialist": {
        "median_salary": "5.8 LPA",
        "demand_growth": "+6% YoY",
        "top_cities": ["Mumbai", "Bangalore", "Hyderabad"],
        "demand_level": "Moderate"
    },
    "Mechanical Engineer": {
        "median_salary": "6.0 LPA",
        "demand_growth": "+4% YoY",
        "top_cities": ["Pune", "Chennai", "Ahmedabad"],
        "demand_level": "Moderate"
    },
    "Embedded Systems Engineer": {
        "median_salary": "8.2 LPA",
        "demand_growth": "+15% YoY",
        "top_cities": ["Bangalore", "Hyderabad", "Coimbatore"],
        "demand_level": "High"
    },
    "Product Manager": {
        "median_salary": "15.0 LPA",
        "demand_growth": "+17% YoY",
        "top_cities": ["Bangalore", "Mumbai", "Gurugram"],
        "demand_level": "Very High"
    },
    "Business Consultant": {
        "median_salary": "10.5 LPA",
        "demand_growth": "+9% YoY",
        "top_cities": ["Mumbai", "Delhi NCR", "Bangalore"],
        "demand_level": "High"
    },
    "Civil Engineer": {
        "median_salary": "5.5 LPA",
        "demand_growth": "+5% YoY",
        "top_cities": ["Mumbai", "Chennai", "Delhi NCR"],
        "demand_level": "Moderate"
    },
    "Content Writer": {
        "median_salary": "4.5 LPA",
        "demand_growth": "+7% YoY",
        "top_cities": ["Remote", "Mumbai", "Delhi NCR"],
        "demand_level": "Moderate"
    }
}

def get_market_analysis(career):
    """
    Retrieves mock labor market statistics for a given career path.
    """
    # Try exact match or substring match
    for k, v in MOCK_MARKET_DATA.items():
        if k.lower() in career.lower() or career.lower() in k.lower():
            return v
            
    # Default fallback
    return {
        "median_salary": "7.5 LPA",
        "demand_growth": "+8% YoY",
        "top_cities": ["Remote", "Bangalore", "Hyderabad"],
        "demand_level": "High"
    }

def get_missing_skills(career, user_skills):
    """
    Identifies what required skills for a target career the user is missing.
    Matches against careers.csv data by extracting complete skill entities.
    """
    try:
        df = pd.read_csv("datasets/careers.csv")
    except Exception:
        from career_recommender import DEFAULT_CAREERS
        df = pd.DataFrame(DEFAULT_CAREERS)

    # Search for target career
    match = df[df["Career"].str.lower() == career.lower()]
    if match.empty:
        match = df[df["Career"].str.lower().str.contains(career.lower())]
        
    if match.empty:
        return []

    career_skills_str = match.iloc[0]["Skills"].lower()
    
    # Load global skills list to find complete skill phrases
    try:
        from skill_extractor import SKILLS
    except ImportError:
        from skill_extractor import DEFAULT_SKILLS as SKILLS
        
    # Find which global skills exist in this career's skills string
    career_skills = []
    for skill in SKILLS:
        skill_lower = skill.lower().strip()
        # Use word boundaries to avoid partial matches
        pattern = r'\b' + re.escape(skill_lower) + r'\b'
        if re.search(pattern, career_skills_str):
            career_skills.append(skill)
            
    # Find which of these career skills the user is missing
    user_skills_lower = [s.lower().strip() for s in user_skills]
    missing_skills = []
    
    for cs in career_skills:
        cs_lower = cs.lower().strip()
        is_missing = True
        for us in user_skills_lower:
            if us == cs_lower or us in cs_lower or cs_lower in us:
                is_missing = False
                break
        if is_missing and cs not in missing_skills:
            missing_skills.append(cs)
            
    return missing_skills
