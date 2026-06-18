# roadmap_generator.py

import os
import re
from groq import Groq

# Fallback roadmap database
LOCAL_ROADMAPS = {
    "AI Engineer": [
        {"step_number": 1, "title": "Advanced Python & Math Foundations", "duration": "4 Weeks", "details": ["Master linear algebra, calculus, probability, and statistics.", "Deep dive into Python OOP, generators, decorators, and libraries like NumPy."]},
        {"step_number": 2, "title": "Data Manipulation & Machine Learning", "duration": "6 Weeks", "details": ["Learn Pandas, Matplotlib, and Scikit-Learn for data processing and visualization.", "Implement classic classification, regression, and clustering algorithms."]},
        {"step_number": 3, "title": "Deep Learning & Neural Networks", "duration": "6 Weeks", "details": ["Understand neural network architectures (ANNs, CNNs, RNNs).", "Build and train models using TensorFlow or PyTorch framework."]},
        {"step_number": 4, "title": "Natural Language Processing & LLMs", "duration": "4 Weeks", "details": ["Learn text processing, tokenization, word embeddings, and transformer models.", "Fine-tune pretrained LLMs and use vector databases for RAG applications."]}
    ],
    "Data Scientist": [
        {"step_number": 1, "title": "Python & Data Analysis Foundations", "duration": "4 Weeks", "details": ["Learn core Python programming, data structures, and functions.", "Master SQL databases: queries, joins, subqueries, and aggregations.", "Use Pandas and NumPy for exploratory data analysis (EDA)."]},
        {"step_number": 2, "title": "Statistics & Probability", "duration": "3 Weeks", "details": ["Study descriptive and inferential statistics, hypothesis testing, and probability distributions.", "Learn to design A/B testing and analyze experimental data."]},
        {"step_number": 3, "title": "Machine Learning in Practice", "duration": "5 Weeks", "details": ["Learn supervised learning (regression, classification, random forests) and unsupervised learning (K-Means, PCA).", "Use Scikit-Learn to build, evaluate, and tune machine learning models."]},
        {"step_number": 4, "title": "Data Visualization & Communication", "duration": "3 Weeks", "details": ["Build interactive dashboards in Power BI or Tableau.", "Communicate technical results to business stakeholders using Jupyter Notebooks."]}
    ],
    "Data Analyst": [
        {"step_number": 1, "title": "Excel Foundations & Business Math", "duration": "3 Weeks", "details": ["Master Excel features: Pivot Tables, VLOOKUP, INDEX-MATCH, and data cleaning.", "Understand business metrics, basic algebra, and data summaries."]},
        {"step_number": 2, "title": "SQL Database Querying", "duration": "4 Weeks", "details": ["Learn basic to intermediate SQL (SELECT, WHERE, JOIN, GROUP BY, HAVING).", "Practice writing queries on relational databases (MySQL, PostgreSQL)."]},
        {"step_number": 3, "title": "BI Tools & Dashboards", "duration": "4 Weeks", "details": ["Master Power BI or Tableau.", "Connect to data sources, build data models, and design interactive, professional reports."]},
        {"step_number": 4, "title": "Python for Analytics", "duration": "3 Weeks", "details": ["Learn Python basics, focusing on Pandas and Matplotlib/Seaborn.", "Automate data cleaning and report generation."]}
    ],
    "ML Engineer": [
        {"step_number": 1, "title": "Software Engineering & Python Mastery", "duration": "4 Weeks", "details": ["Master Python data structures, algorithms, and object-oriented programming.", "Learn version control using Git and write clean, testable code."]},
        {"step_number": 2, "title": "Core Machine Learning", "duration": "6 Weeks", "details": ["Learn classic ML algorithms (SVMs, Decision Trees, ensemble methods).", "Implement pipelines, handle missing data, and tune hyperparameters using Scikit-Learn."]},
        {"step_number": 3, "title": "Deep Learning & Frameworks", "duration": "6 Weeks", "details": ["Build neural networks using PyTorch or TensorFlow.", "Implement convolutional neural networks (CNNs) and recurrent neural networks (RNNs)."]},
        {"step_number": 4, "title": "MLOps & Deployment", "duration": "4 Weeks", "details": ["Deploy ML models as APIs using Flask, FastAPI, or Docker.", "Learn about model tracking, CI/CD, and basic cloud integration."]}
    ],
    "Software Engineer": [
        {"step_number": 1, "title": "Programming & OOP Concepts", "duration": "4 Weeks", "details": ["Learn programming fundamentals in Python, Java, or C++.", "Master Object-Oriented Programming (OOP): classes, inheritance, encapsulation, and polymorphism."]},
        {"step_number": 2, "title": "Data Structures & Algorithms (DSA)", "duration": "6 Weeks", "details": ["Study arrays, linked lists, stacks, queues, trees, and graphs.", "Learn searching, sorting, and algorithmic paradigms like recursion and dynamic programming.", "Practice solving coding problems (LeetCode style)."]},
        {"step_number": 3, "title": "Databases & Web Technologies", "duration": "4 Weeks", "details": ["Learn relational database concepts, SQL queries, and normalization (DBMS).", "Understand basic web architectures: HTTP, REST APIs, frontend-backend flow, and MVC pattern."]},
        {"step_number": 4, "title": "Software Development Life Cycle & Tools", "duration": "4 Weeks", "details": ["Learn Git, testing (unit tests), and CI/CD pipelines.", "Build a full stack portfolio project using Flask or Java Spring Boot."]}
    ],
    "Financial Analyst": [
        {"step_number": 1, "title": "Accounting & Finance Principles", "duration": "4 Weeks", "details": ["Understand core financial statements: Income Statement, Balance Sheet, Cash Flow.", "Learn standard bookkeeping, cost accounting, and corporate finance concepts."]},
        {"step_number": 2, "title": "Excel Mastery & Reporting", "duration": "4 Weeks", "details": ["Master financial calculations, pivot tables, lookup functions, and data cleansing in Excel.", "Build clean, professional financial models and forecasting templates."]},
        {"step_number": 3, "title": "Corporate Valuation & Modeling", "duration": "5 Weeks", "details": ["Learn Discounted Cash Flow (DCF) models, Comparable Companies Analysis (CCA).", "Understand mergers & acquisitions (M&A) basics and investment portfolio metrics."]},
        {"step_number": 4, "title": "Business Intelligence & Strategy", "duration": "3 Weeks", "details": ["Build financial dashboards using Power BI or Excel Charts.", "Present investment reports and key performance indicators (KPIs) to leadership."]}
    ],
    "Digital Marketer": [
        {"step_number": 1, "title": "Marketing Strategy & Audience Research", "duration": "3 Weeks", "details": ["Learn core marketing funnels, customer personas, and market research techniques.", "Master copywriting basics and brand voice positioning."]},
        {"step_number": 2, "title": "SEO & Content Marketing", "duration": "4 Weeks", "details": ["Learn keyword research, on-page, off-page, and technical Search Engine Optimization (SEO).", "Develop content calendars and distribute search-optimized blogs and newsletters."]},
        {"step_number": 3, "title": "Paid Advertising & Analytics", "duration": "5 Weeks", "details": ["Configure and launch Pay-Per-Click (PPC) campaigns on Google Ads and social media platforms.", "Track web traffic, conversion rates, and ROI using Google Analytics."]},
        {"step_number": 4, "title": "Social Media & Retention Campaigns", "duration": "4 Weeks", "details": ["Build communities on LinkedIn, Instagram, and YouTube.", "Launch email automation campaigns to nurture leads and retain customers."]}
    ],
    "UI/UX Designer": [
        {"step_number": 1, "title": "UX Research & Wireframing", "duration": "4 Weeks", "details": ["Conduct user interviews, build user personas, and map user journeys.", "Draw low-fidelity sketches and build structured wireframes for web/mobile layouts."]},
        {"step_number": 2, "title": "Figma Mastery & UI Design", "duration": "4 Weeks", "details": ["Master Figma grids, auto-layout, components, variants, and design systems.", "Apply color theory, typography, spacing scales, and visual hierarchy."]},
        {"step_number": 3, "title": "Prototyping & User Testing", "duration": "4 Weeks", "details": ["Build high-fidelity interactive prototypes with smart animations in Figma.", "Conduct usability testing sessions, collect feedback, and iterate on visual designs."]},
        {"step_number": 4, "title": "Portfolio Development & Handoff", "duration": "4 Weeks", "details": ["Publish 3 detailed case studies explaining your design process.", "Configure developer handoff files, assets exports, and Zeplin/Figma specifications."]}
    ],
    "HR Specialist": [
        {"step_number": 1, "title": "HR Principles & Labor Compliance", "duration": "4 Weeks", "details": ["Learn human resource management theories and labor regulations.", "Understand corporate organization, payroll administration, and policy writing."]},
        {"step_number": 2, "title": "Recruitment & Talent Acquisition", "duration": "4 Weeks", "details": ["Master candidate sourcing, writing job descriptions, and screening resumes.", "Conduct behavioral interviews and manage Applicant Tracking Systems (ATS)."]},
        {"step_number": 3, "title": "Onboarding & Employee Relations", "duration": "4 Weeks", "details": ["Design onboarding journeys and manage employee feedback surveys.", "Mediate workplace disputes and implement employee wellness programs."]},
        {"step_number": 4, "title": "HR Analytics & Strategic Planning", "duration": "4 Weeks", "details": ["Analyze turnover rates, hiring speed, and training effectiveness metrics.", "Develop performance management frameworks and strategic talent planning."]}
    ],
    "Mechanical Engineer": [
        {"step_number": 1, "title": "Engineering Physics & Thermodynamics", "duration": "4 Weeks", "details": ["Review statics, dynamics, material strength, and fluid mechanics.", "Master laws of thermodynamics, heat transfer, and mechanical systems analysis."]},
        {"step_number": 2, "title": "CAD Drafting & SolidWorks 3D Modeling", "duration": "5 Weeks", "details": ["Learn 2D drafting with AutoCAD (technical drawing standards).", "Build 3D models, assemblies, and detailed engineering drawings in SolidWorks."]},
        {"step_number": 3, "title": "Finite Element Analysis (FEA) & CFD", "duration": "5 Weeks", "details": ["Perform stress, thermal, and vibration simulations in SolidWorks Simulation or ANSYS.", "Run Computational Fluid Dynamics (CFD) for flow and pressure drops."]},
        {"step_number": 4, "title": "Manufacturing & Product Design", "duration": "4 Weeks", "details": ["Design for Manufacturing (DFM) and Design for Assembly (DFA) guidelines.", "Understand CNC machining, 3D printing, sheet metal fabrication, and prototyping."]}
    ],
    "Embedded Systems Engineer": [
        {"step_number": 1, "title": "Circuit Design & C Programming", "duration": "4 Weeks", "details": ["Master digital electronics, schematic capture, and circuit design basics.", "Learn embedded C programming (pointers, registers, bitwise operations)."]},
        {"step_number": 2, "title": "Microcontrollers & Hardware Interfacing", "duration": "4 Weeks", "details": ["Study ARM Cortex, AVR, or PIC microcontroller architectures.", "Interface peripherals: GPIO, ADC, PWM, Timers, and interrupts."]},
        {"step_number": 3, "title": "Communication Protocols & IoT", "duration": "4 Weeks", "details": ["Implement UART, SPI, I2C, and CAN bus communication protocols.", "Connect sensors to the cloud using Wi-Fi/Bluetooth modules (ESP32/Raspberry Pi)."]},
        {"step_number": 4, "title": "Real-Time Operating Systems (RTOS) & Testing", "duration": "4 Weeks", "details": ["Learn RTOS concepts: tasks, semaphores, mutexes, and scheduling (FreeRTOS).", "Debug hardware using oscilloscopes, logic analyzers, and multimeters."]}
    ],
    "Product Manager": [
        {"step_number": 1, "title": "Product Lifecycle & Market Research", "duration": "3 Weeks", "details": ["Understand the product development lifecycle: ideation, MVP, scale, sunset.", "Conduct market sizing, competitor analysis, and customer interviews."]},
        {"step_number": 2, "title": "Agile Methodologies & Requirements", "duration": "4 Weeks", "details": ["Master Agile frameworks, Scrum practices, and sprints.", "Write high-quality Product Requirement Documents (PRDs) and user stories."]},
        {"step_number": 3, "title": "UX Principles & Analytics", "duration": "4 Weeks", "details": ["Learn user experience (UX) fundamentals, wireframing, and usability testing.", "Analyze product metrics (retention, churn, conversion) using analytics tools."]},
        {"step_number": 4, "title": "Product Strategy & Launch", "duration": "4 Weeks", "details": ["Define product visions, roadmaps, and pricing/monetization strategies.", "Coordinate cross-functional engineering, marketing, and sales teams for product launch."]}
    ],
    "Business Consultant": [
        {"step_number": 1, "title": "Business Fundamentals & Strategy", "duration": "4 Weeks", "details": ["Study corporate strategy, operations, marketing, and organizational design.", "Learn consulting frameworks (MECE, SWOT, Porter's Five Forces)."]},
        {"step_number": 2, "title": "Data Analysis & Financial Modeling", "duration": "4 Weeks", "details": ["Use Excel for data modeling, cost-benefit analysis, and business valuation.", "Gather corporate data and identify operational inefficiencies."]},
        {"step_number": 3, "title": "Problem Solving & Hypothesis Testing", "duration": "4 Weeks", "details": ["Develop issue trees and structure complex business problems.", "Formulate and test hypotheses using quantitative and qualitative data."]},
        {"step_number": 4, "title": "Client Management & Storytelling", "duration": "4 Weeks", "details": ["Master executive communication, presentation design (slide decks), and client management.", "Present final recommendation reports and implementation plans to corporate executives."]}
    ]
}

