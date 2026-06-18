# app.py

import os
import re
import sqlite3
import json
import uuid
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from dotenv import load_dotenv

# Import our custom modules
from skill_extractor import extract_skills, extract_skills_with_groq, SPACY_AVAILABLE
from career_recommender import recommend_career, recommend_career_with_groq, calculate_compatibility_score, calculate_compatibility_score_with_groq
from education_advisor import EducationAdvisor
from roadmap_generator import generate_roadmap

# Load environment variables (such as GROQ_API_KEY) from .env file
load_dotenv()

from datetime import timedelta
app = Flask(__name__)
app.secret_key = "pathfinder_session_secret_key_98765"
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

# Initialize Education Advisor (which handles ChromaDB and fallback)
# We store the chroma database files in a directory called 'chroma_db'
advisor = EducationAdvisor(db_path="chroma_db")

# Database Helper functions for saving user profiles
def get_db_connection():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL;')
    return conn

def init_db():
    try:
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        
        # Check if columns exist
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
    except Exception as e:
        print(f"Error initializing database: {e}")

# Run DB initialization
init_db()

# Fetch latest manual and resume profiles in the session for side-by-side tabs
def fetch_latest_profiles(session_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Fetch latest manual profile
    cursor.execute('''
        SELECT * FROM user_profiles 
        WHERE session_id = ? AND submission_type = 'manual' 
        ORDER BY id DESC LIMIT 1
    ''', (session_id,))
    manual_row = cursor.fetchone()
    
    # Fetch latest resume profile
    cursor.execute('''
        SELECT * FROM user_profiles 
        WHERE session_id = ? AND submission_type = 'resume' 
        ORDER BY id DESC LIMIT 1
    ''', (session_id,))
    resume_row = cursor.fetchone()
    
    conn.close()
    return manual_row, resume_row

# Helper function to generate recommendation results dynamically for a profile row
def get_profile_results(row, active_api_key):
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
        
    # Fetch learning resources
    if active_api_key:
        recommendations = advisor.get_dynamic_recommendations_with_groq(recommended_career, active_api_key, limit=6)
    else:
        course_query = f"{recommended_career} {interests}"
        recommendations = advisor.get_recommendations(course_query, limit=6)
        
    courses = [r for r in recommendations if r.get('type') == 'Course']
    certifications = [r for r in recommendations if r.get('type') == 'Certification']
    
    # Generate Roadmap
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



# Regex pattern validation compile
NAME_REGEX = re.compile(r'^[a-zA-Z\s]{2,50}$')
# Standard RFC 5322 email validation regex
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')


@app.route('/', methods=['GET'])
def index():
    """Render the main input form and display saved profiles for the current session only."""
    env_groq_key = os.getenv("GROQ_API_KEY")
    has_env_key = bool(env_groq_key)
    
    # Initialize session_id if not present
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
        session.permanent = True
        
    profiles = []
    try:
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
        ''', (session['session_id'], session['session_id']))
        rows = cursor.fetchall()
        for row in rows:
            skills_list = []
            if row['extracted_skills']:
                try:
                    skills_list = json.loads(row['extracted_skills'])
                except Exception:
                    skills_list = [s.strip() for s in row['extracted_skills'].split(',') if s.strip()]
            
            profiles.append({
                'id': row['id'],
                'name': row['name'],
                'email': row['email'],
                'skills_text': row['skills_text'],
                'interests': row['interests'],
                'extracted_skills': skills_list,
                'recommended_career': row['recommended_career'],
                'match_score': row['match_score'],
                'created_at': row['created_at']
            })
        conn.close()
    except Exception as e:
        print(f"Error fetching saved profiles: {e}")
        
    return render_template(
        'index.html',
        has_env_key=has_env_key,
        profiles=profiles
    )


@app.route('/recommend', methods=['POST'])
def recommend():
    """Handle the profile submission, validate inputs, run models, save details, and return recommendations."""
    # 1. Retrieve inputs
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    skills_text = request.form.get('skills_text', '').strip()
    interests = request.form.get('interests', '').strip()
    custom_groq_key = request.form.get('custom_groq_key', '').strip()
    associated_resume_id = request.form.get('associated_resume_id', '').strip()
    target_career = request.form.get('target_career', '').strip()
    
    # Parse associated resume ID
    if associated_resume_id:
        try:
            associated_resume_id = int(associated_resume_id)
        except ValueError:
            associated_resume_id = None
    else:
        associated_resume_id = None
    
    # 2. Input validation using Regex
    errors = []
    if not name:
        errors.append("Name is required.")
    elif not NAME_REGEX.match(name):
        errors.append("Name must contain only letters and spaces (2 to 50 characters).")
        
    if not email:
        errors.append("Email address is required.")
    elif not EMAIL_REGEX.match(email):
        errors.append("Please provide a valid email address (e.g. user@domain.com).")
        
    if not skills_text:
        errors.append("Please write down your skills, experience, or upload text.")
        
    # If validation errors exist, flash them and return to form
    if errors:
        for err in errors:
            flash(err, "error")
        return redirect(url_for('index'))
        
    # Determine which API Key to use (custom key overrides env key)
    active_api_key = custom_groq_key or os.getenv("GROQ_API_KEY")

    # 3. Process skills extraction
    if active_api_key:
        user_skills = extract_skills_with_groq(skills_text, active_api_key)
    else:
        user_skills = extract_skills(skills_text)
    
    # 4. Predict/Recommend Career based on user skills
    if target_career:
        recommended_career = target_career
        if active_api_key:
            match_score = calculate_compatibility_score_with_groq(user_skills, target_career, active_api_key)
        else:
            recommended_career, match_score = calculate_compatibility_score(user_skills, target_career)
    else:
        if active_api_key:
            recommended_career, match_score = recommend_career_with_groq(user_skills, interests, active_api_key)
        else:
            recommended_career, match_score = recommend_career(user_skills)
    
    # 5. Save profile to SQLite database with session_id
    try:
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
            session.permanent = True
            
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO user_profiles (session_id, name, email, skills_text, interests, extracted_skills, recommended_career, match_score, submission_type, associated_resume_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session['session_id'],
            name,
            email,
            skills_text,
            interests,
            json.dumps(user_skills),
            recommended_career,
            match_score,
            'manual',
            associated_resume_id
        ))
        conn.commit()
        profile_id = cursor.lastrowid
        
        # Fetch exact rows for rendering
        cursor.execute('SELECT * FROM user_profiles WHERE id = ?', (profile_id,))
        manual_row = cursor.fetchone()
        
        resume_row = None
        if associated_resume_id:
            cursor.execute('SELECT * FROM user_profiles WHERE id = ? AND session_id = ?', (associated_resume_id, session['session_id']))
            resume_row = cursor.fetchone()
            
        conn.close()
        
        if custom_groq_key:
            session['custom_groq_key'] = custom_groq_key
        flash("Profile recommendation map generated and saved successfully!", "success")
    except Exception as e:
        print(f"Error saving profile: {e}")
        flash("Analysis complete, but error saving profile to database.", "warning")
        return redirect(url_for('index'))
    
    manual_results = get_profile_results(manual_row, active_api_key)
    resume_results = get_profile_results(resume_row, active_api_key)
    
    return render_template(
        'result.html',
        manual_results=manual_results,
        resume_results=resume_results,
        active_tab='manual',
        using_chromadb=advisor.use_chroma,
        using_nlp=SPACY_AVAILABLE
    )


@app.route('/api/parse-resume', methods=['POST'])
def api_parse_resume():
    """Parse resume file asynchronously and return extracted JSON data for autofill."""
    if 'resume_file' not in request.files:
        return jsonify({"success": False, "error": "No resume file uploaded."}), 400
        
    file = request.files['resume_file']
    if file.filename == '':
        return jsonify({"success": False, "error": "No selected file."}), 400
        
    custom_groq_key = request.form.get('custom_groq_key', '').strip()
    active_api_key = custom_groq_key or os.getenv("GROQ_API_KEY")
    
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    
    allowed_exts = ['.pdf', '.docx', '.txt']
    if ext not in allowed_exts:
        return jsonify({"success": False, "error": "Unsupported file format. Please upload PDF, DOCX, or TXT."}), 400
        
    try:
        file_bytes = file.read()
        from resume_parser import extract_text_from_pdf, extract_text_from_docx, extract_text_from_txt, parse_resume_text
        
        if ext == '.pdf':
            text = extract_text_from_pdf(file_bytes)
        elif ext == '.docx':
            text = extract_text_from_docx(file_bytes)
        else: # .txt
            text = extract_text_from_txt(file_bytes)
            
        if not text or not text.strip():
            return jsonify({"success": False, "error": "Unable to extract text from the file."}), 400
            
        parsed_profile = parse_resume_text(text, api_key=active_api_key)
        
        target_career = request.form.get('target_career', '').strip()
        
        # Determine interests (auto-extracted from resume with fallback to target career or Software Engineering)
        interests = parsed_profile.get("interests", "").strip()
        if not interests:
            interests = target_career if target_career else "Software Engineering"

        # Determine recommended career and match score to save the resume profile record
        user_skills = parsed_profile.get("skills", [])
        if target_career:
            if active_api_key:
                recommended_career = target_career
                match_score = calculate_compatibility_score_with_groq(user_skills, target_career, active_api_key)
            else:
                recommended_career, match_score = calculate_compatibility_score(user_skills, target_career)
        else:
            if active_api_key:
                recommended_career, match_score = recommend_career_with_groq(user_skills, interests, active_api_key)
            else:
                recommended_career, match_score = recommend_career(user_skills)
                
        # Validate critical fields
        name = parsed_profile.get("name", "").strip()
        email = parsed_profile.get("email", "").strip()
        if not name or not NAME_REGEX.match(name):
            name = "Resume Candidate"
        if not email or not EMAIL_REGEX.match(email):
            email = "resume_applicant@example.com"
            
        # Save resume details in DB under type 'resume'
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
            session.permanent = True
            
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO user_profiles (session_id, name, email, skills_text, interests, extracted_skills, recommended_career, match_score, submission_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session['session_id'],
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
        resume_profile_id = cursor.lastrowid
        conn.close()
            
        return jsonify({
            "success": True,
            "resume_profile_id": resume_profile_id,
            "name": name,
            "email": email,
            "skills_text": text.strip(), # Populate full text in textarea
            "interests": interests,
            "target_career": target_career
        })
    except Exception as e:
        print(f"Error in API parse resume: {e}")
        return jsonify({"success": False, "error": f"An unexpected error occurred during parsing: {str(e)}"}), 500


@app.route('/upload-resume', methods=['POST'])
def upload_resume():
    """Handle resume file uploads, parse text, extract details, run recommenders, save, and render results."""
    if 'resume_file' not in request.files:
        flash("No resume file uploaded.", "error")
        return redirect(url_for('index'))
        
    file = request.files['resume_file']
    if file.filename == '':
        flash("No selected resume file.", "error")
        return redirect(url_for('index'))
        
    custom_groq_key = request.form.get('custom_groq_key', '').strip()
    active_api_key = custom_groq_key or os.getenv("GROQ_API_KEY")
    target_career = request.form.get('target_career', '').strip()
    
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    
    allowed_exts = ['.pdf', '.docx', '.txt']
    if ext not in allowed_exts:
        flash("Unsupported file format. Please upload a PDF (.pdf), Word (.docx), or Text (.txt) file.", "error")
        return redirect(url_for('index'))
        
    try:
        # Read file contents into bytes
        file_bytes = file.read()
        
        # 1. Parse text from file based on extension
        from resume_parser import extract_text_from_pdf, extract_text_from_docx, extract_text_from_txt, parse_resume_text
        
        if ext == '.pdf':
            text = extract_text_from_pdf(file_bytes)
        elif ext == '.docx':
            text = extract_text_from_docx(file_bytes)
        else: # .txt
            text = extract_text_from_txt(file_bytes)
            
        if not text or not text.strip():
            flash("Unable to extract text from the uploaded resume. The file may be empty or corrupted.", "error")
            return redirect(url_for('index'))
            
        # 2. Parse candidate details
        parsed_profile = parse_resume_text(text, api_key=active_api_key)
        
        name = parsed_profile.get("name", "").strip()
        email = parsed_profile.get("email", "").strip()
        user_skills = parsed_profile.get("skills", [])
        
        # Determine interests (auto-extracted from resume with fallback to target career or Software Engineering)
        interests = parsed_profile.get("interests", "").strip()
        if not interests:
            interests = target_career if target_career else "Software Engineering"
        
        # Validate critical fields
        # If name is not valid or empty, set default/placeholder but let it pass
        if not name or not NAME_REGEX.match(name):
            name = "Resume Candidate"
            
        if not email or not EMAIL_REGEX.match(email):
            email = "resume_applicant@example.com"
            
        if not user_skills:
            flash("No skills could be identified in your resume. Please try entering them manually.", "error")
            return redirect(url_for('index'))
            
        # 3. Match Career: Align against target_career if provided, else predict recommended career
        if target_career:
            if active_api_key:
                recommended_career = target_career
                match_score = calculate_compatibility_score_with_groq(user_skills, target_career, active_api_key)
            else:
                recommended_career, match_score = calculate_compatibility_score(user_skills, target_career)
        else:
            if active_api_key:
                recommended_career, match_score = recommend_career_with_groq(user_skills, interests, active_api_key)
            else:
                recommended_career, match_score = recommend_career(user_skills)
            
        # 4. Save profile to SQLite database with session_id
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
            session.permanent = True
            
        # Save the full extracted text in skills_text to display as raw resume content
        skills_text = text.strip()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO user_profiles (session_id, name, email, skills_text, interests, extracted_skills, recommended_career, match_score, submission_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session['session_id'],
            name,
            email,
            skills_text,
            interests,
            json.dumps(user_skills),
            recommended_career,
            match_score,
            'resume'
        ))
        conn.commit()
        profile_id = cursor.lastrowid
        # Fetch exact resume row for rendering
        cursor.execute('SELECT * FROM user_profiles WHERE id = ?', (profile_id,))
        resume_row = cursor.fetchone()
        manual_row = None
        conn.close()
        
        if custom_groq_key:
            session['custom_groq_key'] = custom_groq_key
            
        flash("Resume processed and profile recommendation map generated successfully!", "success")
        
        manual_results = get_profile_results(manual_row, active_api_key)
        resume_results = get_profile_results(resume_row, active_api_key)
        
        return render_template(
            'result.html',
            manual_results=manual_results,
            resume_results=resume_results,
            active_tab='resume',
            using_chromadb=advisor.use_chroma,
            using_nlp=SPACY_AVAILABLE
        )
        
    except Exception as e:
        print(f"Error processing resume upload: {e}")
        flash("An unexpected error occurred while processing your resume.", "error")
        return redirect(url_for('index'))


@app.route('/profile/<int:profile_id>', methods=['GET'])
def view_profile(profile_id):
    """Load and render the recommendation dashboard for a saved profile belonging to the current session."""
    try:
        session_id = session.get('session_id')
        if not session_id:
            flash("Unauthorized. Session not found.", "error")
            return redirect(url_for('index'))
            
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM user_profiles WHERE id = ? AND session_id = ?', (profile_id, session_id))
        row = cursor.fetchone()
            
        if not row:
            conn.close()
            flash("Profile not found or unauthorized.", "error")
            return redirect(url_for('index'))
            
        active_api_key = session.get('custom_groq_key') or os.getenv("GROQ_API_KEY")
        
        # Load both profiles for comparison tabs
        manual_row = None
        resume_row = None
        
        if row['submission_type'] == 'resume':
            resume_row = row
            # Find the manual profile associated with this resume profile
            cursor.execute('''
                SELECT * FROM user_profiles 
                WHERE session_id = ? AND associated_resume_id = ? AND submission_type = 'manual'
                LIMIT 1
            ''', (session_id, row['id']))
            manual_row = cursor.fetchone()
            active_tab = 'resume'
        else:
            manual_row = row
            # Find the resume profile associated with this manual profile
            associated_resume_id = row['associated_resume_id'] if 'associated_resume_id' in row.keys() else None
            if associated_resume_id:
                cursor.execute('''
                    SELECT * FROM user_profiles 
                    WHERE id = ? AND session_id = ? AND submission_type = 'resume'
                ''', (associated_resume_id, session_id))
                resume_row = cursor.fetchone()
            active_tab = 'manual'
            
        conn.close()
            
        manual_results = get_profile_results(manual_row, active_api_key)
        resume_results = get_profile_results(resume_row, active_api_key)
        
        return render_template(
            'result.html',
            manual_results=manual_results,
            resume_results=resume_results,
            active_tab=active_tab,
            using_chromadb=advisor.use_chroma,
            using_nlp=SPACY_AVAILABLE
        )
    except Exception as e:
        print(f"Error loading saved profile: {e}")
        flash("Failed to load saved profile recommendation map.", "error")
        return redirect(url_for('index'))


@app.route('/delete-profile/<int:profile_id>', methods=['POST'])
def delete_profile(profile_id):
    """Delete a saved profile belonging to the current session."""
    try:
        session_id = session.get('session_id')
        if not session_id:
            flash("Unauthorized. Session not found.", "error")
            return redirect(url_for('index'))
            
        conn = get_db_connection()
        cursor = conn.cursor()
        # Fetch target row to check for associations
        cursor.execute('SELECT * FROM user_profiles WHERE id = ? AND session_id = ?', (profile_id, session_id))
        row = cursor.fetchone()
        
        if row:
            associated_resume_id = row['associated_resume_id'] if 'associated_resume_id' in row.keys() else None
            
            # Delete selected row
            conn.execute('DELETE FROM user_profiles WHERE id = ? AND session_id = ?', (profile_id, session_id))
            
            # Delete associated resume if this is a manual profile
            if associated_resume_id:
                conn.execute('DELETE FROM user_profiles WHERE id = ? AND session_id = ?', (associated_resume_id, session_id))
                
            # Delete associated manual profile if this is a resume profile
            if row['submission_type'] == 'resume':
                conn.execute('DELETE FROM user_profiles WHERE associated_resume_id = ? AND session_id = ?', (profile_id, session_id))
                
        conn.commit()
        conn.close()
        flash("Profile deleted successfully.", "success")
    except Exception as e:
        print(f"Error deleting profile: {e}")
        flash("Failed to delete profile.", "error")
    return redirect(url_for('index'))



@app.route('/api/validate', methods=['POST'])
def api_validate():
    """Endpoint for asynchronous real-time client-side regex validation."""
    data = request.get_json() or {}
    field = data.get('field', '')
    value = data.get('value', '').strip()
    
    is_valid = False
    message = ""
    
    if field == 'name':
        is_valid = bool(NAME_REGEX.match(value))
        message = "Valid name." if is_valid else "Name must contain only letters and spaces (2-50 chars)."
    elif field == 'email':
        is_valid = bool(EMAIL_REGEX.match(value))
        message = "Valid email." if is_valid else "Please enter a valid email address."
        
    return jsonify({
        "valid": is_valid,
        "message": message
    })


if __name__ == '__main__':
    # Run server locally on port 5000 in debug mode
    print("Starting Career & Educational Advisor Flask Server...")
    app.run(host='127.0.0.1', port=5000, debug=True)
