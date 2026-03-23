from transformers import pipeline
from pdf2image import convert_from_path
from pypdf import PdfReader
import json

def pdf_to_images(pdf_path):
    return convert_from_path(pdf_path)

def docx_to_images(docx_path):
    raise NotImplementedError("This functionality requires MS Word to be installed. This would add bloat in this project, so I bypassed it for now. In a stable environment, can install Word and implement this simple method.")

def load_document_images(path):
    if path.lower().endswith(".pdf"):
        return pdf_to_images(path)
    elif path.lower().endswith(".docx"):
        return docx_to_images(path)
    else:
        raise ValueError("Unsupported file type")

def get_relevant_pages(pdf_path, terms, top_k=3):
    '''
    For more efficient, prioritised page search.
    For each queried field, if search terms are provided: 
    Finds the pages with the highest occurence of that term.
    Works only with pdf files because docx not supported at the moment.

    Args:
        pdf_path : str
            pdf file path
        terms : dict
            Dictionary of queried fields and their respective search terms

    Returns:
        Dictionary of queries and list of best page candidates
    '''
    reader = PdfReader(pdf_path)
    num_pages = len(reader.pages)
    
    # extract all page texts once
    page_texts = []
    for page in reader.pages:
        text = page.extract_text() or ""
        page_texts.append(text.lower())
    
    results = {}
    
    for field, keywords in terms.items():
        # if [""] return all pages
        if keywords == [""] or not any(k.strip() for k in keywords):
            results[field] = list(range(num_pages))
            continue
        
        page_scores = []
        
        for i, text in enumerate(page_texts):
            score = 0

            for kw in keywords:
                if kw == "#num":
                    score += sum(c.isdigit() for c in text)
                elif kw and kw.lower() in text:
                    score += 1
            page_scores.append((i, score))
        
        page_scores = sorted(page_scores, key=lambda x: x[1], reverse=True)
        
        pages = [i for i, score in page_scores if score > 0][:top_k]
        
        results[field] = pages if pages else list(range(num_pages))
    
    return results






qa = pipeline(
    "document-question-answering",
    model="impira/layoutlm-invoices"
)

def ask_doc_questions(path, questions, terms, verbose=0, progress_callback=None):
    """
    Using huggingface model searches the document pdf for queried terms.

    Args:
        path : str
            pdf file path
        questions : dict
            Dictionary of queried fields, and their respective LLM questions
        terms : dict
            Dictionary of queried fields and their respective search terms (passed to get_relevant_pages)
        verbose = 0 : int
            Print progress to CLI
        progress_callback = None : func
            Streamlit interface progress object

    Returns:
        results : dict{question:list}
            Dictionary of queried fields, and a list containing the answer, confidence level, page where found
        page_map : dict
            Output of get_relevant_pages. Dictionary of queried fields, and best candidate pages.
    """
    images = load_document_images(path)
    num_pages = len(images)
    
    # align terms with questions (in case missing search terms)
    aligned_terms = {}
    for key in questions:
        aligned_terms[key] = terms.get(key, [""])
    
    # only applies to PDFs
    if path.lower().endswith(".pdf"):
        page_map = get_relevant_pages(path, aligned_terms) # get_relevant_pages only works on pdf files
    else:
        page_map = {k: list(range(len(images))) for k in questions} # otherwise search everywhere
    
    results = {}
    if verbose:print(page_map)
    
    total = len(questions) * num_pages

    for i, (q_key, q_text) in enumerate(questions.items()):
            if verbose: print(q_key)
            best_answer = None
            best_score = -1
            best_page = -1
            
            primary_pages = page_map[q_key]
            remaining_pages = [i for i in range(num_pages) if i not in primary_pages]
            
            # first pass: suggested pages
            for page_idx in primary_pages:
                if progress_callback:
                    progress_callback((i*num_pages + page_idx)/ total)
                if verbose: print(page_idx)
                out = qa(question=q_text, image=images[page_idx])[0]
                
                # Find the best score answer
                if out["score"] > best_score:
                    best_score = out["score"]
                    best_answer = out["answer"]
                    best_page = page_idx
                
                if best_score > 0.98:
                    break # Early Stopping if confidence is over 0.98

            # Failsafe: if get_relevant_pages didn't produce good answers, search remaining pages
            if best_score < 0.8:
                for page_idx in remaining_pages:
                    if progress_callback:
                        progress_callback((i*num_pages + page_idx)/ total)
                    if verbose: print('failsafe:', page_idx)
                    out = qa(question=q_text, image=images[page_idx])[0]
                    
                    # Find best score
                    if out["score"] > best_score:
                        best_score = out["score"]
                        best_answer = out["answer"]
                        best_page = page_idx
                    
                    if best_score > 0.98:
                        break
            if progress_callback:
                progress_callback(1.0)
            
            results[q_key] = {"answer": best_answer, "score" : best_score, "page" : best_page+1}
    
    return results, page_map


def save_results_to_json(results, output_path):
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

