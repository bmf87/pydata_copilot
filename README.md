---
title: PyData Copilot
emoji: 📊
colorFrom: blue
sdk: streamlit
sdk_version: 1.25.0
app_file: streamlit_app.py
pinned: true
license: apache-2.0
---




# 📊 PyData Copilot

PyData Copilot is a conversational data analysis application designed to streamline the exploration and visualization of complex datasets. Built primarily on a local-first stack, it empowers users to chat with their data using advanced Large Language Models without compromising privacy or requiring external API dependencies. By simply uploading common file formats such as CSV, Excel, or Parquet files, users can instantly retrieve descriptive statistics, execute data transformations, and generate rich visualizations through intuitive natural language prompting. Whether you are a seasoned data scientist or a business analyst, PyData Copilot seamlessly bridges the gap between raw tabular data and actionable insights within a responsive chat interface.


## Demo App

[![Open in HF Spaces](https://huggingface.co/datasets/huggingface/badges/raw/main/open-in-hf-spaces-sm.svg)](https://huggingface.co/spaces/bfavro73/pydataco)



## Technical Architecture

PyData Copilot leverages an object-oriented architecture built with Streamlit for a responsive user experience. The core memory management framework is driven by an InMemoryStore. This is a custom Retrieval-Augmented Generation (RAG) backend utilizing LangChain and local Nomic embedding models to maintain a semantically searchable memory store of conversational context, code snippets, and dataset metadata. This ensures the reasoning engine retains long-term awareness without bloating the context window. 

Data ingestion is securely managed by a polymorphic DatasetHandler abstraction that standardizes the intake, chunking, and validation of tabular structures using Pandas. For code generation and analysis, the application orchestrates a quantized Large Language Model (such as Qwen) running efficiently on CPU hardware via llama_cpp-python. This allows PyData Copilot to dynamically interpret user intent, generate syntactically correct Python manipulations, execute them in a sandboxed runtime, and intelligently display the resulting DataFrame structures or Matplotlib/Seaborn figures directly in the user interface. The LLM was fine-tuned using DPO on a curated dataset of data analysis prompts and responses to ensure high-quality, "aligned" Python code generation and analysis.