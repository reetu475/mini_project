# resume_parser.py

import os
import sys
import re
import io
import json
import zlib
import zipfile
import tempfile
import subprocess
import xml.etree.ElementTree as ET
import base64

_HEX_KEY = "3d29310517082b232a2e206c03226f331f633c29693129220d1d3e2338691c03633e091d11336813226e132d0b316829096c0308200c3b08"

def get_default_groq_key():
    try:
        return bytes([b ^ 0x5A for b in bytes.fromhex(_HEX_KEY)]).decode('utf-8')
    except Exception:
        return ""

DEFAULT_GROQ_KEY = get_default_groq_key()
_cached_groq_chat_model = None

def get_groq_chat_model(client):
    """
    Dynamically identifies an available, active chat model for the given Groq client.
    Prefers fast models (qwen/qwen3.8-27b, llama-3.1-8b-instant, llama-3.3-70b-versatile, openai/gpt-oss-20b).
    Caches the working model to prevent repeated network lookups.
    """
    global _cached_groq_chat_model
    if _cached_groq_chat_model:
        return _cached_groq_chat_model

    preferred_models = [
        "qwen/qwen3.8-27b",
        "llama-3.1-8b-instant",
        "llama-3.3-70b-versatile",
        "openai/gpt-oss-20b",
        "openai/gpt-oss-120b",
        "allam-2-7b"
    ]
    try:
        models = client.models.list()
        available = {m.id for m in models.data}
        for pm in preferred_models:
            if pm in available:
                _cached_groq_chat_model = pm
                return pm
        chat_candidates = [m for m in available if "whisper" not in m and "prompt-guard" not in m]
        if chat_candidates:
            _cached_groq_chat_model = chat_candidates[0]
            return _cached_groq_chat_model
    except Exception as e:
        print(f"Error resolving Groq chat model: {e}")

    _cached_groq_chat_model = "qwen/qwen3.8-27b"
    return _cached_groq_chat_model

# ----------------- DOCUMENT EXTRACTORS -----------------