DEFAULT_ROADMAP = [
    {"step_number": 1, "title": "Foundations & Core Skills", "duration": "4 Weeks", "details": ["Master the fundamentals of the field and core programming/theory.", "Learn relevant tools, setup your development environment, and configure version control (Git)."]},
    {"step_number": 2, "title": "Intermediate Techniques & Pipelines", "duration": "6 Weeks", "details": ["Build simple to medium complexity scripts, applications, or database queries.", "Focus on implementing core modules, frameworks, and workflow automation."]},
    {"step_number": 3, "title": "Advanced Projects & Integrations", "duration": "6 Weeks", "details": ["Develop complex, end-to-end projects showcasing your skills.", "Integrate databases, API calls, and deploy models or applications."]},
    {"step_number": 4, "title": "Portfolio & Career Readiness", "duration": "4 Weeks", "details": ["Document your code and publish your projects to GitHub.", "Prepare resumes, review mock interview questions, and practice communication skills."]}
]


def parse_roadmap_with_regex(markdown_text):
    """
    Uses Regular Expressions (re) to parse custom formatted steps from Groq LLM output.
    Expected format in Markdown:
    ### Step X: [Title] - [Duration]
    - [Detail 1]
    - [Detail 2]
    """
    # Pattern explanation: 
    # Match "### Step [Number]: [Title] - [Duration]" followed by bullet points
    # until the next Step header or end of string.
    step_pattern = r'### Step (\d+):\s*(.*?)\s*-\s*(.*?)\n(.*?)(?=\n### Step|\Z)'
    matches = re.findall(step_pattern, markdown_text, re.DOTALL)
    
    parsed_steps = []
    for match in matches:
        step_num = int(match[0])
        title = match[1].strip()
        duration = match[2].strip()
        raw_details = match[3].strip()
        
        # Clean details: extract lines starting with - or * or numbers
        details = []
        for line in raw_details.split('\n'):
            line = line.strip()
            if line.startswith('-') or line.startswith('*'):
                details.append(line[1:].strip())
            elif line.startswith('•'):
                details.append(line[1:].strip())
            elif line:
                # Remove number prefixes if any
                cleaned = re.sub(r'^\d+[\.\)]\s*', '', line)
                details.append(cleaned)
                
        parsed_steps.append({
            "step_number": step_num,
            "title": title,
            "duration": duration,
            "details": details
        })
        
    return parsed_steps


