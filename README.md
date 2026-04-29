# Wealth to FIRE

Wealth to FIRE is a comprehensive financial intelligence platform featuring a FastAPI microservices backend and a React (Vite) frontend. The platform helps users simulate FIRE (Financial Independence, Retire Early) goals, optimize loans, and score their financial health.

## Key Features

- **FIRE Calculator**: Estimates the year you can retire based on savings, income, and expenses.
- **Loan Optimizer**: Compares current debt repayment strategies against optimized scenarios.
- **Financial Health Score**: Grades your financial situation out of 100 based on savings and debt ratios.
- **AI Financial Explainability**: Uses LLMs and RAG to break down complex financial concepts.

## Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy, PostgreSQL, Alembic
- **Frontend**: React, TypeScript, Vite, TailwindCSS, Framer Motion, Zustand

## Setup Instructions

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL database (or NeonDB)

### 1. Backend Setup

Navigate to the backend directory:
```bash
cd fire-number--final-year-pro
```

Install dependencies:
```bash
pip install -r requirements.txt
```

Set up your `.env` file (see the Environment Variables section below).

Run the backend server (API Gateway):
```bash
uvicorn api_gateway.main:app --reload --port 8000
```

### 2. Frontend Setup

Navigate to the frontend directory:
```bash
cd frontend
```

Install dependencies:
```bash
npm install
```

Run the development server:
```bash
npm run dev
```

## Environment Variables

Create a `.env` file in the `fire-number--final-year-pro` root directory with the following variables:

```env
# Database Configuration
DATABASE_URL=postgresql+asyncpg://user:password@host/dbname

# API Keys (For AI explanation service)
GEMINI_API_KEY=your_gemini_api_key_here
```

*Note: The frontend does not currently require environment variables out of the box unless specified.*
