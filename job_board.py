# job_board.py

MOCK_JOBS = [
    # AI Engineer
    {
        "career": "AI Engineer",
        "title": "AI & Generative AI Developer",
        "company": "Viswam AI Solutions",
        "location": "Hyderabad (Hybrid)",
        "salary": "₹12,00,000 - ₹18,00,000 / year",
        "skills": ["Python", "TensorFlow", "Deep Learning", "LangChain", "Generative AI"],
        "link": "https://careers.google.com"
    },
    {
        "career": "AI Engineer",
        "title": "Graduate AI Engineer",
        "company": "Infosys",
        "location": "Bangalore (On-site)",
        "salary": "₹8,00,000 - ₹12,00,000 / year",
        "skills": ["Python", "Machine Learning", "NLP", "PyTorch", "SQL"],
        "link": "https://www.infosys.com/careers.html"
    },
    # Data Scientist
    {
        "career": "Data Scientist",
        "title": "Junior Data Scientist",
        "company": "Cognizant",
        "location": "Hyderabad (Remote)",
        "salary": "₹7,50,000 - ₹11,00,000 / year",
        "skills": ["Python", "SQL", "Statistics", "Machine Learning", "Excel"],
        "link": "https://careers.cognizant.com"
    },
    {
        "career": "Data Scientist",
        "title": "Data Science Associate",
        "company": "TCS",
        "location": "Bangalore (On-site)",
        "salary": "₹6,00,000 - ₹9,50,000 / year",
        "skills": ["Python", "SQL", "Tableau", "Statistics", "Machine Learning"],
        "link": "https://www.tcs.com/careers"
    },
    # Data Analyst
    {
        "career": "Data Analyst",
        "title": "Data Analyst Intern",
        "company": "Cognifyz Technologies",
        "location": "Remote",
        "salary": "₹4,00,000 - ₹6,50,000 / year",
        "skills": ["Excel", "SQL", "Power BI", "Python"],
        "link": "https://www.linkedin.com/jobs"
    },
    {
        "career": "Data Analyst",
        "title": "Business Intelligence Analyst",
        "company": "Wipro",
        "location": "Hyderabad (On-site)",
        "salary": "₹5,50,000 - ₹8,00,000 / year",
        "skills": ["Power BI", "SQL", "Excel", "Tableau", "Python"],
        "link": "https://careers.wipro.com"
    },
    # ML Engineer
    {
        "career": "ML Engineer",
        "title": "Machine Learning Operations (MLOps) Engineer",
        "company": "Tech Mahindra",
        "location": "Bangalore (Hybrid)",
        "salary": "₹10,00,000 - ₹15,00,000 / year",
        "skills": ["Python", "Machine Learning", "TensorFlow", "Docker", "Kubernetes"],
        "link": "https://www.techmahindra.com/en-in/careers/"
    },
    {
        "career": "ML Engineer",
        "title": "ML Engineer - Systems",
        "company": "Accenture",
        "location": "Hyderabad (On-site)",
        "salary": "₹9,00,000 - ₹13,50,000 / year",
        "skills": ["Python", "Machine Learning", "PyTorch", "Docker", "Linux"],
        "link": "https://www.accenture.com/in-en/careers"
    },
    # Software Engineer
    {
        "career": "Software Engineer",
        "title": "Associate Software Engineer",
        "company": "HCLTech",
        "location": "Noida (On-site)",
        "salary": "₹5,00,000 - ₹8,00,000 / year",
        "skills": ["Java", "OOP", "DBMS", "SQL", "DSA"],
        "link": "https://www.hcltech.com/careers"
    },
    {
        "career": "Software Engineer",
        "title": "Python Developer",
        "company": "Capgemini",
        "location": "Hyderabad (Hybrid)",
        "salary": "₹6,50,000 - ₹10,00,000 / year",
        "skills": ["Python", "NodeJS", "RESTful APIs", "SQL", "OOP"],
        "link": "https://www.capgemini.com/careers"
    },
    # Financial Analyst
    {
        "career": "Financial Analyst",
        "title": "Financial Analyst - Corporate Finance",
        "company": "PwC India",
        "location": "Hyderabad (On-site)",
        "salary": "₹8,00,000 - ₹12,00,000 / year",
        "skills": ["Finance", "Accounting", "Excel", "Valuation"],
        "link": "https://www.pwc.in/careers.html"
    },
    {
        "career": "Financial Analyst",
        "title": "Investment Banking Analyst",
        "company": "Goldman Sachs",
        "location": "Bangalore (On-site)",
        "salary": "₹15,00,000 - ₹22,00,000 / year",
        "skills": ["Finance", "Financial Modeling", "Valuation", "Excel"],
        "link": "https://www.goldmansachs.com/careers"
    },
    # Digital Marketer
    {
        "career": "Digital Marketer",
        "title": "SEO & Performance Marketing Specialist",
        "company": "Inbound Digital",
        "location": "Remote",
        "salary": "₹4,50,000 - ₹7,00,000 / year",
        "skills": ["SEO", "Google Ads", "Marketing", "Content Strategy"],
        "link": "https://www.linkedin.com/jobs"
    },
    {
        "career": "Digital Marketer",
        "title": "Social Media Campaign Manager",
        "company": "Flipkart",
        "location": "Bangalore (Hybrid)",
        "salary": "₹7,00,000 - ₹11,00,000 / year",
        "skills": ["Social Media", "Branding", "Marketing", "Copywriting"],
        "link": "https://www.flipkartcareers.com"
    },
    # UI/UX Designer
    {
        "career": "UI/UX Designer",
        "title": "Junior Product UI Designer",
        "company": "Razorpay",
        "location": "Bangalore (Hybrid)",
        "salary": "₹8,00,000 - ₹13,00,000 / year",
        "skills": ["Figma", "UI/UX Design", "Wireframing", "Prototyping"],
        "link": "https://razorpay.com/jobs/"
    },
    {
        "career": "UI/UX Designer",
        "title": "Graphic & UI Designer",
        "company": "Swiggy",
        "location": "Remote",
        "salary": "₹6,00,000 - ₹9,50,000 / year",
        "skills": ["Photoshop", "Illustrator", "Figma", "Design", "Canva"],
        "link": "https://careers.swiggy.com"
    },
    # HR Specialist
    {
        "career": "HR Specialist",
        "title": "Talent Acquisition Associate",
        "company": "Deloitte India",
        "location": "Hyderabad (On-site)",
        "salary": "₹5,50,000 - ₹8,50,000 / year",
        "skills": ["Recruitment", "Communication", "Talent Acquisition"],
        "link": "https://www2.deloitte.com/in/en/careers"
    },
    {
        "career": "HR Specialist",
        "title": "Human Resources Executive",
        "company": "Amazon India",
        "location": "Bangalore (Hybrid)",
        "salary": "₹7,00,000 - ₹11,50,000 / year",
        "skills": ["HR Management", "Communication", "Management"],
        "link": "https://www.amazon.jobs"
    },
    # Mechanical Engineer
    {
        "career": "Mechanical Engineer",
        "title": "CAD Design Engineer",
        "company": "Tata Motors",
        "location": "Pune (On-site)",
        "salary": "₹6,00,000 - ₹9,00,000 / year",
        "skills": ["CAD", "SolidWorks", "AutoCAD", "Manufacturing Engineering"],
        "link": "https://www.tatamotors.com/careers/"
    },
    {
        "career": "Mechanical Engineer",
        "title": "Thermal Analyst",
        "company": "L&T Technology Services",
        "location": "Bangalore (On-site)",
        "salary": "₹7,00,000 - ₹10,50,000 / year",
        "skills": ["Thermodynamics", "MATLAB", "CAD", "SolidWorks"],
        "link": "https://www.ltts.com/careers"
    },
    # Embedded Systems Engineer
    {
        "career": "Embedded Systems Engineer",
        "title": "Embedded Software Engineer",
        "company": "Robert Bosch India",
        "location": "Coimbatore (On-site)",
        "salary": "₹7,50,000 - ₹12,00,000 / year",
        "skills": ["microcontrollers", "embedded systems", "circuit design", "Arduino"],
        "link": "https://careers.smartcampus.bosch.com"
    },
    {
        "career": "Embedded Systems Engineer",
        "title": "Firmware Development Intern",
        "company": "Qualcomm",
        "location": "Hyderabad (On-site)",
        "salary": "₹12,00,000 - ₹16,00,000 / year",
        "skills": ["embedded systems", "microcontrollers", "circuit design", "Raspberry Pi"],
        "link": "https://www.qualcomm.com/company/careers"
    },
    # Product Manager
    {
        "career": "Product Manager",
        "title": "Associate Product Manager (APM)",
        "company": "Paytm",
        "location": "Noida (Hybrid)",
        "salary": "₹12,00,000 - ₹16,00,000 / year",
        "skills": ["Product Management", "Agile", "Scrum", "Business Analysis"],
        "link": "https://careers.paytm.com"
    },
    {
        "career": "Product Manager",
        "title": "Junior Product Manager",
        "company": "PhonePe",
        "location": "Bangalore (On-site)",
        "salary": "₹14,00,000 - ₹20,00,000 / year",
        "skills": ["Product Strategy", "Product Lifecycle", "Agile", "Product Management"],
        "link": "https://www.phonepe.com/careers"
    },
    # Business Consultant
    {
        "career": "Business Consultant",
        "title": "Management Consultant Associate",
        "company": "EY India",
        "location": "Mumbai (On-site)",
        "salary": "₹9,00,000 - ₹14,00,000 / year",
        "skills": ["Business Analysis", "Strategy", "Consulting", "Finance"],
        "link": "https://www.ey.com/en_in/careers"
    },
    {
        "career": "Business Consultant",
        "title": "Operations Strategy Advisor",
        "company": "McKinsey & Company",
        "location": "Gurugram (On-site)",
        "salary": "₹18,00,000 - ₹25,00,000 / year",
        "skills": ["Operations Management", "Strategy", "Communication", "Consulting"],
        "link": "https://www.mckinsey.com/careers"
    },
    # Civil Engineer
    {
        "career": "Civil Engineer",
        "title": "Site Engineer - Concrete Structures",
        "company": "L&T Construction",
        "location": "Chennai (On-site)",
        "salary": "₹5,50,000 - ₹8,00,000 / year",
        "skills": ["Civil Engineering", "Concrete Construction Management", "AutoCAD", "Surveying"],
        "link": "https://www.lntecc.com"
    },
    {
        "career": "Civil Engineer",
        "title": "Structural AutoCAD Drafter",
        "company": "Shapoorji Pallonji",
        "location": "Mumbai (On-site)",
        "salary": "₹6,00,000 - ₹9,50,000 / year",
        "skills": ["AutoCAD", "CAD", "Structural Engineering", "Estimation"],
        "link": "https://www.shapoorjipallonji.com/careers"
    },
    # Content Writer (Additional fallback)
    {
        "career": "Content Writer",
        "title": "Technical Content Writer",
        "company": "GeeksforGeeks",
        "location": "Noida (Hybrid)",
        "salary": "₹4,00,000 - ₹6,50,000 / year",
        "skills": ["Writing", "Editing", "Research", "Blogging"],
        "link": "https://www.geeksforgeeks.org/careers/"
    }
]

