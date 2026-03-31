# feedback_logger.py
import json
from datetime import datetime

def log_feedback(query, answer, feedback):

    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "query": query,
        "answer": answer,
        "feedback": feedback
    }

    with open("feedback_log.json", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")