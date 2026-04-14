is entry details a comprehensive survey and comparative analysis of the technological landscape conducted to maximise the theoretical scope of the data pipeline. It evaluates a broad spectrum of candidate libraries, databases, and models, spanning the trajectory from PDF ingestion to disease extraction, to establish a rigorous evidence base that informs subsequent architectural selection.

---

### **Section 1: The "Eyes" (OCR, Layout & Vision)**

*Strategic Goal: To convert pixels into trustworthy text with spatial proof (bounding boxes).*

| **#** | **Function** | **Tool** | **Type** | **Strategic Pro (Why this?)** | **Strategic Con (Risk to Mitigate)** | **Alternatives (Plan B)** | **Citation** |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Optical Character Recognition | **Surya OCR** | Model | **Precision & Speed.** Unlike Tesseract, it detects line-level bounding boxes in one GPU pass, creating a perfect "skeleton" for the document. | **Resource Heavy.** Requires 16GB VRAM for efficiency. If the GPU fails, the pipeline halts. | Tesseract, PaddleOCR | Paruchuri, V. (2024). |
| 2 | Optical Character Recognition | **Marker** | Model | **Math & Speed.** Best-in-class at cleaning messy equations/headers into Markdown. Fast enough to run on every page. | **Heuristic Limits.** Struggles with complex table structures; we rely on it for text, not data grids. It is slower than Docking | Nougat, MinerU | Datalab (2024). |
| 3 | Optical Character Recognition | **Docling** | Model | **The "Second Opinion".** A completely independent parsing engine (IBM). If Marker and Docling agree, the text is ground truth. | **Complexity.** It is complex in setup adds a heavy dependency chain. | Adobe Extract API | Auer, C., et al. (2024). |
| 4 | Optical Character Recognition | **PP-StructureV3** | Model | **Multilingual Robustness.** Excellent at "borderless" tables where Western models fail. Adds diversity to the voting pool. | **Ecosystem Lock.** Uses PaddlePaddle (not PyTorch), requiring a separate container. | TableFormer | Li, C., et al. (2022). |
| 5 | Optical Character Recognition | **Nougat** | Model | **End-to-End.** Good for pure math papers where layout doesn't matter. | **Hallucination Risk.** Generates text without bounding boxes (unverifiable). | Marker | Blecher, L., et al. (2023). |
| 6 | Optical Character Recognition | **Donut** | Model | **OCR-Free.** Skips text recognition, goes straight to JSON. | **Fragile.** Requires massive fine-tuning for each new document type. | Pix2Struct | Kim, G., et al. (2022). |
| 7 | Ingestion Integrity Probe | **pytesseract** | Library | **Reliability.** The "Old Guard." Used *only* to check page rotation before heavy models run. CPU-safe. | **Accuracy.** Too inaccurate for final data extraction; used only for metadata probes. | EasyOCR | Google (2024). |
| 8 | Visual-Semantic Alignment | **Florence-2** | Model | **Semantic Vision.** Can "look" at a page and find "Figure 1" without needing text. **SOTA** for visual search. | **Generative Risk.** It can hallucinate if not strictly prompted. Must be constrained. | LayoutLMv3 | Xiao, B., et al. (2024). |
| 9 | Inference Verification | **Qwen2.5-VL** | Model | **The Tie-Breaker.** If Surya and Marker disagree on a number, this model "looks" at the crop to decide who is right. | **Expensive.** Very slow; only used on the <5% of data where conflicts exist. | Llama-3.2-Vision | Qwen Team (2024). |
| 10 | Document Layout Analysis | **RT-DETR** | Model | **Real-Time Speed.** Identifies headers/footers instantly so we can strip them out. | **Thresholding.** Needs tuning to distinguish "Caption" from "Text". | YOLOv8 | Lv, W., et al. (2023). |
| 11 | Document Layout Analysis | **LayoutLMv3** | Model | **Standard.** The academic baseline for classifying "Title" vs "Paragraph". | **Token Limit.** Can't read a whole dense page (512 tokens max). | LiLT, DiT | Huang, Y., et al. (2022). |
| 12 | Document Layout Analysis | **DiT** | Model | **Vision Only.** Classification without needing OCR text first. | **Blind spots.** Can't read the text content to help classification. | LayoutLMv3 | Li, J., et al. (2022). |
| 13 | PDF Analysis | **PyMuPDF** | Library | **Speed.** The fastest way to turn PDFs into images for the vision models. | **License.** AGPL (strict), but acceptable for academic research. | pdf2image | Artifex (2024). |
| 14 | PDF Analysis | **PyMuPDF** | Library | **Structure Preservation.** Rotates pages without breaking the text layer. | **Ambiguity.** Sometimes metadata rotation conflicts with visual rotation. | QPDF | Artifex (2024). |
| 15 | PDF Analysis | **pdfplumber** | Library | **Debuggability.** Great for visualizing what the computer "sees". | **Sluggish.** Too slow for processing 100k+ pages. | PyMuPDF | Jsvine (2024). |
| 16 | PDF Analysis | **pdf2image** | Library | **Simplicity.** Just wraps Poppler. Rock solid. | **System Dep.** Requires installing Poppler on the OS level. | PyMuPDF | Belval (2024). |

