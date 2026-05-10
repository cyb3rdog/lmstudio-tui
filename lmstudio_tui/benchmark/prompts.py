from __future__ import annotations

BUILTIN: dict[str, list[str]] = {
    "short": [
        "What is 2 + 2?",
        "Name the capital of France.",
        "What color is the sky on a clear day?",
        "How many days are in a week?",
        "What is the boiling point of water in Celsius?",
        "Who wrote Romeo and Juliet?",
        "What is the chemical symbol for gold?",
        "How many continents are there?",
        "What is the speed of light in km/s (approximate)?",
        "What language is spoken in Brazil?",
    ],
    "medium": [
        "Explain the concept of machine learning in 2-3 sentences.",
        "Describe the main differences between Python and JavaScript.",
        "What are the key benefits of containerization in software development?",
        "Summarize how a transformer neural network works.",
        "Explain the CAP theorem in distributed systems.",
        "What is the difference between supervised and unsupervised learning?",
        "Describe what REST APIs are and why they are commonly used.",
        "What is gradient descent and why is it important in ML?",
        "Explain the concept of a context window in large language models.",
        "What are the main differences between SQL and NoSQL databases?",
    ],
    "long": [
        "Write a detailed explanation of how attention mechanisms work in transformer models, "
        "including the concepts of queries, keys, and values.",
        "Compare and contrast convolutional neural networks (CNNs) and recurrent neural networks (RNNs), "
        "discussing their architectures, use cases, strengths, and weaknesses.",
        "Explain the complete lifecycle of a machine learning project from problem definition "
        "to production deployment, including data collection, preprocessing, model selection, "
        "training, evaluation, and monitoring.",
        "Describe the history and evolution of natural language processing, starting from rule-based "
        "systems through statistical methods to modern large language models.",
        "Write a thorough explanation of the RLHF (Reinforcement Learning from Human Feedback) "
        "technique used to fine-tune large language models, explaining each step of the process.",
    ],
    "code": [
        "Write a Python function that implements binary search on a sorted list.",
        "Implement a simple LRU cache in Python using only built-in data structures.",
        "Write a Python async function that fetches JSON from a URL with a timeout and retry logic.",
        "Implement a basic thread-safe queue in Python.",
        "Write a Python decorator that measures and prints the execution time of a function.",
    ],
}

BUILTIN["mixed"] = (
    BUILTIN["short"][:4]
    + BUILTIN["medium"][:4]
    + BUILTIN["long"][:2]
    + BUILTIN["code"][:2]
)


class PromptLibrary:
    @staticmethod
    def load(name_or_path: str) -> list[str]:
        if name_or_path in BUILTIN:
            return BUILTIN[name_or_path]
        import json
        from pathlib import Path
        path = Path(name_or_path).expanduser()
        if path.suffix == ".json":
            return json.loads(path.read_text())
        return [line.strip() for line in path.read_text().splitlines() if line.strip()]
