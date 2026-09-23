# Tools to Learn

Three levels:
- 🟢 **Deep** — master it; used heavily in RootCause and other projects
- 🟡 **Working** — used hands-on in at least one project
- ⚪ **Awareness** — know what it is and when it's used; learn it quickly if a job needs it

**Rule:** learn each tool when a project needs it, not months in advance. One tool per category deeply; know the alternatives exist.

---

## 1. Foundations (learn first, weeks 1–6)
| Tool | Level | Where used |
|---|---|---|
| Python | 🟢 | Everything |
| SQL | 🟢 | Everything |
| Git + GitHub | 🟢 | Every project |
| Command line (Windows + Linux/Bash basics) | 🟢 | Every project; data pipelines |
| VS Code | 🟢 | Daily |
| Python virtual environments + pip | 🟢 | Every project |
| JSON, REST APIs, HTTP | 🟢 | Every project |

## 2. Databases and data
| Tool | Level | Project |
|---|---|---|
| PostgreSQL | 🟢 | RootCause, ReplayDesk, most projects |
| pgvector | 🟢 | RootCause, RedFlag (RAG) |
| BigQuery | 🟡 | RootCause (GA4), Companion Economics |
| Redis | 🟡 | ReplayDesk (Celery queue) |
| MongoDB | 🟡 | TriageRouter (MERN), raw logs |
| SQLite | 🟡 | Practice and mini projects |
| Snowflake | ⚪ | One weekend on the free trial before applying where needed |
| MySQL, Redshift, Databricks, ClickHouse | ⚪ | Awareness |

## 3. Data processing and pipelines
| Tool | Level | Project |
|---|---|---|
| pandas, NumPy | 🟢 | Everywhere |
| Shell tools (awk, sed, cron) | 🟡 | PageviewPulse, RootCause Module 1 |
| dbt | ⚪→🟡 | Optional in RootCause (transformations) |
| Airflow, Fivetran, Airbyte, Kafka | ⚪ | Awareness |

## 4. LLMs and AI apps
| Tool | Level | Project |
|---|---|---|
| Gemini API (free tier) | 🟢 | RootCause and all AI projects |
| LangGraph | 🟢 | RootCause, RedFlag (agents) |
| LangChain | 🟡 | RedFlag, DocForge |
| LlamaIndex | 🟡 | RedFlag (PDF/RAG ingestion) |
| LiteLLM | 🟡 | Switching providers in RootCause |
| Ollama | 🟡 | Free local development (if RAM allows) |
| Groq API (free tier) | 🟡 | Backup provider |
| Hugging Face (transformers, sentence-transformers, datasets, Hub, Spaces) | 🟡 | Embeddings, TriageRouter, free demo hosting |
| Langfuse | 🟡 | RootCause tracing, cost, latency |
| Claude API, OpenAI API | ⚪ | Code supports them; switch when credits are available |
| CrewAI, AutoGen | ⚪ | Learn in 1–2 days if a target company uses them |
| Pinecone, Qdrant, Chroma | ⚪ | Awareness |

## 5. Machine learning, vision, IoT
| Tool | Level | Project |
|---|---|---|
| scikit-learn | 🟢 | Baselines, scoring, clustering |
| PyTorch | 🟡 | TriageRouter, PlateSight, DwellSense |
| OpenCV | 🟡 | PlateSight, DwellSense |
| Ultralytics YOLO | 🟡 | PlateSight, DwellSense |
| statsmodels / SciPy | 🟡 | Anomaly detection, A/B tests |
| LightGBM / Prophet | 🟡 | Forecasting (PlateDemand) |
| MLflow | 🟡 | Experiment tracking |
| OR-Tools, SimPy | 🟡 | Scheduling, simulation (PlateDemand) |
| ONNX | 🟡 | Edge deployment |
| TensorFlow / Keras | ⚪→🟡 | One comparison in TriageRouter |
| MQTT | 🟡 | IoT stream (TurbineSense) |
| Google Colab / Kaggle Notebooks | 🟡 | Free GPU for training |

## 6. Backend
| Tool | Level | Project |
|---|---|---|
| FastAPI | 🟢 | RootCause, most AI APIs |
| Pydantic | 🟢 | FastAPI data validation |
| Django + Django REST Framework | 🟡 | ReplayDesk, Saleor PRs |
| Celery | 🟡 | ReplayDesk |
| Node.js + Express | 🟡 | TriageRouter (MERN), RootCause gateway |
| sqlglot | 🟡 | RootCause SQL guardrails |
| Flask | ⚪ | Awareness |

