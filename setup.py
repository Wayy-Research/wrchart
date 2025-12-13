"""
wrchart - Interactive financial charting for Python

Setup script for installation and distribution.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text() if readme_path.exists() else ""

setup(
    name="wrchart",
    version="0.1.0",
    description="Interactive financial charting library with Polars support and TradingView-style aesthetics",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Wayy Research",
    author_email="contact@wayy.research",
    url="https://github.com/wayy-research/wrchart",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Financial and Insurance Industry",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Office/Business :: Financial :: Investment",
        "Topic :: Scientific/Engineering :: Visualization",
        "Framework :: Jupyter",
    ],
    python_requires=">=3.9",
    install_requires=[
        "polars>=0.20.0",
        "numpy>=1.21.0",
    ],
    extras_require={
        "jupyter": [
            "ipywidgets>=8.0.0",
            "jupyterlab>=4.0.0",
        ],
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "ruff>=0.1.0",
            "mypy>=1.0.0",
        ],
        "all": [
            "ipywidgets>=8.0.0",
            "jupyterlab>=4.0.0",
        ],
    },
    include_package_data=True,
    package_data={
        "wrchart": ["widget/js/*.js"],
    },
    zip_safe=False,
    keywords=[
        "charting",
        "trading",
        "finance",
        "visualization",
        "candlestick",
        "renko",
        "kagi",
        "polars",
        "jupyter",
        "interactive",
    ],
    project_urls={
        "Bug Reports": "https://github.com/wayy-research/wrchart/issues",
        "Documentation": "https://wrchart.readthedocs.io/",
        "Source": "https://github.com/wayy-research/wrchart",
    },
)
