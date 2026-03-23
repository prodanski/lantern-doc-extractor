# Setup & Running Instructions
This projct is a document exctraction pipeline that uses an OCR + small LLM to extract structured data from PDF contract documents.

## 1. Clone 
`git clone https://github.com/prodanski/lantern-doc-extractor your_dir`

`cd your_dir`

## 2. Install Dependencies
This project requires *poppler* for PDF -> image conversion.

`brew install poppler`

## 3. UV
Install uv if not already installed:`brew install uv`

then

`uv python install`

`uv sync`

## 4. Bring data
Place your PDF files inside a new folder, e.g. data.

_Recommendation: Name your pdf files something without spaces, a lot easier to use CLI then._

## 5. Run the extraction pipeline:
`uv run python src/main.py --doc data/your_document.pdf`

## 6. Output
Results are saved in the same project root directory, in the folder `outputs`. There should be .json files with the same filename as the document.

Each extracted field includes:
* Queried field
* answer
* score
* page (page where best answer found)

# Notes:
* The `outputs/` directory must exist (included in repo)
* The `data/` directory excluded from version control. You have to copy in your own data documents.
* First run may take longer due to model weight download (HuggingFace)

## Streamlit app:
Instead of step 5, run

`uv run streamlit run src/app.py`

It is a much more user-friendly experience. The user can customise the things they want to extract, have a progress bar, and can download the extracted fields to excel.
**For ease, a button called `Demo Fields` was added. It automatically fills-in the fields required by the task description.**
**Debugging**: If you get an `.../.venv/bin/python3: cannot execute: No such file or directory` error, try running:

`uv venv` -> when prompted, hit `[y]`



# Approach and Design Decisions:
### Overview:
The aim of this project is to extract structured data from semi-structured contracts. These documents can vary significantly in format, layout, wording, so a regex or rules-based approach is unsustainable.

To address this, I set up an OCR + small LLM pipeline.

The user can query the LLM with a question that should extract the desired field, e.g.:

`investor_email : "What is the investor email address?`

See `config/extraction_config.json['questions']` for definition.

### 1. Document Ingestion:
* Input documents (PDF) are converted into images using pdf2image. This is required by the LLM, which operates on visual document structure rather than raw text;

**Rationale**: Traditional text extraction can fail on complex layouts. HuggingFace has visual models specifically optimised for visual structure extraction.

### 2. Page Prioritisation Helper:
The pipeline extracts the raw text from the pdf files.

Before querying the model on every page for every field, the pipeline narrows down potential candidates:
* Fields are associated with potential keywords (e.g. `investor_email: ["@"], bank_name: ["bank", "building society"]`)
* Pages are scored based on keyword density
* The keyword `#num` can be used for searching pages with high numeric density

This produces a `page_map`: Top 3 potential page candidates for that field.

This step is entirely optional: if a field doesn't have suggested keywords, or they are not found altogether, the model defaults to searching the entire document. See more about fallback in the next section.

**Rationale**: Running an LLM accross every page is expensive and slow. With the sample keywords provided in the config, the pipeline runs **3x faster**

### 3. LLM-Based Extraction:
For each field:
* LLM is asked a natural question (e.g. `What is the account number?`)
	* For each page in `page_map` it evaluates the question
	* If answer (`score>0.8`) is found, return best answer
	* _Fallback:_ If no satisfying answer found, evaluate the question on the remaining pages in the document
* _Early stopping_: If `score>0.98`

**Rationale**: Using a question-answering paradigm:
* No brittle regex/rules-based extraction
* Allows easy addition of new fields
* Generalises well accross visually formatted documents

### 4. Output:
Results are returned and saved as JSON.
* field_name: Bank Name
	* answer: Lloyds
	* score: 0.98412
	* page: 13

# Limitations and further improvemens:
* **.docx support**: Currently this pipeline only supports pdf files. The method for docx support is referenced, but raises `NotImplementedError`. Docx parsing has MS-Word dependency, and I don't have it on this machine. LibreOffice could be used, but it is an unnecesary complication and adds further niche system dependencies (non-uv). 
* **top-N answers**: Currently this pipeline only stores the best found answer per field. Could save top-N answers per field.
* **validation layer**: With more time, I would implement some sort of cleaning layer on the output. For example, querying "What currency is the commitment in?" yields "EURO 10,000,000", instead of just "EURO". A method to clean the output (in this case strip away digit characters) to match the expected format could be used.
* **model choice**: The model chosen was a light model to ensure cross-platform support. With more compute, a stronger LLM could be used (e.g. GPT-based or fine-tuned LayoutLM)
* **batch processing**: This is single file, single, query, single page. With more time, especially on a light model such as this, batch processing could be implemented.
* **evaluation**: Introduce evaluation framework with ground truth labels (assuming such data exists)
* **containerisation**: E.g. Docker for consistent deployment.