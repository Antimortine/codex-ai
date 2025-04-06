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

# --- Configuration (Match IndexManager) ---
CHROMA_PERSIST_DIR = "../backend/chroma_db"
CHROMA_COLLECTION_NAME = "codex_ai_documents"

try:
    print(f"Connecting to ChromaDB at: {CHROMA_PERSIST_DIR}")
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)

    print(f"Getting collection: {CHROMA_COLLECTION_NAME}")
    # Use get_collection to avoid creating if it doesn't exist (it should after indexing)
    collection = client.get_collection(name=CHROMA_COLLECTION_NAME)

    count = collection.count()
    print(f"\nCollection '{CHROMA_COLLECTION_NAME}' found with {count} documents.")

    if count > 0:
        print("\nGetting first few documents (max 5):")
        # Peek at some data - includes embeddings, metadata, documents/text
        results = collection.peek(limit=5)
        # Or get all data if you prefer (might be large)
        # results = collection.get(include=["metadatas", "documents"])

        print("\n--- Sample Data ---")
        if results.get("ids"):
             for i, doc_id in enumerate(results["ids"]):
                  print(f"ID: {doc_id}")
                  if results.get("metadatas") and len(results["metadatas"]) > i:
                       print(f"  Metadata: {results['metadatas'][i]}")
                  if results.get("documents") and len(results["documents"]) > i:
                       # Only print start of document if long
                       doc_content = results['documents'][i]
                       print(f"  Document: {doc_content[:100]}{'...' if len(doc_content) > 100 else ''}")
                  print("-" * 10)
        else:
             print("Peek results format unexpected or empty.")
        print("-------------------")

    # Example: Get documents by specific ID (replace with an actual file path used)
    # specific_id = r"user_projects\your_project_id\plan.md" # Use raw string for Windows paths
    # try:
    #     print(f"\nGetting specific document by ID: {specific_id}")
    #     specific_doc = collection.get(ids=[specific_id], include=["metadatas", "documents"])
    #     print(specific_doc)
    # except Exception as e:
    #     print(f"Could not get specific document (may not exist): {e}")


except Exception as e:
    print(f"\nAn error occurred: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()