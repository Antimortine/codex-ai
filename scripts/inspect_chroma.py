# Copyright 2025 Antimortine (antimortine@gmail.com)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import chromadb
import sys
import argparse # Import argparse
from pathlib import Path # Import Path

# --- Configuration (Match IndexManager) ---
# Assume script is run from the root 'scripts/' directory
DEFAULT_CHROMA_PERSIST_DIR = "../backend/chroma_db"
DEFAULT_CHROMA_COLLECTION_NAME = "codex_ai_documents"

def inspect_chroma(db_path: str, collection_name: str, project_id_filter: str | None = None, limit: int = 5):
    """
    Connects to a persistent ChromaDB collection, displays its total count,
    and shows sample documents, optionally filtering by project_id.
    """
    try:
        resolved_db_path = Path(db_path).resolve()
        print(f"Connecting to ChromaDB at: {resolved_db_path}")
        if not resolved_db_path.exists() or not resolved_db_path.is_dir():
            print(f"Error: ChromaDB persistence directory not found at '{resolved_db_path}'.", file=sys.stderr)
            print("Please ensure the backend has run at least once to create the database or provide the correct path via --db-path.", file=sys.stderr)
            sys.exit(1)

        client = chromadb.PersistentClient(path=str(resolved_db_path)) # Use resolved path string

        print(f"Getting collection: {collection_name}")
        try:
            # Use get_collection to ensure it exists
            collection = client.get_collection(name=collection_name)
        except Exception as e:
            print(f"Error: Could not get collection '{collection_name}'. Does it exist?", file=sys.stderr)
            print(f"Details: {e}", file=sys.stderr)
            sys.exit(1)

        # --- Filtering Logic ---
        where_filter = None
        if project_id_filter:
            where_filter = {"project_id": project_id_filter}
            print(f"\nApplying filter: project_id == '{project_id_filter}'")

        count = collection.count() # Total count in the collection
        print(f"\nCollection '{collection_name}' found with {count} total documents.")

        # Get filtered count if applicable
        filtered_count = count
        if where_filter:
            try:
                # Getting filtered results just to count is inefficient, but count() doesn't take where
                # A more efficient way might involve querying with limit=0 and checking metadata,
                # but ChromaDB's API for filtered count isn't direct. Let's get IDs.
                filtered_ids = collection.get(where=where_filter, include=[])['ids']
                filtered_count = len(filtered_ids)
                print(f"Found {filtered_count} documents matching the filter.")
            except Exception as e:
                 print(f"Warning: Could not accurately determine filtered count. Error: {e}", file=sys.stderr)
                 # Proceed to try and get data anyway

        if filtered_count > 0:
            print(f"\nGetting first few documents (limit {limit})" + (f" matching filter:" if where_filter else ":"))
            # Peek doesn't support where filters directly as of chromadb 0.4.x
            # We need to use get() with the filter
            results = collection.get(
                where=where_filter, # Apply filter here
                limit=limit,
                include=["metadatas", "documents"] # Specify what to include
            )

            print("\n--- Sample Data ---")
            if results and results.get("ids"):
                 num_results = len(results["ids"])
                 print(f"(Showing {num_results} out of {filtered_count} matching documents)")
                 for i, doc_id in enumerate(results["ids"]):
                      print(f"ID: {doc_id}")
                      if results.get("metadatas") and len(results["metadatas"]) > i:
                           print(f"  Metadata: {results['metadatas'][i]}")
                      if results.get("documents") and len(results["documents"]) > i:
                           doc_content = results['documents'][i] or "" # Handle potential None
                           print(f"  Document: {doc_content[:150]}{'...' if len(doc_content) > 150 else ''}")
                      print("-" * 10)
            else:
                 print("No documents found matching the criteria or results format unexpected.")
            print("-------------------")
        elif count > 0 and where_filter:
             print("No documents found matching the specified filter.")
        # --- End Filtering Logic ---

    except Exception as e:
        print(f"\nAn error occurred: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Inspects a ChromaDB collection used by Codex AI.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter # Show defaults in help
    )
    parser.add_argument(
        "--db-path",
        default=DEFAULT_CHROMA_PERSIST_DIR,
        help="Path to the ChromaDB persistence directory."
    )
    parser.add_argument(
        "--collection",
        default=DEFAULT_CHROMA_COLLECTION_NAME,
        help="Name of the ChromaDB collection to inspect."
    )
    parser.add_argument(
        "--project",
        metavar="PROJECT_ID",
        default=None,
        help="Optional: Filter documents by a specific project_id."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum number of sample documents to display."
    )

    args = parser.parse_args()

    inspect_chroma(
        db_path=args.db_path,
        collection_name=args.collection,
        project_id_filter=args.project,
        limit=args.limit
    )