from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="finance-tracker",
    version="0.1.0",
    author="Finance Data Engineering Team",
    author_email="data-eng@company.com",
    description="Event-driven finance data pipeline with visualization and scoring",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/company/finance-tracker",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.11",
    install_requires=[
        "pandas>=2.1.0",
        "pydantic>=2.5.0",
        "boto3>=1.34.0",
        "plotly>=5.17.0",
        "matplotlib>=3.8.0",
        "fastapi>=0.104.0",
        "uvicorn>=0.24.0",
        "pyyaml>=6.0.0",
        "numpy>=1.25.0",
        "scipy>=1.11.0",
        "structlog>=23.2.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.11.0",
            "flake8>=6.1.0",
            "isort>=5.12.0",
            "mypy>=1.7.0",
            "moto>=4.2.0",
        ],
        "docs": [
            "sphinx>=7.1.0",
            "sphinx-rtd-theme>=1.3.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "finance-tracker=src.cli:main",
        ],
    },
)
