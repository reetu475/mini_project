# streamlit_app.py

import os
import re
import uuid
import sqlite3
import json
import streamlit as st
from dotenv import load_dotenv

# Load local .env file
load_dotenv()

# Set up Streamlit Page Configuration
st.set_page_config(
    page_title="PathFinder | Career & Educational Advisor",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom premium styling via markdown
st.markdown("""
<style>
    .reportview-container {
        background: #0f172a;
    }
    /* Logo styling */
    .logo-text {
        font-family: 'Outfit', sans-serif;
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #8b5cf6 0%, #3b82f6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .logo-sub {
        font-size: 0.95rem;
        color: #94a3b8;
        margin-bottom: 2rem;
    }
    /* Timeline / Roadmap Styling */
    .timeline-node {
        background: rgba(139, 92, 246, 0.1);
        border: 1px solid rgba(139, 92, 246, 0.25);
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .timeline-title {
        color: #f8fafc;
        font-weight: 600;
        font-size: 1.1rem;
        margin-bottom: 0.25rem;
    }
    .timeline-duration {
        font-size: 0.8rem;
        color: #8b5cf6;
        font-weight: bold;
    }
    /* Resource Card Styling */
    .resource-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 12px;
        padding: 1.25rem;
        height: 100%;
        transition: transform 0.2s;
    }
    .resource-card:hover {
        transform: translateY(-3px);
        border-color: rgba(255, 255, 255, 0.12);
    }
    .badge-provider {
        background: rgba(59, 130, 246, 0.1);
        color: #3b82f6;
        font-size: 0.75rem;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-weight: bold;
    }
    .badge-type {
        background: rgba(16, 185, 129, 0.1);
        color: #10b981;
        font-size: 0.75rem;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Helper to fetch configuration (Env var first, fallback to Streamlit Secrets)
def get_config(key, default=None):
    if key in os.environ:
        return os.environ[key]
    try:
        # Check in streamlit secrets if initialized
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return default


# Import custom core modules
from skill_extractor import extract_skills, extract_skills_with_groq, SPACY_AVAILABLE
from career_recommender import (
    recommend_career, recommend_career_with_groq,
    calculate_compatibility_score, calculate_compatibility_score_with_groq
)
from education_advisor import EducationAdvisor
from roadmap_generator import generate_roadmap

# Initialize Advisor Class
@st.cache_resource
def get_advisor():
    return EducationAdvisor(db_path="chroma_db")

advisor = get_advisor()

# SQLite Database Helper Functions
def get_db_connection():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL;')
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS user_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            skills_text TEXT NOT NULL,
            interests TEXT,
            extracted_skills TEXT,
            recommended_career TEXT NOT NULL,
            match_score REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            session_id TEXT,
            submission_type TEXT,
            associated_resume_id INTEGER
        )
    ''')
    conn.commit()
    
    # Check/Migration for missing columns
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(user_profiles)")
    columns = [info[1] for info in cursor.fetchall()]
    if 'session_id' not in columns:
        conn.execute('ALTER TABLE user_profiles ADD COLUMN session_id TEXT')
        conn.commit()
    if 'submission_type' not in columns:
        conn.execute('ALTER TABLE user_profiles ADD COLUMN submission_type TEXT')
        conn.commit()
        conn.execute("UPDATE user_profiles SET submission_type = 'manual' WHERE submission_type IS NULL")
        conn.commit()
    if 'associated_resume_id' not in columns:
        conn.execute('ALTER TABLE user_profiles ADD COLUMN associated_resume_id INTEGER')
        conn.commit()
    conn.close()

# Run DB migration check
init_db()

# Initialize Session State
if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid.uuid4())
if "active_profile_id" not in st.session_state:
    st.session_state["active_profile_id"] = None
if "autofill_data" not in st.session_state:
    st.session_state["autofill_data"] = None

# Validation Regex Compile
NAME_REGEX = re.compile(r'^[a-zA-Z\s]{2,50}$')
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')

# Get Active API Key
if "custom_groq_key" not in st.session_state:
    st.session_state["custom_groq_key"] = ""

active_api_key = get_config("GROQ_API_KEY") or st.session_state["custom_groq_key"]


# Profile rendering results loader
def get_profile_results_context(row):
    if not row:
        return None
        
    name = row['name']
    email = row['email']
    skills_text = row['skills_text']
    interests = row['interests']
    recommended_career = row['recommended_career']
    match_score = row['match_score']
    
    try:
        user_skills = json.loads(row['extracted_skills'])
    except Exception:
        user_skills = [s.strip() for s in row['extracted_skills'].split(',') if s.strip()]
        
    # Semantic recommendations
    if active_api_key:
        recommendations = advisor.get_dynamic_recommendations_with_groq(recommended_career, active_api_key, limit=6)
    else:
        course_query = f"{recommended_career} {interests}"
        recommendations = advisor.get_recommendations(course_query, limit=6)
        
    courses = [r for r in recommendations if r.get('type') == 'Course']
    certifications = [r for r in recommendations if r.get('type') == 'Certification']
    
    # Generate Roadmap Steps
    roadmap_steps, roadmap_source = generate_roadmap(
        career=recommended_career,
        user_skills=user_skills,
        user_interests=interests,
        custom_api_key=active_api_key
    )
    
    return {
        'id': row['id'],
        'name': name,
        'email': email,
        'input_skills': skills_text,
        'extracted_skills': user_skills,
        'career': recommended_career,
        'match_score': match_score,
        'courses': courses,
        'certifications': certifications,
        'roadmap_steps': roadmap_steps,
        'roadmap_source': roadmap_source,
        'interests': interests
    }

# ----------------- SIDEBAR: SAVED HISTORY -----------------
with st.sidebar:
    st.markdown('<div class="logo-text">🧭 PathFinder</div>', unsafe_allow_html=True)
    st.markdown('<div class="logo-sub">Career Discovery Engine</div>', unsafe_allow_html=True)
    st.markdown("---")
    
    # API Key Input if not configured globally
    if not get_config("GROQ_API_KEY"):
        api_key_input = st.text_input(
            "Groq API Key",
            value=st.session_state["custom_groq_key"],
            type="password",
            help="Enter your Groq API key from console.groq.com to enable dynamic recommendations."
        )
        if api_key_input != st.session_state["custom_groq_key"]:
            st.session_state["custom_groq_key"] = api_key_input
            st.rerun()
        st.markdown("---")

    
    st.subheader("Saved Profiles")
    
    # Fetch profiles for current session
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM user_profiles 
        WHERE session_id = ? 
          AND (submission_type = 'manual' 
               OR (submission_type = 'resume' 
                   AND id NOT IN (
                       SELECT associated_resume_id 
                       FROM user_profiles 
                       WHERE session_id = ? AND associated_resume_id IS NOT NULL
                   )
                  )
              )
        ORDER BY created_at DESC
    ''', (st.session_state["session_id"], st.session_state["session_id"]))
    rows = cursor.fetchall()
    
    if not rows:
        st.info("No saved profiles in this session yet.")
    else:
        for r in rows:
            col_view, col_del = st.columns([4, 1])
            with col_view:
                label = f"🎓 {r['name']} ({r['recommended_career']})"
                if st.button(label, key=f"view_{r['id']}", use_container_width=True):
                    st.session_state["active_profile_id"] = r['id']
                    st.rerun()
            with col_del:
                if st.button("🗑️", key=f"del_{r['id']}"):
                    # Cascade Deletions
                    assoc_resume = r['associated_resume_id'] if 'associated_resume_id' in r.keys() else None
                    conn.execute('DELETE FROM user_profiles WHERE id = ? AND session_id = ?', (r['id'], st.session_state["session_id"]))
                    advisor.delete_user_profile_from_chroma(r['id'])
                    
                    if assoc_resume:
                        conn.execute('DELETE FROM user_profiles WHERE id = ? AND session_id = ?', (assoc_resume, st.session_state["session_id"]))
                        advisor.delete_user_profile_from_chroma(assoc_resume)
                        
                    if r['submission_type'] == 'resume':
                        cursor.execute('SELECT id FROM user_profiles WHERE associated_resume_id = ? AND session_id = ?', (r['id'], st.session_state["session_id"]))
                        assoc_manual = cursor.fetchone()
                        if assoc_manual:
                            advisor.delete_user_profile_from_chroma(assoc_manual['id'])
                        conn.execute('DELETE FROM user_profiles WHERE associated_resume_id = ? AND session_id = ?', (r['id'], st.session_state["session_id"]))
                    
                    conn.commit()
                    
                    if st.session_state["active_profile_id"] == r['id']:
                        st.session_state["active_profile_id"] = None
                    conn.close()
                    st.toast("Profile deleted successfully!")
                    st.rerun()
                    
    conn.close()
    
    st.markdown("---")
    # New analysis button
    if st.session_state["active_profile_id"] is not None:
        if st.button("➕ Create New Analysis", use_container_width=True):
            st.session_state["active_profile_id"] = None
            st.session_state["autofill_data"] = None
            st.rerun()

# ----------------- MAIN INTERFACE -----------------

# If no profile is actively selected, show input Forms side-by-side
if st.session_state["active_profile_id"] is None:
    st.title("🧭 Connect Your Profile Path")
    st.markdown("Provide details manually or upload a resume to construct your educational alignment map.")
    
    col_left, col_right = st.columns(2)
    
    # Autofill retrieval state helper
    pre_name = ""
    pre_email = ""
    pre_skills = ""
    pre_interests = ""
    pre_resume_id = ""
    pre_target_career = ""
    
    if st.session_state["autofill_data"]:
        pre_name = st.session_state["autofill_data"].get("name", "")
        pre_email = st.session_state["autofill_data"].get("email", "")
        pre_skills = st.session_state["autofill_data"].get("skills_text", "")
        pre_interests = st.session_state["autofill_data"].get("interests", "")
        pre_resume_id = st.session_state["autofill_data"].get("resume_profile_id", "")
        pre_target_career = st.session_state["autofill_data"].get("target_career", "")
    
    # ----------------- LEFT CARD: MANUAL PROFILE -----------------
    with col_left:
        with st.container(border=True):
            st.header("📝 Manual Profile Form")
            st.markdown("Fill out your details manually to generate your alignment roadmap.")
            
            with st.form("manual_profile_form"):
                m_name = st.text_input("Full Name", value=pre_name, placeholder="e.g. Alex Morgan")
                m_email = st.text_input("Email Address", value=pre_email, placeholder="alex@example.com")
                m_skills = st.text_area("Skills & Experience", value=pre_skills, placeholder="Describe your programming languages, frameworks, or past projects.")
                m_interests = st.text_input("Interests & Educational Goals", value=pre_interests, placeholder="e.g. Data visualization, backend web services, Cloud Computing")
                
                m_submit = st.form_submit_button("Generate Advisor Map", use_container_width=True)
                
                if m_submit:
                    # Input Validations
                    if not m_name or not NAME_REGEX.match(m_name):
                        st.error("Name must contain only letters and spaces (2 to 50 characters).")
                    elif not m_email or not EMAIL_REGEX.match(m_email):
                        st.error("Please provide a valid email address.")
                    elif not m_skills.strip():
                        st.error("Please write down your skills.")
                    else:
                        with st.spinner("Processing manual alignment recommendations..."):
                            # Extract Skills
                            if active_api_key:
                                user_skills = extract_skills_with_groq(m_skills, active_api_key)
                            else:
                                user_skills = extract_skills(m_skills)
                                
                            # Calculate scoring and recommend career
                            target_c = str(pre_target_career).strip()
                            if target_c:
                                rec_career = target_c
                                if active_api_key:
                                    m_score = calculate_compatibility_score_with_groq(user_skills, target_c, active_api_key)
                                else:
                                    _, m_score = calculate_compatibility_score(user_skills, target_c)
                            else:
                                if active_api_key:
                                    rec_career, m_score = recommend_career_with_groq(user_skills, m_interests, active_api_key)
                                else:
                                    rec_career, m_score = recommend_career(user_skills)
                                    
                            # Parse associated resume ID
                            assoc_id = int(pre_resume_id) if str(pre_resume_id).strip() else None
                            
                            # Save to SQLite
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            cursor.execute('''
                                INSERT INTO user_profiles (session_id, name, email, skills_text, interests, extracted_skills, recommended_career, match_score, submission_type, associated_resume_id)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                st.session_state["session_id"],
                                m_name,
                                m_email,
                                m_skills,
                                m_interests,
                                json.dumps(user_skills),
                                rec_career,
                                m_score,
                                'manual',
                                assoc_id
                            ))
                            conn.commit()
                            profile_id = cursor.lastrowid
                            
                            # Save to ChromaDB
                            advisor.save_user_profile(profile_id, m_name, m_email, m_skills, m_interests, rec_career, m_score, 'manual')
                            conn.close()
                            
                            st.session_state["active_profile_id"] = profile_id
                            st.session_state["autofill_data"] = None
                            st.rerun()

    # ----------------- RIGHT CARD: UPLOAD RESUME -----------------
    with col_right:
        with st.container(border=True):
            st.header("📄 Upload Resume Form")
            st.markdown("Upload your PDF, DOCX, or TXT resume for automatic parsing.")
            
            uploaded_file = st.file_uploader("Select Resume Document", type=["pdf", "docx", "txt"])
            target_career = st.text_input("Target / Aiming Career (Optional)", placeholder="e.g. Data Scientist, DevOps Engineer")
            
            col_direct, col_autofill = st.columns(2)
            
            with col_direct:
                direct_btn = st.button("Analyze Directly", use_container_width=True)
            with col_autofill:
                autofill_btn = st.button("Extract & Edit Form", use_container_width=True)
                
            if (direct_btn or autofill_btn) and uploaded_file is not None:
                with st.spinner("Extracting resume contents..."):
                    file_bytes = uploaded_file.read()
                    ext = os.path.splitext(uploaded_file.name)[1].lower()
                    
                    # File parsing based on format
                    from resume_parser import extract_text_from_pdf, extract_text_from_docx, extract_text_from_txt, parse_resume_text
                    if ext == '.pdf':
                        text = extract_text_from_pdf(file_bytes)
                    elif ext == '.docx':
                        text = extract_text_from_docx(file_bytes)
                    else:
                        text = extract_text_from_txt(file_bytes)
                        
                    if not text or not text.strip():
                        st.error("Could not extract text from the file.")
                    else:
                        # Parse details
                        parsed_profile = parse_resume_text(text, api_key=active_api_key)
                        name = parsed_profile.get("name", "Resume Candidate").strip()
                        email = parsed_profile.get("email", "resume_applicant@example.com").strip()
                        user_skills = parsed_profile.get("skills", [])
                        
                        interests = parsed_profile.get("interests", "").strip()
                        if not interests:
                            interests = target_career if target_career else "Software Engineering"
                            
                        # Evaluate matching
                        if target_career.strip():
                            recommended_career = target_career.strip()
                            if active_api_key:
                                match_score = calculate_compatibility_score_with_groq(user_skills, target_career.strip(), active_api_key)
                            else:
                                _, match_score = calculate_compatibility_score(user_skills, target_career.strip())
                        else:
                            if active_api_key:
                                recommended_career, match_score = recommend_career_with_groq(user_skills, interests, active_api_key)
                            else:
                                recommended_career, match_score = recommend_career(user_skills)
                                
                        # Execute based on selected pathway
                        if direct_btn:
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            cursor.execute('''
                                INSERT INTO user_profiles (session_id, name, email, skills_text, interests, extracted_skills, recommended_career, match_score, submission_type)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                st.session_state["session_id"],
                                name,
                                email,
                                text.strip(),
                                interests,
                                json.dumps(user_skills),
                                recommended_career,
                                match_score,
                                'resume'
                            ))
                            conn.commit()
                            profile_id = cursor.lastrowid
                            
                            # Save to ChromaDB
                            advisor.save_user_profile(profile_id, name, email, text.strip(), interests, recommended_career, match_score, 'resume')
                            conn.close()
                            
                            st.session_state["active_profile_id"] = profile_id
                            st.session_state["autofill_data"] = None
                            st.rerun()
                            
                        elif autofill_btn:
                            # Save resume temporarily in SQLite under 'resume' type
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            cursor.execute('''
                                INSERT INTO user_profiles (session_id, name, email, skills_text, interests, extracted_skills, recommended_career, match_score, submission_type)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                st.session_state["session_id"],
                                name,
                                email,
                                text.strip(),
                                interests,
                                json.dumps(user_skills),
                                recommended_career,
                                match_score,
                                'resume'
                            ))
                            conn.commit()
                            resume_id = cursor.lastrowid
                            
                            # Save to ChromaDB
                            advisor.save_user_profile(resume_id, name, email, text.strip(), interests, recommended_career, match_score, 'resume')
                            conn.close()
                            
                            # Populate manual form session state
                            st.session_state["autofill_data"] = {
                                "name": name,
                                "email": email,
                                "skills_text": text.strip(),
                                "interests": interests,
                                "resume_profile_id": resume_id,
                                "target_career": target_career.strip()
                            }
                            st.toast("Resume data extracted! Check the Manual Form on the left.")
                            st.rerun()

# ----------------- DISPLAY COMPILATION RESULTS -----------------
else:
    # Fetch active rows
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM user_profiles WHERE id = ? AND session_id = ?', (st.session_state["active_profile_id"], st.session_state["session_id"]))
    active_row = cursor.fetchone()
    
    manual_row = None
    resume_row = None
    
    if active_row:
        if active_row['submission_type'] == 'resume':
            resume_row = active_row
            cursor.execute('SELECT * FROM user_profiles WHERE session_id = ? AND associated_resume_id = ? AND submission_type = \'manual\' LIMIT 1', (st.session_state["session_id"], active_row['id']))
            manual_row = cursor.fetchone()
            default_tab_idx = 1
        else:
            manual_row = active_row
            assoc_id = active_row['associated_resume_id'] if 'associated_resume_id' in active_row.keys() else None
            if assoc_id:
                cursor.execute('SELECT * FROM user_profiles WHERE id = ? AND session_id = ? AND submission_type = \'resume\'', (assoc_id, st.session_state["session_id"]))
                resume_row = cursor.fetchone()
            default_tab_idx = 0
            
    conn.close()
    
    # Process Recommendation Contexts
    manual_results = get_profile_results_context(manual_row)
    resume_results = get_profile_results_context(resume_row)
    
    # Header user details
    header_user = manual_results if manual_results else resume_results
    st.title(f"🎓 Career Alignment Dashboard")
    st.markdown(f"**Candidate**: {header_user['name']} | **Email**: {header_user['email']}")
    
    # Back button
    if st.button("⬅️ Modify Profile Settings"):
        st.session_state["active_profile_id"] = None
        st.rerun()
        
    tab_manual, tab_resume = st.tabs(["📝 Manual Form Results", "📄 Resume Upload Results"])
    
    # ----------------- TAB 1: MANUAL RESULTS -----------------
    with tab_manual:
        if not manual_results:
            st.warning("No manual profile submitted for this run. Go back to fill details manually.")
        else:
            col_m_left, col_m_right = st.columns([1, 2])
            
            with col_m_left:
                with st.container(border=True):
                    st.metric(label="Skill Compatibility Score", value=f"{manual_results['match_score']}%")
                    st.subheader(manual_results['career'])
                    st.write(f"Based on your profile inputs, your skills align closely with a **{manual_results['career']}** career path.")
                
                # Extracted Skills
                with st.container(border=True):
                    st.subheader("Extracted Skills")
                    st.write(", ".join(manual_results['extracted_skills']))
                    
                # Profile details table
                with st.container(border=True):
                    st.subheader("Profile Info")
                    st.write(f"**Interests**: {manual_results['interests']}")
                    
            with col_m_right:
                # Roadmap steps
                with st.container(border=True):
                    st.subheader(f"Educational Roadmap ({manual_results['roadmap_source']})")
                    for step in manual_results['roadmap_steps']:
                        st.markdown(f"""
                        <div class="timeline-node">
                            <div class="timeline-title">Step {step['step_number']}: {step['title']}</div>
                            <div class="timeline-duration">⏳ Duration: {step['duration']}</div>
                            <ul>
                                {"".join(f"<li>{d}</li>" for d in step['details'])}
                            </ul>
                        </div>
                        """, unsafe_allow_html=True)
            
            st.markdown("---")
            st.subheader("📚 Recommended Learning Resources")
            col_courses, col_certs = st.columns(2)
            
            with col_courses:
                st.markdown("### Online Courses")
                if not manual_results['courses']:
                    st.info("No courses matched in database.")
                else:
                    for c in manual_results['courses']:
                        st.markdown(f"""
                        <div class="resource-card" style="margin-bottom:1rem;">
                            <span class="badge-provider">{c['provider']}</span> <span class="badge-type">Course</span>
                            <h4>{c['title']}</h4>
                            <p>{c['description']}</p>
                            <p>🔑 Skills: {c['skills']}</p>
                            <a href="{c['link']}" target="_blank" style="text-decoration:none;"><button style="background-color:#3b82f6;color:white;border:none;padding:5px 10px;border-radius:4px;cursor:pointer;">Start Learning</button></a>
                        </div>
                        """, unsafe_allow_html=True)
                        
            with col_certs:
                st.markdown("### Professional Certifications")
                if not manual_results['certifications']:
                    st.info("No professional certifications matched.")
                else:
                    for cert in manual_results['certifications']:
                        st.markdown(f"""
                        <div class="resource-card" style="margin-bottom:1rem;">
                            <span class="badge-provider">{cert['provider']}</span> <span class="badge-type">Certification</span>
                            <h4>{cert['title']}</h4>
                            <p>{cert['description']}</p>
                            <p>🔑 Skills: {cert['skills']}</p>
                            <a href="{cert['link']}" target="_blank" style="text-decoration:none;"><button style="background-color:#10b981;color:white;border:none;padding:5px 10px;border-radius:4px;cursor:pointer;">Register Now</button></a>
                        </div>
                        """, unsafe_allow_html=True)

    # ----------------- TAB 2: RESUME RESULTS -----------------
    with tab_resume:
        if not resume_results:
            st.warning("No resume document processed for this run. Go back to upload your resume.")
        else:
            col_r_left, col_r_right = st.columns([1, 2])
            
            with col_r_left:
                with st.container(border=True):
                    st.metric(label="Skill Compatibility Score", value=f"{resume_results['match_score']}%")
                    st.subheader(resume_results['career'])
                    st.write(f"Based on your parsed resume, your skills align closely with a **{resume_results['career']}** career path.")
                
                # Extracted Skills
                with st.container(border=True):
                    st.subheader("Extracted Skills")
                    st.write(", ".join(resume_results['extracted_skills']))
                    
                # Profile details table
                with st.container(border=True):
                    st.subheader("Profile Info")
                    st.write(f"**Interests**: {resume_results['interests']}")
                    
            with col_r_right:
                # Roadmap steps
                with st.container(border=True):
                    st.subheader(f"Educational Roadmap ({resume_results['roadmap_source']})")
                    for step in resume_results['roadmap_steps']:
                        st.markdown(f"""
                        <div class="timeline-node">
                            <div class="timeline-title">Step {step['step_number']}: {step['title']}</div>
                            <div class="timeline-duration">⏳ Duration: {step['duration']}</div>
                            <ul>
                                {"".join(f"<li>{d}</li>" for d in step['details'])}
                            </ul>
                        </div>
                        """, unsafe_allow_html=True)
            
            st.markdown("---")
            st.subheader("📚 Recommended Learning Resources")
            col_r_courses, col_r_certs = st.columns(2)
            
            with col_r_courses:
                st.markdown("### Online Courses")
                if not resume_results['courses']:
                    st.info("No courses matched in database.")
                else:
                    for c in resume_results['courses']:
                        st.markdown(f"""
                        <div class="resource-card" style="margin-bottom:1rem;">
                            <span class="badge-provider">{c['provider']}</span> <span class="badge-type">Course</span>
                            <h4>{c['title']}</h4>
                            <p>{c['description']}</p>
                            <p>🔑 Skills: {c['skills']}</p>
                            <a href="{c['link']}" target="_blank" style="text-decoration:none;"><button style="background-color:#3b82f6;color:white;border:none;padding:5px 10px;border-radius:4px;cursor:pointer;">Start Learning</button></a>
                        </div>
                        """, unsafe_allow_html=True)
                        
            with col_r_certs:
                st.markdown("### Professional Certifications")
                if not resume_results['certifications']:
                    st.info("No professional certifications matched.")
                else:
                    for cert in resume_results['certifications']:
                        st.markdown(f"""
                        <div class="resource-card" style="margin-bottom:1rem;">
                            <span class="badge-provider">{cert['provider']}</span> <span class="badge-type">Certification</span>
                            <h4>{cert['title']}</h4>
                            <p>{cert['description']}</p>
                            <p>🔑 Skills: {cert['skills']}</p>
                            <a href="{cert['link']}" target="_blank" style="text-decoration:none;"><button style="background-color:#10b981;color:white;border:none;padding:5px 10px;border-radius:4px;cursor:pointer;">Register Now</button></a>
                        </div>
                        """, unsafe_allow_html=True)
