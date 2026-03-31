#evaluate_rag.py
from rag_answerer import RAGAnswerer

TEST_QUERIES = [

    "what does ESC do",
    "how to jump start a car",
    "why is my brake warning light on",
    "is there a recall for ABS fire issue",
    "what is roadside assistance coverage",
    "can warranty be transferred",
    "what should owner do for ABS recall",
    "how to install ABS fuse kit",
]

def run_tests():

    rag = RAGAnswerer()

    print("\nRunning RAG evaluation\n")

    for q in TEST_QUERIES:

        print("\nQUESTION:")
        print(q)

        answer = rag.answer(q)

        print("\nANSWER:")
        print(answer)
        print("\n" + "-"*60)


if __name__ == "__main__":
    run_tests()