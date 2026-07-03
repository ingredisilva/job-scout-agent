# Job Scout: Local Job Hunting Dashboard & Automation Pipeline

Job Scout is a privacy-first, fully local job-hunting pipeline and web dashboard. It aggregates opportunities from both Brazilian (Gupy candidate portal) and international remote job boards (Remotive, RemoteOK, Arbeitnow, etc.), scores listings against your profile, flags on-site (presencial) positions for manual review, and dynamically generates tailored resumes in English or Portuguese using your local **Ollama** LLM.

Everything runs 100% locally and free of charge, with zero external API key dependencies.

---

## 🌟 Key Features

*   **Bilingual Job Searches:** Aggregates remote, hybrid, and local opportunities in Brazil (via Gupy) and global remote boards.
*   **On-site Filtering ("Review Manual"):** Automatically flags in-person roles for manual review, skipping automatic resume creation to maintain high application quality.
*   **Dynamic Bilingual CV Tailoring:** Uses local Ollama to rewrite your resume's summary, keywords, and bullet points to match the job description. Generates CVs in **English** or **Portuguese** depending on the language of the job posting.
*   **Print-Ready Formats:** Saves customized resumes in clean Markdown (`cv_tailored.md`) and styled, print-ready HTML (`cv_tailored.html`) inside the job results folder.
*   **Glassmorphic Web Dashboard:** Control the search script, stream console logs live, filter/sort listings, change application status, and open local results directories in your OS File Explorer with one click.

---

## ⚙️ Prerequisites

1.  **Python 3.7+**
2.  **Ollama** installed on your host. Pull the model configured in `profile.conf`:
    ```bash
    ollama pull gemma4:latest
    ```
3.  **Python Dependencies:** Install the PDF parsing library:
    ```bash
    pip install pypdf
    ```

---

## 🚀 Setup & Execution

### 1. Configure your Profile
Open `profile.conf` and update the `[user]` and `[ollama]` sections:

```ini
[user]
name = Your Name
target_title = Frontend Developer, React Developer, Fullstack Developer
target_skills = react, javascript, typescript, node.js, HTML, CSS
location_preference = Brazil (Remote, Hybrid), International Remote (Worldwide, LATAM)
salary_expectation = 6000 BRL

[ollama]
url = http://localhost:11434
model = gemma4:latest
resume_path = C:\Path\To\Your\Base_Resume.pdf
```

### 2. Run the Dashboard
Start the local Python server in the project root:
```bash
python server.py
```

### 3. Access the Web Dashboard
Open your web browser and navigate to:
👉 **[http://localhost:8088](http://localhost:8088)**

From the dashboard, you can:
*   Click **"Run Job Scout"** to start the search and monitor the scraper logs live.
*   View all fetched jobs sorted by fit score.
*   Filter by titles, companies, statuses, or workplace types (Remote/Hybrid/On-site).
*   Change job status (Applied, Not Applied, Review Manual).
*   Click the **Folder Icon** next to any job to instantly open its local results folder in your OS File Explorer.

---

## 📂 Output Structure
Every execution creates categorized results inside your user home directory:

```text
~/job_scout_results/
  2026-06-30/
    summary.md                    ← Daily search report
    Vivo_Digital_React_Dev/
      job_description.txt         ← Clean text details of the vacancy
      match_score.txt             ← Fit score details (e.g. 77/100)
      apply_link.txt              ← Original application link
      cv_tailored.md              ← Tailored resume in Markdown
      cv_tailored.html            ← Styled print-ready resume (Ctrl+P to export PDF)
  job_scout_tracker.csv           ← Main tracker database (imported into Google Sheets)
```

---

## 🤝 Open Source & Contributions
This customized project is modified from the original `job-scout-agent` repository. Feel free to extend scrapers and adjust scoring coefficients in `profile.conf`.