def generate_roadmap(career, user_skills, user_interests, custom_api_key=None):
    """
    Generates a personalized educational roadmap. 
    Checks for Groq API keys and queries the Groq API. 
    If not available, falls back to high-quality local roadmap databases.
    """
    # Check for API Key: custom key overrides environment variables
    api_key = custom_api_key or os.getenv("GROQ_API_KEY")
    
    if not api_key:
        print("No Groq API Key found. Using local database fallback.")
        return LOCAL_ROADMAPS.get(career, DEFAULT_ROADMAP), "Local Database Fallback (No Groq API Key Configured)"

    try:
        client = Groq(api_key=api_key)
        
        # Custom prompt detailing regex target format
        prompt = f"""
You are an expert personalized career and education advisor.
Create a detailed, step-by-step educational roadmap for a user transitioning into a '{career}' career.

User's current skills: {', '.join(user_skills) if user_skills else 'Beginner / No specific skills listed'}
User's interests/background: {user_interests if user_interests else 'General Tech / Career growth'}

You MUST structure the roadmap in EXACTLY the following Markdown format so that a regular expression parser can process it:

### Step 1: [Step Title] - [Duration (e.g. 3 Weeks)]
- [Specific detail or topic to learn]
- [Actionable practice task or project]
- [Key technologies or tools to use]

### Step 2: [Step Title] - [Duration (e.g. 4 Weeks)]
- [Specific detail or topic to learn]
- [Actionable practice task or project]
- [Key technologies or tools to use]

Guidelines:
1. Provide exactly 4 steps.
2. Customize the steps to build upon their current skills and interests.
3. Keep the step title and duration on the same line as "### Step X: [Title] - [Duration]".
4. Do not include introductory or concluding conversational text. Start directly with "### Step 1:".
"""
        
        # Call Groq API
        # Using Llama 3 8B which is fast, reliable, and cheap/free depending on Groq tiers
        completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama-3.1-8b-instant",
            temperature=0.3,
            max_tokens=1000,
        )
        
        response_text = completion.choices[0].message.content
        print("Groq API completed successfully.")
        
        # Parse the output using our regex parser
        parsed_steps = parse_roadmap_with_regex(response_text)
        
        # If parsing succeeded, return it
        if parsed_steps and len(parsed_steps) >= 3:
            return parsed_steps, f"Generated dynamically by Groq AI (Llama-3.1-8B)"
        else:
            print("Regex parsing of Groq response yielded insufficient steps. Falling back to local database.")
            print(f"Raw Response:\n{response_text}")
            return LOCAL_ROADMAPS.get(career, DEFAULT_ROADMAP), "Local Database Fallback (Groq Output Formatting Mismatch)"
            
    except Exception as e:
        print(f"Error calling Groq API: {e}. Falling back to local database.")
        return LOCAL_ROADMAPS.get(career, DEFAULT_ROADMAP), f"Local Database Fallback (Groq API Error: {str(e)})"


if __name__ == "__main__":
    # Test the regex parser locally
    test_text = """
### Step 1: Python Basics & SQL - 3 Weeks
- Learn basic Python syntax: variables, loops, conditionals, functions.
- Practice querying relational databases with SQL (SELECT, JOINS, GROUP BY).
- Practice exercises on SQL and python.

### Step 2: Data Wrangling with Pandas - 4 Weeks
- Learn NumPy for numerical operations and array processing.
- Clean and analyze datasets using Pandas.
- Build a miniature automation script.
"""
    parsed = parse_roadmap_with_regex(test_text)
    print("Test Regex Parser:")
    for step in parsed:
        print(f"Step {step['step_number']}: {step['title']} ({step['duration']})")
        for detail in step['details']:
            print(f"  - {detail}")
