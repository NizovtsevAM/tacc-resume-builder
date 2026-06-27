# Prompt for Resume Generation from TACC Data in ChatGPT / Claude / Gemini

## Instructions
1. Take the `tacc.json` file (a JSON array of records from the TACC Timesheet system)
2. Copy its contents
3. Paste it into an online LLM (chatgpt.com, claude.ai, etc.) together with the prompt text below
4. In response, you'll receive a ready-to-use resume in HTML and JSON formats

---

## Prompt

```
You are a professional recruiter and HR analyst with many years of experience in creating ATS-optimized resumes.

Below I am uploading a tacc.json file with data from a time-tracking system spanning from 2012 to 2025. The file contains ~4100 records with the following fields:
- CustomerName — client / project name
- ContractId — if not null, the work is billable
- Date — date (M/D/YYYY)
- Description — task description
- TotalTime / UnbillableTime — hours

Personal details (use these in the resume):
- First Name: NAME
- Last Name: SURNAME
- Email: email@gmail.com
- Phone: +123 45 1234567
- Location: New York, US
- LinkedIn: LinkedIn profile URL or handle.

### Your Task:

Create a professional ATS-optimized resume following these rules:

#### 1. Profession (Heading)
Determine the most appropriate professional title based on the technologies and work descriptions. Consider the tech stack: .NET, GoLang, React, Azure, Docker, Elasticsearch, SQL Server, Angular, Vue.js, jQuery, Python, Java, PHP, Jenkins, CI/CD, AWS, GraphQL. Seniority — Senior. Core stack — .NET / Full Stack.

#### 2. Professional Summary (3-5 sentences)
- ATS-optimized, with key technologies naturally integrated
- Include total years of experience (calculate from the earliest to the latest date)
- Mention key industries: Telecommunications/ISP, Media & Entertainment
- Tone: confident, professional
- NO clichés ("results-driven", "team player", "proven track record")
- No first-person pronouns

#### 3. Technical Skills — group technologies by category:
- Backend: .NET, C#, ASP.NET, GoLang, REST API, WCF, SOAP, GraphQL, Python, Java, PHP
- Frontend: React, Angular, Vue.js, JavaScript, jQuery, HTML, CSS, Bootstrap
- Cloud: Azure, AWS, Amazon Web Services
- DevOps: Docker, CI/CD, Jenkins, Git, TFS
- Databases: SQL Server, Elasticsearch, PostgreSQL (if present)
- Testing: (if present in descriptions)
- Data Engineering: (if present)
- Architecture: (if present)

Exclude from skills: CMS, FTP, Excel, Chrome, IE9, MediaWiki, OnConnect, AppManagement, Query Manager, "Calendar list", GUI, Rovi, Hulu, Netflix, Bamboo, "SQL scripts", IPTV (these are domain/tool terms, not technologies). Also exclude YouTube, LinkedIn as social networks.

#### 4. Professional Experience
Group records by CustomerName. Each client with a duration >= 30 days becomes a separate project in the resume.

For each project:
- Client name
- Role (determine based on technologies and descriptions)
- Start and end dates (format: "Oct 2019 — Nov 2025")
- Duration in days
- **Responsibilities** (3-5 bullet points):
  - Start each with a strong action verb (Developed, Implemented, Architected, Optimized, Designed)
  - Use present tense for current/recent projects
  - Maximum 20 words per bullet
  - Be specific, avoid generic phrases
- **Achievements** (2-4 bullet points):
  - Measurable results where possible
  - Specific improvements: optimization, migration, automation

**Important:** Descriptions in tacc.json often contain task IDs (DT-47, DT-78, DT-74, etc.). Do NOT include task IDs in the final resume — rephrase the task essence into a professional bullet point.

#### 5. Output Format
Return the result as Markdown with two sections:

---HTML_START---
[Resume HTML code in modern style — see requirements below]
---HTML_END---

---JSON_START---
[JSON with resume data — profession, summary, skills, projects]
---JSON_END---

#### HTML Requirements:
- Modern design: dark gradient header, light background, shadows
- Responsive layout
- Clickable contact links (email, linkedin)
- Technical skills displayed as "tag" elements with rounded corners
- Each project: name → role → dates → responsibilities → achievements → technologies
- Use Segoe UI font
- Max width 850px, centered

#### JSON Requirements:
- Fields: profession, summary, years_experience, skills (category object), projects (array)
- In projects: customer, role, start_date, end_date, duration_days, work_types, technologies, responsibilities, achievements
```

---

## Notes for the User

1. Upload the `tacc.json` file into the LLM chat
2. Copy the prompt text above and send it
3. If the model complains about file size (tacc.json ~2MB) — say "read the full file, it's a JSON array of my work records"
4. After receiving the result:
   - Save HTML as `resume.html` and open in a browser
   - Save JSON as `resume.json` for import into other systems

### Alternative: Compact Prompt (if the model cannot process 4000+ records)

If ChatGPT/Claude cannot handle the entire file, use this approach:
> "Analyze the first 200 records from the file as a representative sample. Identify the main projects and technologies. Create a resume based on this sample."

Or pre-process the data locally:
```bash
python3 -c "
import json
with open('input/tacc.json') as f:
    data = json.load(f)
# Keep only billable records (with ContractId)
data = [r for r in data if r.get('ContractId') is not None]
# Deduplicate to 1 record per day per customer
seen = set()
deduped = []
for r in data:
    key = f\"{r['CustomerName']}_{r.get('Date','')}\"
    if key not in seen:
        seen.add(key)
        deduped.append(r)
with open('input/tacc_compact.json', 'w') as f:
    json.dump(deduped, f, indent=2, ensure_ascii=False)
print(f'Reduced from {len(data)} to {len(deduped)} records')
# => ~2000 records
"