import json
import argparse
from extractor import ask_doc_questions, save_results_to_json

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--doc", required=True, help="Path to document")
    parser.add_argument("--config", default="config/extraction_config.json")
    parser.add_argument("--json_output_address", type=str, default='output.json')
    parser.add_argument("--verbose", type=int, default=0)

    args = parser.parse_args()

    with open(args.config, "r") as f:
        cfg = json.load(f)

    questions = cfg["questions"]
    terms = cfg["terms"]

    results, pages = ask_doc_questions(
        args.doc,
        questions,
        terms,
        args.verbose
    )

    output_address = cfg["json_output_address"] + "/" + args.doc.split("/")[-1].split(".")[0] + ".json"

    print(json.dumps(results, indent=2))
    save_results_to_json(results, output_address)


if __name__ == "__main__":
    main()