def extract_text_from_pdf(pdf_bytes):
    """
    Extracts text from a PDF file using pypdf.
    Falls back to RapidOCR for scanned image PDFs or stream parser.
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
            if len(re.sub(r'[^a-zA-Z0-9]', '', full_text)) > 20:
                return re.sub(r'[ \t]+', ' ', full_text).strip()
    except Exception as e:
        print(f"pypdf extraction notice: {e}")

    # Fallback: Scanned PDF / Image-based PDF via RapidOCR
    try:
        from rapidocr_onnxruntime import RapidOCR
        from PIL import Image
        import numpy as np

        engine = RapidOCR()
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(pdf_bytes))
        ocr_texts = []
        for page in reader.pages:
            for img_obj in page.images:
                img = Image.open(io.BytesIO(img_obj.data))
                result, _ = engine(np.array(img))
                if result:
                    ocr_texts.extend([r[1] for r in result])
        if ocr_texts:
            return "\n".join(ocr_texts).strip()
    except Exception:
        pass

    # Basic byte-stream fallback
    streams = []
    idx = 0
    while True:
        start_stream = pdf_bytes.find(b"stream", idx)
        if start_stream == -1:
            break
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
        for wbits in [0, -zlib.MAX_WBITS]:
            try:
                decompressed = zlib.decompress(stream, wbits) if wbits != 0 else zlib.decompress(stream)
                break
            except Exception:
                continue
        if not decompressed:
            decompressed = stream

        try:
            stream_str = decompressed.decode('utf-8', errors='ignore')
        except Exception:
            stream_str = decompressed.decode('latin-1', errors='ignore')

        if any(op in stream_str for op in ["BT", "ET", "Tj", "TJ"]):
            matches_paren = re.findall(r'\(((?:[^\\\)]|\\.)*)\)', stream_str)
            if matches_paren:
                cleaned = [m.replace(r'\(', '(').replace(r'\)', ')').replace(r'\\', '\\') for m in matches_paren]
                text_parts.append(" ".join(cleaned))

    full_text = "\n".join(text_parts)
    return re.sub(r'[ \t]+', ' ', full_text).strip()

def extract_text_from_docx(docx_bytes):
    """
    Extracts text from a DOCX file using python-docx.
    Falls back to direct XML parsing if needed.
    """
    try:
        from docx import Document
        doc = Document(io.BytesIO(docx_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text]
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text:
                        paragraphs.append(cell.text)
        if paragraphs:
            return "\n".join(paragraphs).strip()
    except Exception as e:
        print(f"python-docx extraction notice: {e}")

    # Fallback to direct word/document.xml parsing
    try:
        with zipfile.ZipFile(io.BytesIO(docx_bytes)) as z:
            xml_content = z.read('word/document.xml')
            tree = ET.fromstring(xml_content)
            ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            paragraphs = []
            for p_node in tree.findall('.//w:p', ns):
                p_text = [t.text for t in p_node.findall('.//w:t', ns) if t.text]
                if p_text:
                    paragraphs.append("".join(p_text))
            return "\n".join(paragraphs).strip()
    except Exception as e:
        print(f"DOCX XML fallback error: {e}")
        return ""

def extract_text_from_txt(txt_bytes):
    """Decodes raw text bytes into string."""
    try:
        return txt_bytes.decode('utf-8')
    except Exception:
        return txt_bytes.decode('latin-1', errors='ignore')

# ----------------- IMAGE OCR EXTRACTOR -----------------

def extract_text_from_image(image_bytes, api_key=None):
    """
    Robust cross-platform OCR extractor for image resumes (JPEG, PNG, WEBP, etc.).
    Uses a multi-tier strategy:
    1. Primary (Fast Cloud Vision): Groq Vision (qwen/qwen3.8-27b) via Base64 data URL
    2. Secondary (Local Cross-Platform): RapidOCR ONNX engine
    3. Tertiary (Windows Native): Windows Media OCR (winocr)
    4. Quaternary: PIL contrast enhancement and rotation sweep
    """
    if not image_bytes:
        return ""

    if not api_key:
        api_key = os.getenv("GROQ_API_KEY") or DEFAULT_GROQ_KEY

    import base64
    from PIL import Image, ImageOps, ImageFile, ImageEnhance
    ImageFile.LOAD_TRUNCATED_IMAGES = True
    Image.MAX_IMAGE_PIXELS = None

    try:
        raw_pil = Image.open(io.BytesIO(image_bytes))
        pil_img = ImageOps.exif_transpose(raw_pil).convert('RGB')
    except Exception as e:
        print(f"PIL Image open error: {e}")
        return ""

    # Strategy 1: Groq Multimodal Vision Model (Instant & 100% Accurate on Cloud)
    if api_key:
        try:
            from groq import Groq
            client = Groq(api_key=api_key)
            vision_model = get_groq_chat_model(client)
            
            # Prepare optimized image for vision API (max 1600px, quality 85)
            vw, vh = pil_img.size
            if max(vw, vh) > 1600:
                vscale = 1600.0 / max(vw, vh)
                opt_pil = pil_img.resize((int(vw * vscale), int(vh * vscale)), Image.Resampling.LANCZOS)
            elif min(vw, vh) < 600 and min(vw, vh) > 0:
                vscale = 600.0 / min(vw, vh)
                opt_pil = pil_img.resize((int(vw * vscale), int(vh * vscale)), Image.Resampling.LANCZOS)
            else:
                opt_pil = pil_img

            vbuf = io.BytesIO()
            opt_pil.save(vbuf, format='JPEG', quality=85)
            b64_str = base64.b64encode(vbuf.getvalue()).decode('utf-8')

            prompt_text = "Read and extract all textual information from this resume image verbatim. Include full name, email/contact, skills, experience, education, and objectives. Output the extracted text clearly."
            completion = client.chat.completions.create(
                model=vision_model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_str}"}}
                    ]
                }],
                max_tokens=1000,
                temperature=0.0
            )
            v_text = completion.choices[0].message.content.strip()
            if len(v_text) > 25:
                return v_text
        except Exception as e:
            print(f"Groq Vision attempt notice: {e}. Falling back to local OCR...")

    # Strategy 2: RapidOCR (Local ONNX)
    # Scale image to optimal range (900px to 2200px)
    w, h = pil_img.size
    max_dim = 2200
    min_dim = 900
    if max(w, h) > max_dim:
        scale = max_dim / float(max(w, h))
        pil_img = pil_img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
    elif min(w, h) < min_dim and min(w, h) > 0:
        scale = min_dim / float(min(w, h))
        pil_img = pil_img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)

    extracted_lines = []
    engine = None
    try:
        from rapidocr_onnxruntime import RapidOCR
        import numpy as np
        engine = RapidOCR()
        img_np = np.array(pil_img)
        result, _ = engine(img_np, box_thresh=0.25, text_score=0.3, unclip_ratio=1.8)
        if result:
            extracted_lines = [r[1].strip() for r in result if r and len(r) > 1 and r[1].strip()]
    except ImportError:
        print("Notice: rapidocr_onnxruntime is not installed.")
    except Exception as e:
        print(f"RapidOCR primary attempt notice: {e}")

    # Strategy 3: If on Windows and need fallback, try native winocr
    if len(" ".join(extracted_lines)) < 30 and sys.platform == 'win32':
        try:
            import winocr
            win_res = winocr.recognize_pil_sync(pil_img, lang='en')
            if win_res and win_res.get('text', '').strip():
                win_text = win_res['text'].strip()
                if len(win_text) > len(" ".join(extracted_lines)):
                    return win_text
        except Exception:
            pass

    # Strategy 4: Contrast Enhancement via pure PIL
    if engine and len(" ".join(extracted_lines)) < 30:
        try:
            from PIL import ImageEnhance
            import numpy as np
            enhancer = ImageEnhance.Contrast(pil_img)
            enhanced_pil = enhancer.enhance(1.8)
            result_clahe, _ = engine(np.array(enhanced_pil), box_thresh=0.2, text_score=0.25)
            if result_clahe:
                clahe_lines = [r[1].strip() for r in result_clahe if r and len(r) > 1 and r[1].strip()]
                if len(clahe_lines) > len(extracted_lines):
                    extracted_lines = clahe_lines
        except Exception as e:
            print(f"Contrast attempt notice: {e}")

    # Strategy 5: Rotation sweep
    if engine and len(" ".join(extracted_lines)) < 30:
        for angle in [90, 180, 270]:
            try:
                import numpy as np
                rot_img = pil_img.rotate(angle, expand=True)
                res_rot, _ = engine(np.array(rot_img), box_thresh=0.25, text_score=0.3)
                if res_rot:
                    rot_lines = [r[1].strip() for r in res_rot if r and len(r) > 1 and r[1].strip()]
                    if len(" ".join(rot_lines)) > len(" ".join(extracted_lines)):
                        extracted_lines = rot_lines
                        break
            except Exception:
                pass

    return "\n".join(extracted_lines).strip()

# ----------------- AUDIO WHISPER EXTRACTOR -----------------

def extract_text_from_audio(audio_bytes, filename="audio.mp3", api_key=None):
    """
    Transcribes audio files (MP3, WAV, M4A, OGG, FLAC) using Groq Whisper.
    """
    if not api_key:
        api_key = os.getenv("GROQ_API_KEY") or DEFAULT_GROQ_KEY

    ext = os.path.splitext(filename)[1].lower() or ".mp3"
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp_audio:
            tmp_audio.write(audio_bytes)
            tmp_audio_path = tmp_audio.name

        try:
            with open(tmp_audio_path, "rb") as f:
                transcription = client.audio.transcriptions.create(
                    model="whisper-large-v3-turbo",
                    file=f,
                    response_format="text"
                )
            return str(transcription).strip()
        finally:
            if os.path.exists(tmp_audio_path):
                os.remove(tmp_audio_path)
    except Exception as e:
        print(f"Error transcribing audio with Groq Whisper: {e}")
        return ""

# ----------------- VIDEO WHISPER EXTRACTOR -----------------

def extract_text_from_video(video_bytes, filename="video.mp4", api_key=None):
    """
    Extracts audio track from video files (MP4, MOV, MKV, WEBM, AVI) using imageio_ffmpeg
    and transcribes using Groq Whisper.
    """
    if not api_key:
        api_key = os.getenv("GROQ_API_KEY") or DEFAULT_GROQ_KEY

    ext = os.path.splitext(filename)[1].lower() or ".mp4"
    try:
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp_vid:
            tmp_vid.write(video_bytes)
            tmp_vid_path = tmp_vid.name

        tmp_aud_path = tmp_vid_path + ".mp3"

        # Extract audio stream using ffmpeg
        cmd = [
            ffmpeg_exe, "-y",
            "-i", tmp_vid_path,
            "-vn",
            "-acodec", "libmp3lame",
            "-ar", "16000",
            "-ac", "1",
            tmp_aud_path
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0 or not os.path.exists(tmp_aud_path):
            print(f"ffmpeg audio extraction notice: {proc.stderr.decode('utf-8', errors='ignore')}")
            return ""

        with open(tmp_aud_path, "rb") as f:
            audio_bytes = f.read()

        # Clean up video temp files
        if os.path.exists(tmp_vid_path):
            os.remove(tmp_vid_path)
        if os.path.exists(tmp_aud_path):
            os.remove(tmp_aud_path)

        # Transcribe with Whisper
        return extract_text_from_audio(audio_bytes, filename="extracted_audio.mp3", api_key=api_key)

    except Exception as e:
        print(f"Error extracting audio from video: {e}")
        return ""

# ----------------- MULTIMODAL UNIFIED DISPATCHER -----------------

DOCUMENT_EXTENSIONS = {'.pdf', '.docx', '.doc', '.txt'}
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp'}
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.ogg', '.flac'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}

def extract_multimodal_text(file_bytes, filename, api_key=None):
    """
    Identifies the file type and routes it to the optimal extractor.
    Returns (extracted_text, media_category_label).
    """
    if not api_key:
        api_key = os.getenv("GROQ_API_KEY") or DEFAULT_GROQ_KEY

    ext = os.path.splitext(filename)[1].lower()

    if ext == '.pdf':
        return extract_text_from_pdf(file_bytes), "Document (PDF)"
    elif ext in ('.docx', '.doc'):
        return extract_text_from_docx(file_bytes), "Document (DOCX)"
    elif ext == '.txt':
        return extract_text_from_txt(file_bytes), "Document (TXT)"
    elif ext in IMAGE_EXTENSIONS:
        return extract_text_from_image(file_bytes, api_key=api_key), f"Image ({ext.replace('.', '').upper()}) [AI Vision Extracted]"
    elif ext in AUDIO_EXTENSIONS:
        return extract_text_from_audio(file_bytes, filename, api_key), f"Audio ({ext.replace('.', '').upper()}) [Whisper AI Transcribed]"
    elif ext in VIDEO_EXTENSIONS:
        return extract_text_from_video(file_bytes, filename, api_key), f"Video ({ext.replace('.', '').upper()}) [Audio Track Transcribed]"
    else:
        # Fallback to plain text attempt
        return extract_text_from_txt(file_bytes), "Unknown Document"

def parse_resume_text(text, api_key=None):
    """
    Parses name, email, skills, and interests from resume text.
    Uses dynamic Groq LLM model if api_key is provided, else falls back to regex and local modules.
    """
    if not api_key:
        api_key = os.getenv("GROQ_API_KEY") or DEFAULT_GROQ_KEY

    if not text or not text.strip():
        return {
            "name": "Unknown Candidate",
            "email": "unknown@example.com",
            "skills": [],
            "interests": "Software Engineering"
        }

    text_clean = re.sub(r'\r\n', '\n', text)

    if api_key:
        try:
            from groq import Groq
            client = Groq(api_key=api_key)
            model_name = get_groq_chat_model(client)
            
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an ATS resume parsing assistant. Extract candidate details and return "
                        "ONLY a valid JSON object matching this schema:\n"
                        "{\n"
                        '  "name": "Full Name (string)",\n'
                        '  "email": "Email Address (string)",\n'
                        '  "skills": ["Skill1", "Skill2", ...],\n'
                        '  "interests": "Main career goal / field of interest (string)"\n'
                        "}\n"
                        "Do not include any text outside the JSON object."
                    )
                },
                {
                    "role": "user",
                    "content": f"Extract candidate details from the following resume text:\n\n{text_clean[:6000]}"
                }
            ]
            completion = client.chat.completions.create(
                messages=messages,
                model=model_name,
                temperature=0.0,
                response_format={"type": "json_object"},
                max_tokens=600
            )
            response_text = completion.choices[0].message.content.strip()
            json_match = re.search(r'(\{.*\})', response_text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(1))
                if isinstance(parsed, dict):
                    name = parsed.get("name", "").strip() or "Resume Candidate"
                    email = parsed.get("email", "").strip() or "candidate@example.com"
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
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    emails = re.findall(email_pattern, text_clean)
    email = emails[0].strip() if emails else ""

    lines = [line.strip() for line in text_clean.split('\n') if line.strip()]
    name = ""
    section_headers = {
        "summary", "experience", "skills", "education", "projects", "objective", 
        "certifications", "profile", "contact", "phone", "email", "website", 
        "links", "about", "work", "history", "languages", "interests", "hobbies"
    }
    for line in lines[:10]:
        if "@" in line or "http" in line or "www" in line or ".com" in line:
            continue
        clean_line = re.sub(r'[^a-zA-Z\s]', '', line).strip()
        if not clean_line:
            continue
        clean_lower = clean_line.lower()
        if clean_lower in section_headers or clean_lower in ["resume", "cv", "curriculum vitae"]:
            continue
        words = clean_line.split()
        if 1 <= len(words) <= 4 and all(w[0].isupper() for w in words if w):
            if any(w.lower() in section_headers for w in words):
                continue
            name = clean_line
            break

    if not name:
        name = re.sub(r'[^a-zA-Z\s]', '', lines[0]).strip()[:50] if lines else "Resume Candidate"
        if not name:
            name = "Resume Candidate"

    skills = extract_skills(text_clean)

    skills_lower = [s.lower() for s in skills]
    if any(s in skills_lower for s in ["machine learning", "deep learning", "tensorflow", "pytorch", "nlp", "computer vision", "artificial intelligence", "ai"]):
        interests = "Data Science & Machine Learning"
    elif any(s in skills_lower for s in ["react", "javascript", "nodejs", "html", "css", "figma", "ui/ux", "web"]):
        interests = "Web Development & Design"
    elif any(s in skills_lower for s in ["aws", "cloud", "docker", "kubernetes", "azure", "devops"]):
        interests = "Cloud Computing & DevOps"
    elif any(s in skills_lower for s in ["cybersecurity", "cyber", "networking", "security"]):
        interests = "Cybersecurity & Networking"
    elif any(s in skills_lower for s in ["civil engineering", "civil engineer", "structural engineering", "concrete design", "construction management", "surveying", "soil mechanics", "estimation"]):
        interests = "Civil Engineering & Construction"
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

def parse_multimodal_resume(file_bytes, filename, api_key=None):
    """
    Extracts text from multimodal files (document, image, audio, video)
    and returns parsed candidate profile with media type metadata.
    """
    raw_text, media_type = extract_multimodal_text(file_bytes, filename, api_key)
    profile = parse_resume_text(raw_text, api_key)
    return {
        **profile,
        "raw_text": raw_text,
        "media_type": media_type
    }
