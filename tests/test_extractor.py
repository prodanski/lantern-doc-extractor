from extractor import get_relevant_pages
from extractor import ask_doc_questions

class DummyPage:
    def __init__(self, text):
        self._text = text

    def extract_text(self):
        return self._text

class DummyReader:
    def __init__(self, texts):
        self.pages = [DummyPage(t) for t in texts]


def test_get_relevant_pages_basic(monkeypatch):
    texts = [
        "this is page one with iban 123",
        "this is page two with email test@test.com",
        "nothing useful here"
    ]

    def mock_reader(path):
        return DummyReader(texts)

    monkeypatch.setattr("extractor.PdfReader", mock_reader)

    terms = {
        "bank": ["iban"],
        "email": ["@"]
    }

    result = get_relevant_pages("dummy.pdf", terms, top_k=1)

    assert result["bank"] == [0]
    assert result["email"] == [1]


def test_get_relevant_pages_num(monkeypatch):
    texts = [
        "no numbers",
        "123 456 789",
        "1"
    ]

    def mock_reader(path):
        return DummyReader(texts)

    monkeypatch.setattr("extractor.PdfReader", mock_reader)

    terms = {"amount": ["#num"]}

    result = get_relevant_pages("dummy.pdf", terms, top_k=1)

    assert result["amount"] == [1]  # most digits


from extractor import ask_doc_questions

def test_ask_doc_questions_basic(monkeypatch):
    # mock images
    monkeypatch.setattr("extractor.load_document_images", lambda path: ["img1", "img2"])

    # mock page selection
    monkeypatch.setattr("extractor.get_relevant_pages", lambda path, terms: {
        "email": [0]
    })

    # mock QA model
    def mock_qa(question, image):
        return [{"answer": "test@test.com", "score": 0.99}]

    monkeypatch.setattr("extractor.qa", mock_qa)

    questions = {"email": "What is the email?"}
    terms = {"email": ["@"]}

    results, _ = ask_doc_questions("file.pdf", questions, terms)

    assert results["email"]["answer"] == "test@test.com"
    assert results["email"]["score"] > 0.9