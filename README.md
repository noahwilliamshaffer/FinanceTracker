# Finance Tracker - Event-Driven Data Pipeline

A production-ready finance data pipeline for Treasury and repo market data processing, visualization, and scoring.

## Architecture Overview

- **Event-Driven Pipeline**: AWS EventBridge → Lambda for data fetching and updates
- **Data Storage**: Partitioned CSVs in S3 with versioning, encryption, and audit trails
- **Visualizations**: Interactive dashboards using Plotly/Matplotlib
- **Scoring Models**: Configurable internal scoring with YAML-based weights

## Features

### Data Pipeline
- Treasury and repo market data ingestion
- CUSIP, maturity, coupon, BVAL price tracking
- Discount price, dollar price, and internal pricing
- Day-over-day change calculations
- Audit-ready practices with immutable logs

### Visualizations
- Time-series Treasury prices per CUSIP
- Repo spread trend analysis
- Internal vs BVAL pricing divergence charts
- FastAPI web interface with HTML templates

### Scoring Models
- Configurable market signal weighting
- Repo spread analysis
- BVAL vs internal pricing divergence scoring
- YAML-based configuration management

## Quick Start

### Prerequisites
- Python 3.11+
- AWS CLI configured
- Terraform installed
- Docker (optional)

### Local Development

```bash
# Clone and setup
git clone <repo-url>
cd FinanceTracker
make setup

# Run tests
make test

# Start local development server
make dev

# Deploy infrastructure
make deploy
```

### Infrastructure Deployment

```bash
# Initialize Terraform
cd infra/terraform
terraform init

# Plan deployment
terraform plan

# Deploy
terraform apply
```

## Project Structure

```
FinanceTracker/
├── src/                    # Application source code
│   ├── models/            # Pydantic data models
│   ├── pipeline/          # Data pipeline components
│   ├── visualization/     # Dashboard and plotting
│   ├── scoring/           # Internal scoring models
│   └── api/              # FastAPI application
├── infra/                 # Infrastructure as Code
│   └── terraform/        # Terraform configurations
├── tests/                 # Test suite
├── samples/              # Sample data for local development
├── config/               # Configuration files
├── docs/                 # Documentation
├── .github/              # GitHub Actions workflows
├── Makefile              # Build automation
└── requirements.txt      # Python dependencies
```

## Configuration

Configuration is managed through YAML files in the `config/` directory:

- `config/scoring.yaml` - Scoring model weights and parameters
- `config/app.yaml` - Application configuration
- `config/aws.yaml` - AWS service configurations

## Testing

```bash
# Run all tests
make test

# Run with coverage
make test-coverage

# Run specific test module
pytest tests/test_scoring.py -v
```

## CI/CD

GitHub Actions workflows automatically:
- Run linting and formatting checks
- Execute test suite
- Validate Terraform configurations
- Deploy to staging/production environments

## License

MIT License - see LICENSE file for details