---

### **Section 2: The "Scientists" (Tables, Metadata & Logic)**

*Strategic Goal: To structure unstructured data (Grids and Headers).*

| **#** | **Function** | **Tool** | **Type** | **Strategic Pro (Why this?)** | **Strategic Con (Risk to Mitigate)** | **Alternatives (Plan B)** | **Citation** |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 17 | Table Detection | **TATR-Detect** | Model | **Scientific Bias.** Trained on PubTables-1M, specifically for academic journals. | **Cropping.** Requires perfect image crops; if we clip the edge, detection fails. | YOLO-Table | Smock, B. (2022). |
| 18 | Table Structure | **TATR-Struct** | Model | **Granularity.** Recognizes row spans and column spans (complex headers). | **Textless.** Returns boxes only; we must "inject" text back in from Surya. | TableFormer | Smock, B. (2022). |
| 19 | Table Detection | **TableFormer** | Model | **Drift Resistance.** Better at handling columns that "wave" or drift in scans. | **Integrated.** Hard to use outside of the Docling pipeline. | TATR | Nassar, A. (2022). |
| 20 | Metadata | **GROBID** | Service | **The Specialist.** Unbeaten precision for extracting Titles, DOIs, and Authors. | **Rigid.** If the paper is a non-convensional preprint, it might fail silently. | CERMINE | Lopez, P. (2009). |
| 21 | Metadata | **CERMINE** | Model | **Backup.** Good if GROBID fails on a specific layout. | **Java.** Heavy memory usage (JVM). | CrossRef API | Tkaczyk, D. (2015). |
| 22 | Validation | **Pydantic** | Library | **Contract Enforcement.** Ensures data fits the schema *before* it enters the DB. | **Strictness.** Can cause pipelines to crash on minor whitespace errors. | Marshmallow | Colvin, S. (2024). |
| 23 | Validation | **Pandera** | Library | **Statistical Check.** Checks *values* (e.g., "p-value must be < 1"), not just types. | **Overhead.** Slower on large DataFrames. | GreatExpectations | Bantilan, N. (2020). |
| 24 | Validation | **Marshmallow** | Library | **Legacy.** Good for simple serialization. | **Verbose.** Requires more code than Pydantic. | Pydantic | Marshmallow (2024). |
| 25 | Text Match | **RapidFuzz** | Library | **Verification.** Uses Levenshtein distance to compare Surya vs Marker text. | **Dumb.** Doesn't understand synonyms, only spelling. | FuzzyWuzzy | Bachmann, M. (2024). |
| 26 | Text Match | **FuzzyWuzzy** | Library | **Simple.** Easy API. | **Slow.** Pure Python (slow) vs RapidFuzz (C++). | RapidFuzz | Cohen, A. (2024). |

---

### **Section 3: The "Biologists" (NER, Ontology & Linking)**

*Strategic Goal: To understand that "brca1" is a gene and map it to a global ID.*

