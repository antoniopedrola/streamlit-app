#!/usr/bin/env python3
import os
from supabase import create_client
from sentence_transformers import SentenceTransformer
from tqdm import tqdm # For a nice progress bar

def main():
    print("=" * 60)
    print("🚀 RESEARCH EVIDENCE EMBEDDING PROCESSOR")
    print("=" * 60)

    # 1. Setup Credentials
    URL = input("Enter Supabase URL: ").strip()
    KEY = input("Enter Supabase Anon Key: ").strip()
    supabase = create_client(URL, KEY)

    # 2. Load Model (all-MiniLM-L6-v2 = 384 dimensions)
    print("\n🤖 Loading AI Model...")
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

    # 3. Fetch data missing embeddings
    print("📊 Scanning for items needing embeddings...")
    result = supabase.table("research_evidence")\
        .select("id, content")\
        .is_("embedding", "null")\
        .execute()

    items = result.data
    if not items:
        print("✅ All items already have embeddings!")
        return

    print(f"📦 Found {len(items)} items to process.")

    # 4. Batch Processing Loop
    success_count = 0
    fail_count = 0

    for item in tqdm(items, desc="Generating Embeddings"):
        try:
            # Generate the vector
            vector = model.encode(item['content']).tolist()

            # Save via RPC (Remote Procedure Call)
            # This is the 'secret sauce' that bypasses type-casting errors
            supabase.rpc("update_evidence_embedding", {
                "row_id": item['id'],
                "new_embedding": vector
            }).execute()

            success_count += 1
        except Exception as e:
            print(f"\n❌ Error on ID {item['id']}: {e}")
            fail_count += 1

    print("\n" + "=" * 60)
    print(f"🏁 PROCESSING COMPLETE")
    print(f"✅ Successfully updated: {success_count}")
    print(f"❌ Failed: {fail_count}")
    print("=" * 60)

if __name__ == "__main__":
    main()