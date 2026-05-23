import os
from dotenv import load_dotenv
from supabase import create_client
from openai import OpenAI


load_dotenv()

# Load env
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Clients
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
client = OpenAI(api_key=OPENAI_API_KEY)

print("URL:", SUPABASE_URL)
print("KEY:", SUPABASE_KEY[:10] if SUPABASE_KEY else None)

def get_embedding(text):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding


# 1️⃣ Insert candidate
def insert_candidate(name, resume):
    embedding = get_embedding(resume)

    data = {
        "name": name,
        "resume": resume,
        "embedding": embedding
    }

    supabase.table("candidates").upsert(
        data,
        on_conflict="name"
    ).execute()
    print(f"Inserted: {name}")


# 2️⃣ Search candidates
def search_candidates(query):
    query_embedding = get_embedding(query)

    response = supabase.rpc(
        "match_candidates",
        {"query_embedding": query_embedding}
    ).execute()

    print("\nTop Matches:")
    for r in response.data:
        print(r)


if __name__ == "__main__":
    # Insert test data
    insert_candidate("Alice", "Python developer with ML experience")
    insert_candidate("Bob", "Frontend React developer")
    insert_candidate("Charlie", "Backend engineer with APIs and databases")

    # Search
    search_candidates("Looking for backend engineer")