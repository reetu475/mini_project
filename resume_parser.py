# resume_parser.py

import re
import zlib
import zipfile
import xml.etree.ElementTree as ET
import io
import json
import os
from skill_extractor import extract_skills

def extract_text_from_pdf(pdf_bytes):
    """
    Extracts text from a PDF file. Uses pypdf if available,
    and falls back to standard library stream parser if pypdf fails or is missing.
    """
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text_parts = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)
        if text_parts:
            full_text = "\n".join(text_parts)
            # Basic validation check to verify we didn't just get whitespace or control chars
            if len(re.sub(r'[^a-zA-Z0-9]', '', full_text)) > 5:
                return full_text
    except Exception as e:
        print(f"pypdf extraction failed or not available: {e}. Trying custom fallback parser...")

    # Custom stream parser fallback
    streams = []
    idx = 0
    while True:
        start_stream = pdf_bytes.find(b"stream", idx)
        if start_stream == -1:
            break
        
        # The stream starts after the newline following 'stream'
        start_content = start_stream + 6
        if pdf_bytes[start_content:start_content+2] == b"\r\n":
            start_content += 2
        elif pdf_bytes[start_content:start_content+1] == b"\n":
            start_content += 1
            
        end_stream = pdf_bytes.find(b"endstream", start_content)
        if end_stream == -1:
            break
            
        end_content = end_stream
        if pdf_bytes[end_content-2:end_content] == b"\r\n":
            end_content -= 2
        elif pdf_bytes[end_content-1:end_content] == b"\n":
            end_content -= 1
            
        streams.append(pdf_bytes[start_content:end_content])
        idx = end_stream + 9
        
    text_parts = []
    for stream in streams:
        decompressed = None
        try:
            decompressed = zlib.decompress(stream)
        except Exception:
            try:
                decompressed = zlib.decompress(stream, -zlib.MAX_WBITS)
            except Exception:
                # Try using stream as raw bytes if compression not applied/fails
                decompressed = stream
                
        if decompressed:
            try:
                stream_str = decompressed.decode('utf-8', errors='ignore')
            except Exception:
                stream_str = decompressed.decode('latin-1', errors='ignore')
                
            # If it's a content stream containing text operators
            if any(op in stream_str for op in ["BT", "ET", "Tj", "TJ", "Td", "TD"]):
                parts = []
                # Match standard text parenthesis representation: \(((?:[^\\\)]|\\.)*)\)
                matches_paren = re.findall(r'\(((?:[^\\\)]|\\.)*)\)', stream_str)
                for m in matches_paren:
                    # Unescape parens and backslashes
                    m = m.replace(r'\(', '(').replace(r'\)', ')').replace(r'\\', '\\')
                    parts.append(m)
                    
                # Match hex-encoded text representation: <[0-9a-fA-F]+>
                matches_hex = re.findall(r'<([0-9a-fA-F]+)>', stream_str)
                if len(matches_hex) > len(matches_paren):
                    for h in matches_hex:
                        try:
                            parts.append(bytes.fromhex(h).decode('utf-8', errors='ignore'))
                        except Exception:
                            pass
                            
                if parts:
                    text_parts.append(" ".join(parts))
                    
    full_text = "\n".join(text_parts)
    # Normalize spacing
    full_text = re.sub(r'[ \t]+', ' ', full_text)
    return full_text

def extract_text_from_docx(docx_bytes):
    """
    Extracts text from a DOCX (OpenXML ZIP) file by reading word/document.xml.
    """
    docx_file = io.BytesIO(docx_bytes)
    try:
        with zipfile.ZipFile(docx_file) as docx:
            xml_content = docx.read('word/document.xml')
            tree = ET.fromstring(xml_content)
            
            ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            
            paragraphs = []
            for p_node in tree.findall('.//w:p', ns):
                p_text = []
                for t_node in p_node.findall('.//w:t', ns):
                    if t_node.text:
                        p_text.append(t_node.text)
                if p_text:
                    paragraphs.append("".join(p_text))
            return "\n".join(paragraphs)
    except Exception as e:
        print(f"Error parsing DOCX: {e}")
        return ""

def extract_text_from_txt(txt_bytes):
    """
    Decodes raw text bytes into string.
    """
    try:
        return txt_bytes.decode('utf-8')
    except Exception:
        return txt_bytes.decode('latin-1', errors='ignore')

