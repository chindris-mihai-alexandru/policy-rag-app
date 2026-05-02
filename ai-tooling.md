# AI Tooling — How AI Was Used in This Project

## Overview

This project was built with extensive AI assistance, as encouraged by the project guidelines. The AI tools used fell into two categories: code generation and content generation.

## Tools Used

### 1. AdaL (SylphAI's AI Agent) — Primary Development Tool

**Role**: End-to-end project planning, code generation, content creation, and deployment orchestration.

**What it did well**:
- **Project planning**: Generated a comprehensive project plan with architecture decisions, folder structure, and implementation sequence before writing any code.
- **Synthetic corpus generation**: Created 10 coherent, cross-referenced policy documents (~2,500 lines of markdown) for the fictional "Acme Corp" company. The documents are internally consistent — e.g., the PTO policy references the holiday schedule, the expense policy references the remote work equipment stipend, and policy IDs cross-reference correctly.
- **Code generation**: Produced all Python source code (Flask app, LangChain RAG pipeline, ChromaDB ingestion, guardrails), frontend code (HTML/CSS/JS chat interface), test suites (30 tests), CI/CD workflows, and evaluation scripts.
- **Deployment configuration**: Generated render.yaml, Procfile, and GitHub Actions workflows matching the existing deployment pattern from a reference project.
- **Documentation**: Created README.md, this file, design-and-evaluation.md, and the evaluation question set.

**What required iteration**:
- Initial test assertions needed minor adjustments (e.g., string length boundary in truncation test was off by ~11 characters).
- ChromaDB API compatibility required checking — the `list_collections()` return type changed between versions.

### 2. Web Search — Research and Verification

**Role**: Confirming technology decisions and finding open-source policy document references.

**Specific uses**:
- Verified Groq and OpenRouter free tier availability and rate limits
- Found open-source HR policy templates on GitHub (OpenGov Foundation, Center for Open Science) as structural references for the synthetic corpus
- Confirmed current LangChain, ChromaDB v0.6.x, and FastEmbed API compatibility
- Researched DigitalOcean App Platform buildpack behavior and Python runtime version support during Render → DO migration

### 3. Claude / GPT Models — Referenced for Model Selection

The project plan includes model recommendations for different task types (e.g., extended context models for corpus generation), though the actual implementation was done end-to-end by AdaL.

## AI's Contribution Breakdown

| Component | AI Contribution | Human Review |
|-----------|----------------|-------------|
| Project plan & architecture | 95% AI-generated | Reviewed and approved |
| Policy corpus (10 docs) | 100% AI-generated | Reviewed for consistency |
| Python source code | 95% AI-generated | Tested and verified |
| Frontend (HTML/CSS/JS) | 100% AI-generated | Visual review |
| Tests (30 cases) | 95% AI-generated | Run and verified |
| CI/CD workflows | 90% AI-generated, 10% adapted from reference | Verified against reference |
| Evaluation questions | 100% AI-generated | Reviewed against corpus |
| Documentation | 95% AI-generated | Reviewed and edited |

## Key Takeaway

AI code generation tools are highly effective for:
1. **Scaffolding**: Rapidly creating project structure, boilerplate, and configuration files
2. **Content generation**: Creating realistic synthetic data (policy documents) with internal consistency
3. **Test writing**: Generating comprehensive test suites that cover edge cases
4. **Documentation**: Producing clear, well-structured documentation

Human oversight remains essential for:
1. **Architecture decisions**: AI proposes, human validates against requirements
2. **Quality verification**: Running tests, checking for regressions, verifying deployment
3. **Security review**: Ensuring no secrets are committed, API keys are properly managed
4. **Business logic validation**: Confirming the corpus content makes sense and is internally consistent
