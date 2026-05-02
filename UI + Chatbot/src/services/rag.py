import json
import os
from typing import List

from langchain_community.document_loaders import TextLoader, PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
import dotenv

dotenv.load_dotenv(override=True)

class RAGService:
    def __init__(self, db_path: str = "./vector_db"):
        self.db_path = db_path

        # ✅ OpenAI embeddings (cheap + stable)
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small"
        )

        self.vector_db = None

        # Load existing DB if it exists
        if os.path.exists(db_path):
            self.vector_db = Chroma(
                persist_directory=self.db_path,
                embedding_function=self.embeddings
            )

    @staticmethod
    def clean_text(text: str) -> str:
        """Normalize text to proper UTF-8 and fix common encoding issues."""
        if not text:
            return ""

        replacements = {
            "Ã©": "é",
            "Ã¨": "è",
            "Ã": "à",
            "â€™": "'",
            "â€“": "-",
            "â€˜": "'",
            "â€œ": '"',
            "â€": '"',
            "â€¯": " ",
            "Â": "",
        }

        text = text.encode("utf-8", "ignore").decode("utf-8")

        for wrong, right in replacements.items():
            text = text.replace(wrong, right)

        text = text.replace('\u2009', ' ')
        text = text.replace('\u202f', ' ')
        text = text.replace('\u2013', '-')
        text = text.replace('\u2019', "'")
        text = text.replace('\u201c', '"')
        text = text.replace('\u201d', '"')

        text = " ".join(text.split())

        return text

    def ingest_files(self, file_paths: List[str]):
        """Load, clean, chunk, embed, and store documents."""
        all_docs = []

        for file_path in file_paths:
            docs = []

            if file_path.endswith(".pdf"):
                loader = PyMuPDFLoader(file_path)
                docs = loader.load()

            elif file_path.endswith((".txt", ".md", ".markdown")):
                # Markdown is plain text; the splitter handles structure via
                # separators. Avoids pulling in the unstructured + nltk
                # dependency tree just to read MD.
                loader = TextLoader(file_path, encoding="utf-8")
                docs = loader.load()

            elif file_path.endswith(".json"):
                with open(file_path, "r", encoding="utf-8") as f:
                    data_list = json.load(f)

                for data in data_list:
                    docs.append(
                        Document(
                            page_content=data.get("content", ""),
                            metadata={
                                "source": file_path,
                                "url": data.get("url", "")
                            }
                        )
                    )
            else:
                continue

            # Clean text
            for doc in docs:
                doc.page_content = self.clean_text(doc.page_content.strip())

            all_docs.extend(docs)

        # ✅ Better chunking (slightly improved)
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=700,
            chunk_overlap=120,
            separators=["\n\n", "\n", ".", " ", ""]
        )

        chunks = text_splitter.split_documents(all_docs)

        # ✅ Build / overwrite vector DB
        self.vector_db = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            persist_directory=self.db_path
        )

        print(f"✅ Successfully indexed {len(chunks)} chunks.")

    def search(self, query: str, k: int = 3) -> List[Document]:
        """Return top-k relevant chunks."""
        if not self.vector_db:
            raise ValueError("Vector database not initialized.")

        return self.vector_db.similarity_search(query, k=k)