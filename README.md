# Trading Decision System

A modular and extensible system designed to analyze market structure, identify key supply/demand zones, compute technical indicators, and implement automated or semi-automated trading strategies.

## Folder Structure

```text
Trading-Decision-System/
│
├── backend/
│   ├── app/
│   │   ├── data/             # Data sourcing, ingestion, and preprocessing
│   │   ├── indicators/       # Custom and standard technical indicators
│   │   ├── market_structure/ # Market structure analysis (e.g., MSB, BOS, CHoCH)
│   │   ├── zones/            # Order blocks, supply/demand, and liquidity zones
│   │   ├── strategy/         # Trading strategies and backtesting engine
│   │   ├── utils/            # Shared helper functions and utility modules
│   │   └── api/              # API layer (FastAPI/Flask) for frontend/external communication
│   │
│   ├── tests/                # Unit and integration tests
│   ├── requirements.txt      # Python dependencies
│   └── main.py               # Main application entry point
│
├── frontend/                 # Frontend user interface files
├── docs/                     # Project documentation and specs
└── README.md                 # Project overview and documentation
```

## Getting Started

Detailed setup and usage instructions will be added as components are developed.
