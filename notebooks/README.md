# Notebooks

Jupyter notebooks for exploration, analysis, and experimentation.

## Purpose

Interactive notebooks for:
- Data exploration and profiling
- Embedding quality analysis
- Search accuracy evaluation
- Performance benchmarking
- Prototype development

## Notebooks

- `01_data_exploration.ipynb`: Explore SFDC case data
- `02_pii_analysis.ipynb`: Analyze PII patterns and detection
- `03_embedding_quality.ipynb`: Evaluate embedding quality
- `04_search_accuracy.ipynb`: Test search precision/recall
- `05_performance_analysis.ipynb`: Analyze system performance
- `06_case_similarity.ipynb`: Explore case similarity metrics

## Setup

```bash
# Install Jupyter
pip install jupyter

# Start Jupyter server
jupyter notebook

# Or use JupyterLab
jupyter lab
```

## Dependencies

Notebooks use the same dependencies as the main project:
- pandas, numpy for data manipulation
- matplotlib, seaborn for visualization
- weaviate-client for vector database queries
- transformers for embedding models

## Data Access

Notebooks connect to:
- Development Weaviate instance
- Test data in `/data/test_datasets/`
- Processed data in `/data/processed/`