| **#** | **Function** | **Tool** | **Type** | **Strategic Pro (Why this?)** | **Strategic Con (Risk to Mitigate)** | **Alternatives (Plan B)** | **Citation** |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 27 | Named Entity Recognition | **BERN2** | Model | **Breadth.** Recognizes 9 types (Gene, Drug, Disease) simultaneously. | **Rate Limits.** The public API is throttled; local setup is hard. | BioBERT | Sung, M. (2022). |
| 28 | Named Entity Recognition | **HunFlair2** | Model | **Consensus.** Uses a different architecture (Flair); great for voting against BERN2. | **Speed.** Slower than transformer-only models. | scispaCy | Sänger, M. (2024). |
| 29 | Named Entity Recognition | **MedCAT** | Model | **Hospital Grade.** The SOTA for mapping text to SNOMED-CT/UMLS. | **Learning Curve.** Requires training on the specific "Meta-Annotation" concept. | cTAKES | Kraljevic, Z. (2021). |
| 30 | Named Entity Recognition | **PubMedBERT** | Model | **Vocabulary.** Trained *only* on medical text (no Wikipedia), so it understands jargon. | **Assembly.** Requires fine-tuning to actually do NER. | BioBERT | Gu, Y. (2022). |
| 31 | Named Entity Recognition | **BioBERT** | Model | **Baseline.** The standard comparison point. | **Outdated.** Outperformed by PubMedBERT in 2024 benchmarks. | BlueBERT | Lee, J. (2020). |
| 32 | Named Entity Recognition | **PubTator** | API | **Gold Standard.** Pre-annotated by NCBI. | **Coverage.** Only covers papers already in PubMed. | BERN2 | Wei, C. (2019). |
| 33 | Named Entity Recognition (Zero-Shot) | **GLiNER** | Model | **Flexibility.** Can find new entities (e.g., "Cohort Size") without retraining. | **Newness.** Less battle-tested than BERT. | ChatGPT (API) | Zaratiana, U. (2024). |
| 34 | Named Entity Recognition (Light) | **scispaCy** | Library | **Preprocessing.** Fast enough to run on millions of sentences for filtering. | **Recall.** Misses complex entities that BERN2 catches. | Spacy-Transformers | Neumann, M. (2019). |
| 35 | Disease Ontology | **DOID** | Ontology | **Hierarchy.** Good for high-level classification (Cancer vs Viral). | **Narrow.** Less granular than MONDO. | ICD-10 | Schriml, L. (2022). |
| 36 | Disease Ontology | **MONDO** | Ontology | **Unification.** The "Rosetta Stone" connecting OMIM, DOID, and ORPHA IDs. | **Flux.** IDs can change between versions. | DOID | Vasilevsky, N. (2022). |
| 37 | Phenotype Onotology | **HPO** | Ontology | **Symptoms.** The standard for "Human Phenotypes" (e.g., HP:000123). | **Incomplete.** Not every disease has a full HPO mapping. | SNOMED | Köhler, S. (2021). |
| 38 | Clinical Ontology | **SNOMED-CT** | Ontology | **Clinical.** Essential if working with hospital records (EHR). | **License.** Requires a license for use. | UMLS | SNOMED Int. (2024). |
| 39 | NLP Framework | **spaCy** | Library | **Engineering.** The "Chassis" that holds the NER models together. | **Generic.** Needs plugins (scispaCy) for bio work. | Stanza | Explosion AI. |
| 40 | NLP Framework | **Flair** | Library | **State of Art.** Research-grade sequence labeling. | **Academic.** Less "production ready" tooling than spaCy. | AllenNLP | Akbik, A. (2019). |

---

### **Section 4: The "Brain" (Retrieval, Storage & Analytics)**

*Strategic Goal: To store data efficiently and identify connections.*

| **#** | **Function** | **Tool** | **Type** | **Strategic Pro (Why this?)** | **Strategic Con (Risk to Mitigate)** | **Alternatives (Plan B)** | **Citation** |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 41 | Search & Retrieval | **ColBERTv2** | Model | **Precision.** Uses "Late Interaction" to match exact numbers/units, not just vague topics. | **Storage.** Index is 10x larger than standard vectors. | Splade | Santhanam, K. (2021). |
| 42 | Search & Retrieval | **Elasticsearch** | Database | **Features.** The most robust engine for full-text search (BM25). | **Maintenance.** Heavy Java process; overkill for small data. | MeiliSearch | Elastic (2024). |
| 43 | Search & Retrieval | **FAISS** | Library | **Scale.** Can search 1 Billion vectors in milliseconds. | **Complexity.** Low-level C++; hard to debug. | Qdrant | Johnson, J. (2019). |
| 44 | Search & Retrieval | **OpenSearch** | Database | **Open Source.** A truly open fork of Elasticsearch. | **Lag.** Features lag behind the proprietary Elastic. | Solr | OpenSearch (2024). |
| 45 | Search & Retrieval | **Typesense** | Database | **UX.** Typo-tolerance out of the box. | **Scale.** Not built for massive scientific aggregation. | Algolia | Typesense (2024). |
| 46 | Search & Retrieval | **Milvus** | Database | **Cloud Native.** Good if we move to a cluster later. | **Overkill.** Too complex for a single PhD server. | Weaviate | Milvus (2024). |
| 47 | Search & Retrieval | **Qdrant** | Database | **Rust.** Fast and safe; good filter support. | **Niche.** Less documentation than FAISS. | Chroma | Qdrant (2024). |
| 48 | Search & Retrieval | **Pinecone** | Service | **Easy.** Managed service. | **Cost.** Expensive for millions of vectors. | Milvus | Pinecone (2024). |
| 49 | Analytics Engine | **DuckDB** | Database | **Local Power.** Processes millions of rows on a laptop (Columnar). No server needed. | **Concurrency.** Only one process can write at a time. | ClickHouse | Raasveldt, M. (2019). |
| 50 | Graph Store | **KuzuDB** | Database | **Simplicity.** An embedded Graph DB (like DuckDB but for graphs). Perfect for simple connections. | **New.** Smaller community than Neo4j. | Neo4j | Kuzu Team (2024). |
| 51 | Relational Store | **PostgreSQL** | Database | **Safety.** The reliable place to store user data and job status. | **Slow Analytics.** Bad for querying millions of gene rows. | MySQL | Postgres Group. |
| 52 | Embedding Model | **SBERT** | Library | **Baseline.** Fast, standard embeddings for general similarity. | **Lossy.** Compresses too much detail for scientific use. | Instructor-XL | Reimers, N. (2019). |

