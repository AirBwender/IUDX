# IUDX Metadata Automation

Hey there! I'm **Rahul Palaniappan**, an Applied AI/ML intern at India Urban Data Exchange (IUDX), and this repo showcases my work on automating metadata generation for IUDX and GDI datasets.

## Project Overview

This project builds a pipeline to convert structured data (e.g., GeoJSON) into IUDX-compliant JSON-LD metadata, using Large Language Models (LLaMA-3 via Groq) for high-accuracy type inference and validation. The system infers `dataSchema` types (e.g., `iudx:Text`, `iudx:Number`) and validates outputs for structural and semantic correctness, making IUDX’s data management scalable and efficient.

## Workflow

Here’s the pipeline that makes the magic happen:

```
GeoJSON/Raw Dataset
       |
       v
LLM-based JSON-LD Generation
       |
       v
Schema Validation & Evaluation
       |
       v
Schema Valid? ---- Yes ----> Accept & Save JSON-LD
       |                      ^
       No                     |
       v                      |
Fix or Refine Schema --------|
       |
       v
Re-run Evaluation
       |
       v
End
```

## Technologies Used

- **Python**: pandas, scikit-learn, json, and more.
- **Groq**: For LLaMA-3 inference.
- **Google Colab**: Jupyter notebooks for fine-tuning.
- **JSON-LD & RDF Tools**: For IUDX-compliant metadata.
- **Custom Validators**: Ensuring structural and semantic correctness.

## Impact

This pipeline automates metadata generation, slashing manual effort and boosting scalability for IUDX. The LLM-based approach nails complex schemas, enabling seamless integration into IUDX’s platform for better data discovery and interoperability.