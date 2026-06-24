# Resume Generator from TACC Time-Tracking Data

A powerful CLI tool that integrates with TACC time-tracking data via API to automatically generate professional, ATS-optimized resumes in multiple formats (`.docx`, `.html`, `.json`). The system leverages advanced LLM capabilities for deep analysis and content generation while maintaining robust fallback mechanisms.

## ✨ Key Features
*   **LLM-Driven Intelligence:** AI enhances resume quality by generating detailed bullet points, summarizing roles, and detecting professional profiles. (Optional, recommended).
*   **Smart Extraction:** Automatically extracts technologies using a combination of regex patterns and advanced LLM analysis.
*   **Structured Classification:** Classifies work types (e.g., development, support, DevOps) and infers project roles.
*   **Modular Templates:** Easily switch between `modern`, `classic`, `minimalist`, or `creative` designs for tailored output.
*   **Robustness & Reliability:** Features include rate limiting (token bucket), exponential backoff retries, and graceful degradation when LLM services fail.
*   **Comprehensive Output:** Generates DOCX (ATS-friendly), HTML (web-ready), and JSON (structured data) exports, all with hyperlinked contacts.

## 🚀 Quick Start Guide

Follow these steps to set up and run the generator.

### Prerequisites
Ensure you have Python 3 installed.

### 1. Installation
Install the necessary dependencies:
```bash
pip3 install pydantic python-docx pytest pytest-mock
```

### 2. Configuration (.env)
Copy the example file to create your environment configuration and edit it with your credentials.
```bash
cp .env.example .env
# Edit .env with TACC API details, personal info, and LLM settings.
```

### 3. Execution
Run the main script from your terminal:
```bash
python3 main.py
```
An interactive menu will appear, allowing you to choose between fetching data, generating the resume, or doing both.

---

## ⚙️ Configuration Details (.env)

The `.env` file controls all aspects of the generation process.

### TACC API Settings (Required for Data Fetching)
| Variable | Default | Description |
| :--- | :--- | :--- |
| `TACC_EMAIL` | — | TACC login email |
| `TACC_PASSWORD` | — | TACC login password |
| `TACC_START_DATE` | `1/1/2011` | Timesheet fetch start date (`M/D/YYYY`) |
| `TACC_END_DATE` | `6/30/2026` | Timesheet fetch end date (`M/D/YYYY`) |
| `MINIMUM_PROJECT_DURATION_DAYS` | `30` | Skip projects shorter than this duration. |

### Personal Info (Required for Resume Content)
| Variable | Default | Description |
| :--- | :--- | :--- |
| `FIRST_NAME` | `John` | Your first name (1-100 chars). |
| `LAST_NAME` | `Doe` | Your last name (1-100 chars). |
| `TITLE` | `auto` | Professional title (`auto` = auto-detect by LLM). |
| `EMAIL` | — | Primary email address (validated for `@`). |
| `PHONE` | — | Phone number. |
| `LOCATION` | — | City, Country (e.g., "New York, US"). |
| `LINKEDIN` | — | LinkedIn profile URL or handle. |

### Template & Filtering Settings
| Variable | Default | Valid Values | Description |
| :--- | :--- | :--- | :--- |
| `RESUME_TEMPLATE` | `modern` | `modern`, `classic`, `minimalist`, `creative` | Selects the HTML template style. |
| `ENV_EXCLUDE_CUSTOMERS` | `Internal,` | Comma-separated list of customer names to ignore. |
| `ENV_TECHNOLOGY_BLACKLIST` | `react,angular` | Comma-separated list of technologies to filter out. |

### LLM Provider Settings (Optional)
These settings control the AI enhancement features.

| Variable | Default | Description |
| :--- | :--- | :--- |
| `USE_LLM` | `false` | Enable LLM enhancement (`true`/`false`). |
| `LLM_URL` | `http://127.0.0.1:1234` | API endpoint URL (must start with `http://` or `https://`). |
| `LLM_MODEL` | `google/gemma-4-e4b` | Model name sent to API. |
| `LLM_PROVIDER` | `lmstudio` | Provider type (`lmstudio`, `ollama`, `openai`, etc.). |
| `LLM_API_KEY` | — | Required key for cloud providers. |
| **Rate Limiting** | | The built-in Token Bucket protects against overuse. |
| `LLM_RATE_LIMIT_RPM` | `30` | Requests per minute (1-1000). |
| `LLM_MAX_BURST` | `5` | Max burst tokens for rate limiter (1-100). |


### Module Responsibilities
*   `config.py`: Handles Pydantic settings, environment loading, and date utilities.
*   `models.py`: Defines core domain structures (`ResumeProject`, `ResumeProfile`).
*   `llm.py`: Abstract LLM interface with rate limiting and multiple provider implementations.
*   `extractors.py`: Extracts technology names (regex + optional LLM) and classifies work types.
*   `generators.py`: Generates professional summaries, achievements, skill categories, and roles.
*   `processors.py`: The core logic pipeline: loads data, groups projects, filters by duration, calls extractors/generators.
*   `exporters.py`: Responsible for rendering the final output into DOCX, HTML, or JSON formats.
*   `workflows.py`: Orchestrates the entire process (CLI menu and sequential steps).

## 🔬 Workflow Deep Dive

### Data Flow (The Generation Pipeline)
1.  **Fetch:** Authenticates with TACC API and downloads raw timesheet records to `input/tacc.json`.
2.  **Load & Categorize:** Reads the raw data, separating billable vs. non-billable work based on configuration.
3.  **Group & Filter:** Groups records by customer and removes projects below `MINIMUM_PROJECT_DURATION_DAYS`.
4.  **Enhance (Per Project):** For each project, it runs:
    *   Technology Extraction (Regex + LLM).
    *   Work Type Classification (Keyword scoring + LLM).
    *   Responsibility/Achievement Generation (Heuristic + LLM).
5.  **Aggregate:** Builds the overall profile by detecting the primary profession and compiling a skill matrix across all projects.
6.  **Summary & Export:** Generates the final professional summary before exporting to multiple formats.

### Fallback Behavior
The system is designed for maximum uptime: if any LLM service fails or is disabled (`USE_LLM=false`):
*   Technology extraction falls back entirely to **18 predefined regex patterns**.
*   Work type classification uses **keyword scoring only**.
*   Role/Summary generation defaults to robust **heuristic templates**.

## 🧪 Testing & Validation
The system includes comprehensive testing and validation:
*   **Pydantic Validation:** All settings loaded from `.env` are strictly validated on startup (e.g., valid LLM providers, date formats).
*   **Test Suite:** Run unit tests with `python3 -m pytest tests/test_services.py`. The suite covers rate limiters, data processing, and model integrity (47+ tests).

## 📂 Project Structure
```
.
├── input/            # Generated: Raw TACC timesheet JSON file.
├── output/           # Generated: Resume files (.docx, .html, .json).
├── templates/        # Static HTML templates (modern.html, classic.html, etc.).
├── tests/            # Unit test directory.
├── src/              # Core Python modules (config, models, llm, etc.).
├── main.py           # Entry point and CLI wrapper.
└── .env              # Runtime configuration file (credentials).