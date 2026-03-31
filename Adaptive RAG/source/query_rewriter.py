# query_rewriter.py

import re

# ---------------------------------------------------
# Abbreviation expansion
# ---------------------------------------------------

ABBREVIATIONS = {
    "abs": "anti lock braking system",
    "esc": "electronic stability control",
    "epb": "electronic parking brake",
    "rsa": "roadside assistance",
}

# ---------------------------------------------------
# Synonym expansion
# ---------------------------------------------------

SYNONYMS = {

    "jump start": [
    "battery jump start procedure",
    "jump starting vehicle",
    "jump starting procedure",
    "jump start battery"
    ],

    "brake light": "brake warning light indicator",

    "warranty": "vehicle warranty coverage",
    "coverage": "warranty coverage",

    "recall": "vehicle safety recall"
}

# ---------------------------------------------------
# Intent keywords
# ---------------------------------------------------

INTENT_KEYWORDS = {
    "recall": ["recall", "fire risk", "safety defect"],
    "warranty": ["warranty", "coverage", "covered"],
    "manual": ["how", "procedure", "what does"],
}

# ---------------------------------------------------
# Normalization
# ---------------------------------------------------

def normalize_query(query):

    query = query.lower()

    query = re.sub(r"[^\w\s]", " ", query)

    query = re.sub(r"\s+", " ", query)

    return query.strip()


# ---------------------------------------------------
# Expand abbreviations
# ---------------------------------------------------

def expand_abbreviations(query):

    words = query.split()

    expanded = []

    for w in words:

        if w in ABBREVIATIONS:
            expanded.append(ABBREVIATIONS[w])

        expanded.append(w)

    return " ".join(expanded)


# ---------------------------------------------------
# Synonym expansion
# ---------------------------------------------------

def synonym_expand(query):

    expanded_queries = [query]

    for key, values in SYNONYMS.items():

        if key in query:

            if isinstance(values, list):

                for v in values:
                    expanded_queries.append(query.replace(key, v))

            else:
                expanded_queries.append(query.replace(key, values))

    return expanded_queries


# ---------------------------------------------------
# Multi-intent split
# ---------------------------------------------------

def split_intents(query):

    separators = [" and ", " but ", " also "]

    for sep in separators:

        if sep in query:

            parts = query.split(sep)

            return [p.strip() for p in parts]

    return [query]


# ---------------------------------------------------
# Main rewrite function
# ---------------------------------------------------

def rewrite_query(query):

    query = normalize_query(query)

    query = expand_abbreviations(query)

    intent_parts = split_intents(query)

    rewritten = []

    for part in intent_parts:

        expanded = synonym_expand(part)

        rewritten.extend(expanded)

    # remove duplicates
    rewritten = list(set(rewritten))

    return rewritten


# ---------------------------------------------------
# Debug
# ---------------------------------------------------

if __name__ == "__main__":

    q = input("Enter query: ")

    rewritten = rewrite_query(q)

    print("\nRewritten queries:")

    for r in rewritten:
        print("-", r)