---

### **Section 5: The "Lab Manager" (Ops, Stats & Eval)**

*Strategic Goal: To keep the pipeline running and prove that it works.*

| **#** | **Function** | **Tool** | **Type** | **Strategic Pro (Why this?)** | **Strategic Con (Risk to Mitigate)** | **Alternatives (Plan B)** | **Citation** |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 53 | Workflow Orchestration | **Prefect** | Service | **Modern.** Python-native workflow management; handles retries automatically. | **Backend.** Requires setting up a server for the UI. | Airflow | Prefect (2024). |
| 54 | Workflow Orchestration | **Airflow** | Service | **Enterprise.** The "Big Corp" standard. | **Heavy.** Overkill for a single researcher. | Prefect | Apache (2024). |
| 55 | Workflow Orchestration | **Dagster** | Service | **Data.** Focuses on the "Asset" rather than the "Task". | **Niche.** Steeper learning curve. | Prefect | Dagster Labs (2024). |
| 56 | Message Queue | **RabbitMQ** | Service | **Decoupling.** Buffers jobs so the GPU doesn't crash if 1000 PDFs arrive at once. | **Ops.** Another service to manage/monitor. | Redis Queue | VMware (2024). |
| 57 | Data Processsing | **Pandas** | Library | **Universal.** Every library speaks Pandas. | **Memory.** Can blow up RAM on large datasets. | Polars | McKinney, W. (2010). |
| 58 | Data Processing | **Polars** | Library | **Performance.** Multi-threaded speed for the heavy data lifting. | **API.** Syntax is different from Pandas. | Dask | Vink, R. (2024). |
| 59 | Data Processing | **NumPy** | Library | **Foundation.** The bedrock of all scientific computing in Python. | **Low Level.** We rarely touch it directly, but everything depends on it. | CuPy | Harris, C. (2020). |
| 60 | Evaluation & Validation | **Ragas** | Library | **Methodology.** Algorithmically scores "Faithfulness" (Did we hallucinate?). Essential for the thesis. | **LLM Dep.** Relies on an LLM to do the grading. | TruLens | Es, S. (2024). |
| 61 | Evaluation & Validation | **Stability** | Methodology | **Robustness.** Ensures selected features aren't random noise. | **Compute.** Requires running the model 100x. | Lasso | Meinshausen, N. (2010). |
| 62 | Evaluation & Validation | **Bootstrap** | Methodology | **Confidence.** Generates error bars for our metrics. | **Slow.** Computationally intensive. | Jackknife | Efron, B. (1993). |
| 63 | Modeling & ML | **PyTorch** | Library | **Research.** The standard for all modern AI models. | **Versions.** CUDA version mismatches are a pain. | TensorFlow | Paszke, A. (2019). |
| 64 | Modeling & ML | **Transformers** | Library | **Hub.** Access to 100k+ models (HuggingFace). | **Bloat.** The library is huge and changes often. | Timm | Wolf, T. (2020). |
| 65 | Modeling & ML | **scipy.stats** | Library | **Tests.** Standard t-tests and distributions. | **CPU.** Not accelerated for massive data. | Statsmodels | Virtanen, P. (2020). |
| 66 | Modeling & ML | **statsmodels** | Library | **Diagnostics.** Deep statistical checks (p-values, R-squared). | **Slow.** Slower than sklearn. | Scikit-Learn | Seabold, S. (2010). |
| 67 | Modeling & ML | **scikit-learn** | Library | **Toolbox.** Feature selection and basic ML. | **Simple.** Not for Deep Learning. | XGBoost | Pedregosa, F. (2011). |
| 68 | Visualisation | **Matplotlib** | Library | **Publication.** Total control over every pixel for the thesis. | **Ugly.** Default plots look dated. | Seaborn | Hunter, J. (2007). |
| 69 | Visualisation | **Seaborn** | Library | **Quick.** Beautiful statistical plots instantly. | **Limited.** Hard to customize deeply. | Altair | Waskom, M. (2021). |
| 70 | Visualisation | **Rich** | Library | **Monitoring.** Live progress bars in the terminal. | **Local.** Only visible if watching the screen. | tqdm | McGugan, W. (2024). |

Add MinerU
Add LayoutReader

Add crowd-kit

Add Duckdb