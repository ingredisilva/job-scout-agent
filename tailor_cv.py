#!/usr/bin/env python3
"""
Tailor CV - AI-driven resume tailoring using local Ollama.
No external network dependencies version.
"""

import os
import sys
import json
import configparser
import urllib.request
import urllib.error

# Try to import pypdf for PDF extraction
try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

CONFIG_FILE = "profile.conf"

def load_config():
    config = configparser.RawConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
    return config

def extract_text_from_pdf(pdf_path):
    if not PYPDF_AVAILABLE:
        print("  [Warning] pypdf library is not installed. Trying to install it or read plain text...")
        raise ImportError("pypdf is required. Please install it using: pip install pypdf")
    
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Base resume PDF not found at: {pdf_path}")
    
    print(f"  Extracting text from base CV: {pdf_path}")
    reader = pypdf.PdfReader(pdf_path)
    text = []
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text.append(page_text)
    return "\n".join(text)

def query_ollama(ollama_url, model, system_prompt, user_prompt):
    url = f"{ollama_url.rstrip('/')}/api/chat"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "stream": False,
        "options": {
            "temperature": 0.3  # Low temperature for factual CV tailoring
        }
    }
    
    headers = {"Content-Type": "application/json"}
    data = json.dumps(payload).encode("utf-8")
    
    try:
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=120) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return res_data.get("message", {}).get("content", "")
    except urllib.error.URLError as e:
        print(f"  [Error] Failed to connect to Ollama at {url}: {e.reason}")
        print("  Please make sure Ollama is running and the model is pulled.")
        raise e
    except Exception as e:
        print(f"  [Error] Ollama query failed: {e}")
        raise e

def generate_tailored_cv(job_title, company, job_description, output_dir):
    config = load_config()
    
    # Retrieve Ollama config
    ollama_url = config.get("ollama", "url", fallback="http://localhost:11434")
    model = config.get("ollama", "model", fallback="gemma4:latest")
    pdf_path = config.get("ollama", "resume_path", fallback="")
    
    if not pdf_path:
        print("  [Error] resume_path not configured in profile.conf [ollama] section.")
        return False
        
    try:
        base_cv_text = extract_text_from_pdf(pdf_path)
    except Exception as e:
        print(f"  [Error] Could not read base PDF: {e}")
        return False

    print(f"  Tailoring CV for {job_title} at {company} using {model}...")
    
    system_prompt = (
        "You are an expert technical recruiter and resume editor. Your task is to customize "
        "a candidate's resume to match a specific job description. "
        "CRITICAL RULES:\n"
        "1. DO NOT LIE OR FABRICATE skills, roles, projects, or certifications that are not "
        "present in the candidate's original resume.\n"
        "2. ONLY highlight, reorganize, and rephrase existing experience to match the keywords "
        "and responsibilities in the job description.\n"
        "3. Emphasize React, Frontend, and Node.js skills if they are in the job description and "
        "exist in the base resume.\n"
        "4. Output the final resume in clean Markdown format.\n"
        "5. DYNAMIC LANGUAGE: Write the tailored resume in the SAME language as the job description "
        "(e.g., if the job description is in English, translate the resume summary, experience descriptions, "
        "bullet points, and section headers to English. If it is in Portuguese, output in Portuguese)."
    )
    
    user_prompt = f"""
Here is the candidate's base resume text:
---
{base_cv_text}
---

Here is the Target Job description:
---
Job Title: {job_title}
Company: {company}
Description:
{job_description}
---

Please tailor the resume to fit this job. Highlight relevant experience, match the vocabulary (keywords), and structure it professionally.
Make sure the language of the output matches the job description language (translate headings and details to English if the job description is in English; write in Portuguese if it is in Portuguese).
Output ONLY the tailored resume in Markdown.
"""

    try:
        tailored_markdown = query_ollama(ollama_url, model, system_prompt, user_prompt)
        if not tailored_markdown:
            print("  [Error] Ollama returned empty response.")
            return False
            
        # Save Markdown version
        md_path = os.path.join(output_dir, "cv_tailored.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(tailored_markdown)
        print(f"  Saved tailored CV (Markdown): {md_path}")
        
        # Generate HTML version
        generate_html_cv(tailored_markdown, job_title, company, output_dir)
        return True
        
    except Exception as e:
        print(f"  [Error] Tailoring process failed: {e}")
        return False

def generate_html_cv(markdown_text, job_title, company, output_dir):
    # Convert simple Markdown elements to HTML for a premium presentation
    html_lines = []
    in_list = False
    
    for line in markdown_text.splitlines():
        line = line.strip()
        if not line:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            continue
            
        # Headers
        if line.startswith("# "):
            if in_list: html_lines.append("</ul>"); in_list = False
            html_lines.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "):
            if in_list: html_lines.append("</ul>"); in_list = False
            html_lines.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("### "):
            if in_list: html_lines.append("</ul>"); in_list = False
            html_lines.append(f"<h3>{line[4:]}</h3>")
        # Lists
        elif line.startswith("- ") or line.startswith("* "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            content = line[2:]
            # Bold parsing
            content = re_bold(content)
            html_lines.append(f"<li>{content}</li>")
        # Regular paragraph
        else:
            if in_list: html_lines.append("</ul>"); in_list = False
            line = re_bold(line)
            html_lines.append(f"<p>{line}</p>")
            
    if in_list:
        html_lines.append("</ul>")
        
    html_body = "\n".join(html_lines)
    
    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Tailored CV - Ingredi - {company}</title>
    <style>
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: #2D3748;
            line-height: 1.6;
            max-width: 800px;
            margin: 40px auto;
            padding: 0 20px;
            background-color: #F7FAFC;
        }}
        .cv-container {{
            background: #FFFFFF;
            padding: 50px;
            border-radius: 8px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }}
        h1 {{
            color: #1A365D;
            border-bottom: 2px solid #E2E8F0;
            padding-bottom: 8px;
            margin-top: 0;
            font-size: 26px;
        }}
        h2 {{
            color: #2B6CB0;
            font-size: 20px;
            margin-top: 30px;
            border-bottom: 1px solid #EDF2F7;
            padding-bottom: 4px;
        }}
        h3 {{
            color: #4A5568;
            font-size: 16px;
            margin-top: 20px;
        }}
        p, li {{
            font-size: 14px;
            color: #4A5568;
        }}
        ul {{
            padding-left: 20px;
        }}
        li {{
            margin-bottom: 6px;
        }}
        @media print {{
            body {{
                background-color: #FFFFFF;
                margin: 0;
                padding: 0;
            }}
            .cv-container {{
                box-shadow: none;
                padding: 0;
            }}
        }}
    </style>
</head>
<body>
    <div class="cv-container">
        {html_body}
    </div>
</body>
</html>
"""
    
    html_path = os.path.join(output_dir, "cv_tailored.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_template)
    print(f"  Saved tailored CV (HTML): {html_path}")

def re_bold(text):
    # Quick markdown bold to html bold regex helper
    import re
    return re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)

if __name__ == "__main__":
    # Test script standalone
    if len(sys.argv) > 4:
        generate_tailored_cv(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        print("Usage: python tailor_cv.py <job_title> <company> <job_description> <output_dir>")