def get_jobs_for_career(career, user_skills):
    """
    Retrieves mock job openings for a given career path.
    Analyzes which skills the user has matching each job's requirements.
    """
    matching_jobs = []
    
    # 1. Filter jobs by career (case-insensitive substring match)
    for job in MOCK_JOBS:
        if job["career"].lower() in career.lower() or career.lower() in job["career"].lower():
            matching_jobs.append(job)
            
    # 2. Fallback: If no direct career match, show some general software engineering jobs
    if not matching_jobs:
        for job in MOCK_JOBS:
            if job["career"] == "Software Engineer":
                matching_jobs.append(job)
                
    # 3. Process skill matches for each job
    processed_jobs = []
    user_skills_lower = [s.lower().strip() for s in user_skills]
    
    for job in matching_jobs[:3]:  # Limit to top 3 jobs
        matched = []
        missing = []
        
        for skill in job["skills"]:
            # Check if skill matches user's skills
            if skill.lower().strip() in user_skills_lower:
                matched.append(skill)
            else:
                # Try substring check to be flexible
                has_match = False
                for us in user_skills_lower:
                    if us in skill.lower() or skill.lower() in us:
                        has_match = True
                        break
                if has_match:
                    matched.append(skill)
                else:
                    missing.append(skill)
                    
        processed_jobs.append({
            "title": job["title"],
            "company": job["company"],
            "location": job["location"],
            "salary": job["salary"],
            "matched_skills": matched,
            "missing_skills": missing,
            "link": job["link"]
        })
        
    return processed_jobs