## 7. Frontend
| Tool | Level | Project |
|---|---|---|
| Streamlit | 🟢 | Quick dashboards and demos |
| React | 🟡 | RootCause UI, TriageRouter |
| Tailwind CSS | 🟡 | Styling |
| Plotly / D3 | 🟡 | Charts |
| Next.js | ⚪ | Awareness |

## 8. Analytics, BI, spreadsheets
| Tool | Level | Project |
|---|---|---|
| Excel / Google Sheets (pivots, XLOOKUP, Power Query) | 🟢 | MarginMap, financial models |
| Power BI (DAX) | 🟡 | MarginMap |
| Looker Studio (free) | 🟡 | Companion Economics |
| GA4 | 🟡 | Funnel Forensics, Companion Economics |
| PostHog | 🟡 | Analytics on your own apps |
| Tableau, Metabase, Mixpanel, Amplitude | ⚪ | Awareness (Tableau Public is free if a JD wants it) |

## 9. Testing and quality
| Tool | Level | Project |
|---|---|---|
| pytest | 🟢 | Every Python project |
| Postman | 🟡 | API testing (SpecCheck, ReplayDesk) |
| Playwright | 🟡 | UI tests (SpecCheck) |
| Jira / Linear (free tier) | 🟡 | Bug logs, backlogs |
| Promptfoo / eval tools | ⚪ | Own eval harness covers this |

## 10. DevOps, cloud, monitoring
| Tool | Level | Project |
|---|---|---|
| Docker + Docker Compose | 🟢 | Every serious project |
| GitHub Actions | 🟡 | CI for tests and evals |
| GCP (pairs with BigQuery and Gemini) | 🟡 | Deployment (Cloud Run) |
| Render / Vercel / Hugging Face Spaces (free hosting) | 🟡 | Live links |
| Neon / Supabase (free Postgres) | 🟡 | Online databases |
| Sentry (free tier) | 🟡 | Error tracking |
| AWS (EC2, S3 basics) | ⚪→🟡 | Many JDs mention it |
| Kubernetes, Datadog, Grafana | ⚪ | Awareness |

## 11. Automation and no-code
| Tool | Level | Project |
|---|---|---|
| n8n | 🟡 | ReplyRadar, Funnel Doctor |
| Zapier (free tier) | 🟡 | One flow |
| v0 / Lovable / Bolt / Replit | 🟡 | Quick prototypes (VoiceLock) |
| Make | ⚪ | Awareness |

## 12. Product, design, documentation
| Tool | Level | Use |
|---|---|---|
| Notion or Obsidian | 🟢 | Notes (daily) |
| Loom | 🟢 | Demos for every project |
| Figma | 🟡 | Wireframes |
| draw.io / Excalidraw | 🟡 | Architecture diagrams, BPMN process maps |

## 13. AI coding and learning tools
| Tool | Level | Use |
|---|---|---|
| Claude Code | 🟢 | Building with a tutor — try first, then review |
| Anki | 🟢 | Spaced-repetition memory |
| LeetCode / DataLemur / SQLBolt | 🟢 | Practice |
| Cursor, Copilot | ⚪ | Try briefly (some JDs mention them) |

---

## Learning order

| Phase | Months | Tools |
|---|---|---|
| Foundations | 1–2 | Python, SQL, Git, command line, VS Code, APIs/JSON, pandas, SQLite, Notion, Anki |
| RootCause core | 3–4 | PostgreSQL, Docker, FastAPI, Pydantic, Gemini API, LangGraph, LiteLLM, sqlglot, pytest, GitHub Actions, Streamlit, Render/HF Spaces |
| RootCause+ | 4–5 | pgvector, Hugging Face embeddings, LlamaIndex, LangChain, Langfuse, BigQuery, React, GCP |
| Core projects | 5–7 | Django, DRF, Celery, Redis, Sentry, scikit-learn, Power BI, Excel, Looker Studio, GA4, n8n, Figma, Postman |
| Specialized projects | 7–10+ | PyTorch, OpenCV, YOLO, ONNX, OR-Tools, SimPy, MLflow, MongoDB, Node/Express, Playwright, Jira |
| Before specific applications | As needed | Snowflake, AWS basics, CrewAI, Tableau — whichever a target company uses |

## When a target company uses a tool you don't know
1. Learn it from the official docs and quickstart (1–2 days).
2. Rebuild one small piece of an existing project with it (1–2 days).
3. Write a short comparison note (e.g. "LangGraph vs CrewAI").
4. Mention it in the application: "I built X with A; since you use B, I rebuilt part of it in B."