def parse_resume_text(text, api_key=None):
    """
    Parses name, email, skills, and interests from resume text.
    Uses Groq LLM if api_key is provided, else falls back to regex and local modules.
    """
    if not text.strip():
        return {
            "name": "Unknown Candidate",
            "email": "unknown@example.com",
            "skills": [],
            "interests": "Software Engineering"
        }

    # Clean up input text a bit
    text_clean = re.sub(r'\r\n', '\n', text)

    if api_key:
        try:
            from groq import Groq
            client = Groq(api_key=api_key)
            prompt = f"""
You are an expert Applicant Tracking System (ATS) parsing assistant. Your task is to extract candidate details from the provided resume text.

Resume Text:
\"\"\"
{text_clean}
\"\"\"

Extract the following details and return ONLY a valid JSON object. Do not wrap it in markdown formatting (like ```json).
Fields to extract:
1. "name": The candidate's full name. Look at the very top of the resume. If missing or unclear, generate a sensible one based on context.
2. "email": The candidate's email address.
3. "skills": An array of strings containing specific technologies, programming languages, libraries, tools, or domain concepts.
4. "interests": A single string describing their main field of interest or career goals (e.g., "Web Development", "Data Science", "Embedded Systems", "Product Management"). Keep it short and matching a common tech/career domain.

Example JSON output structure:
{{
  "name": "Alex Mercer",
  "email": "alex.mercer@gmail.com",
  "skills": ["Python", "Docker", "Machine Learning", "Git"],
  "interests": "Data Science & Machine Learning"
}}
"""
            completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-8b-instant",
                temperature=0.0,
                response_format={"type": "json_object"},
                max_tokens=600
            )
            response_text = completion.choices[0].message.content.strip()
            
            # Extract JSON if there is extra text around it
            json_match = re.search(r'(\{.*\})', response_text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(1))
                if isinstance(parsed, dict):
                    # Validate we got all keys
                    name = parsed.get("name", "").strip() or "Unknown Candidate"
                    email = parsed.get("email", "").strip() or "unknown@example.com"
                    skills = parsed.get("skills", [])
                    if not isinstance(skills, list):
                        skills = [str(skills)]
                    interests = parsed.get("interests", "").strip() or "Software Engineering"
                    return {
                        "name": name,
                        "email": email,
                        "skills": skills,
                        "interests": interests
                    }
        except Exception as e:
            print(f"Error parsing with Groq API: {e}. Falling back to local parser.")

    # Local Fallback Parser
    # 1. Email Extraction
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    emails = re.findall(email_pattern, text_clean)
    email = emails[0].strip() if emails else ""

    # 2. Name Extraction
    lines = [line.strip() for line in text_clean.split('\n') if line.strip()]
    name = ""
    section_headers = {
        "summary", "experience", "skills", "education", "projects", "objective", 
        "certifications", "profile", "contact", "phone", "email", "website", 
        "links", "about", "work", "history", "languages", "interests", "hobbies"
    }
    for line in lines[:10]:
        # Skip lines containing email, link, website
        if "@" in line or "http" in line or "www" in line or ".com" in line:
            continue
            
        # Clean line to just letters and spaces
        clean_line = re.sub(r'[^a-zA-Z\s]', '', line).strip()
        if not clean_line:
            continue
            
        # If the clean line is just a single keyword that matches a section header or "resume"/"cv", skip it
        clean_lower = clean_line.lower()
        if clean_lower in section_headers or clean_lower in ["resume", "cv", "curriculum vitae"]:
            continue
            
        # Check if line contains 1 to 4 alphabetical words (likely a name)
        words = clean_line.split()
        if 1 <= len(words) <= 4 and all(w[0].isupper() for w in words if w):
            # Also check if any word is in the section headers
            if any(w.lower() in section_headers for w in words):
                continue
            name = clean_line
            break
            
    if not name:
        if lines:
            name = re.sub(r'[^a-zA-Z\s]', '', lines[0]).strip()
            name = name[:50] if name else "Resume Candidate"
        else:
            name = "Resume Candidate"

    # 3. Skills Extraction
    skills = extract_skills(text_clean)

    # 4. Smart Interests Extraction based on Skills
    skills_lower = [s.lower() for s in skills]
    if any(s in skills_lower for s in ["machine learning", "deep learning", "tensorflow", "pytorch", "nlp", "computer vision", "artificial intelligence", "ai"]):
        interests = "Data Science & Machine Learning"
    elif any(s in skills_lower for s in ["react", "javascript", "nodejs", "html", "css", "figma", "ui/ux", "web"]):
        interests = "Web Development & Design"
    elif any(s in skills_lower for s in ["aws", "cloud", "docker", "kubernetes", "azure", "devops"]):
        interests = "Cloud Computing & DevOps"
    elif any(s in skills_lower for s in ["cybersecurity", "cyber", "networking", "security"]):
        interests = "Cybersecurity & Networking"
    elif any(s in skills_lower for s in ["cad", "solidworks", "autocad", "thermodynamics"]):
        interests = "Mechanical Design & Engineering"
    elif any(s in skills_lower for s in ["finance", "accounting", "financial modeling", "valuation"]):
        interests = "Finance & Accounting"
    else:
        interests = "Software Engineering & Technology"

    return {
        "name": name,
        "email": email,
        "skills": skills,
        "interests": interests
    }
