#!/usr/bin/env python3
"""
Add Research Evidence with Embeddings

This script adds research evidence (transcripts, quotes, search queries) 
to the database with proper embeddings for semantic search.

Usage:
    python add_evidence.py --file evidence_data.json
    or
    python add_evidence.py --text "Your evidence text" --market korea --type interview_transcript
"""

import os
import sys
import argparse
import json
from datetime import datetime, date
from supabase import create_client
from sentence_transformers import SentenceTransformer

def load_config():
    """Load configuration from environment"""
    from dotenv import load_dotenv
    load_dotenv()
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("❌ Error: SUPABASE_URL and SUPABASE_KEY must be set in .env")
        sys.exit(1)
    
    return supabase_url, supabase_key

def init_services():
    """Initialize Supabase and embedding model"""
    print("🔧 Initializing services...")
    supabase_url, supabase_key = load_config()
    
    supabase = create_client(supabase_url, supabase_key)
    embeddings = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    
    print("✅ Services initialized")
    return supabase, embeddings

def add_single_evidence(supabase, embeddings, market, source_type, content, metadata=None):
    """Add a single evidence item"""
    
    # Validate inputs
    valid_markets = ['korea', 'poland', 'turkey', 'global']
    valid_types = ['interview_transcript', 'social_listening', 'search_query', 'user_quote', 'behavioral_data']
    
    if market not in valid_markets:
        print(f"❌ Invalid market. Must be one of: {valid_markets}")
        return False
    
    if source_type not in valid_types:
        print(f"❌ Invalid source type. Must be one of: {valid_types}")
        return False
    
    print(f"\n📝 Adding evidence...")
    print(f"   Market: {market}")
    print(f"   Type: {source_type}")
    print(f"   Content: {content[:50]}...")
    
    try:
        # Generate embedding
        embedding = embeddings.encode(content).tolist()
        
        # Prepare data
        data = {
            "market": market,
            "source_type": source_type,
            "content": content,
            "embedding": embedding,
            "metadata": metadata or {},
            "source_date": date.today().isoformat(),
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Insert into database
        result = supabase.table("research_evidence").insert(data).execute()
        
        print(f"✅ Evidence added successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error adding evidence: {str(e)}")
        return False

def add_bulk_evidence(supabase, embeddings, file_path):
    """Add multiple evidence items from JSON file"""
    
    print(f"\n📦 Loading evidence from: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            print("❌ JSON file must contain an array of evidence items")
            return
        
        print(f"Found {len(data)} evidence items to process")
        
        success_count = 0
        for i, item in enumerate(data, 1):
            print(f"\n[{i}/{len(data)}]")
            
            market = item.get('market')
            source_type = item.get('source_type')
            content = item.get('content')
            metadata = item.get('metadata', {})
            
            if not all([market, source_type, content]):
                print(f"❌ Skipping item {i}: missing required fields")
                continue
            
            if add_single_evidence(supabase, embeddings, market, source_type, content, metadata):
                success_count += 1
        
        print(f"\n🎉 Complete! Added {success_count}/{len(data)} evidence items")
        
    except FileNotFoundError:
        print(f"❌ File not found: {file_path}")
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON in file: {file_path}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description="Add research evidence to database")
    
    # Single item mode
    parser.add_argument("--text", help="Evidence text content")
    parser.add_argument("--market", help="Market: korea, poland, turkey, or global")
    parser.add_argument("--type", help="Source type: interview_transcript, social_listening, search_query, user_quote, behavioral_data")
    parser.add_argument("--metadata", help="Metadata as JSON string")
    
    # Bulk mode
    parser.add_argument("--file", help="JSON file with bulk evidence data")
    
    args = parser.parse_args()
    
    # Initialize services
    supabase, embeddings = init_services()
    
    # Bulk mode
    if args.file:
        add_bulk_evidence(supabase, embeddings, args.file)
    
    # Single item mode
    elif args.text and args.market and args.type:
        metadata = json.loads(args.metadata) if args.metadata else None
        add_single_evidence(supabase, embeddings, args.market, args.type, args.text, metadata)
    
    else:
        print("❌ Error: Must provide either --file OR (--text + --market + --type)")
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
