---
title: PyData Copilot
emoji: 📊
colorFrom: blue
sdk: docker
app_file: streamlit_app.py
pinned: true
license: apache-2.0
---




# 📊 PyData Copilot

PyData Copilot is a conversational data analysis application designed to streamline the exploration and visualization of complex datasets. Built primarily on a local-first stack, it empowers users to chat with their data using advanced Large Language Models without compromising privacy or requiring external API dependencies. By simply uploading common file formats such as CSV, Excel, or Parquet files, users can instantly retrieve descriptive statistics, execute data transformations, and generate rich visualizations through intuitive natural language prompting. Whether you are a seasoned data scientist or a business analyst, PyData Copilot seamlessly bridges the gap between raw tabular data and actionable insights within a responsive chat interface.



## Technical Architecture

PyData Copilot leverages an object-oriented architecture built with Streamlit for the user experience. The core memory management framework is driven by a LangGraph InMemoryStore. This acts as a custom Retrieval-Augmented Generation (RAG) backend utilizing LangChain and a local Nomic embedding model to maintain a semantically searchable memory store of conversational context, code snippets, and dataset metadata. RAG with semantic search ensures the reasoning engine retains long-term awareness without bloating the context window. 

Data ingestion is securely managed by a polymorphic DatasetHandler abstraction that standardizes the intake, chunking, and validation of tabular structures using Pandas. For code generation and analysis, the application orchestrates a quantized Large Language Model (such as Qwen2.5-Coder) running efficiently on hardware via llama_cpp-python. This permits PyData Copilot to dynamically interpret user intent, generate syntactically correct Python manipulations, execute them in a sandboxed runtime, and display the resulting DataFrame structures or Matplotlib/Seaborn figures in the user interface. The LLM was fine-tuned using Direct Preference Optimization (DPO) on a curated dataset of data analysis prompts and responses to ensure high-quality, "aligned" Python code.


### Architectural Overview Diagram


![PyData Copilot Architecture](<design/PyData Copilot - Overview.png>)



## Demo App

[![Open in HF Spaces](https://huggingface.co/datasets/huggingface/badges/raw/main/open-in-hf-spaces-sm.svg)](https://huggingface.co/spaces/bfavro73/pydataco)


