# education_advisor.py

import os
import pandas as pd

try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False


def clean_link(link_val):
    if pd.isna(link_val):
        return "#"
    val = str(link_val).strip()
    if val.lower() in ["nan", "null", "none", "", "#"]:
        return "#"
    if not (val.startswith("http://") or val.startswith("https://")):
        return "https://" + val
    return val


class EducationAdvisor:
    def __init__(self, db_path="chroma_db"):
        self.db_path = db_path
        self.use_chroma = CHROMA_AVAILABLE
        self.courses_df = None
        self.certs_df = None
        self.collection = None
        self.fallback_vectorizer = None
        self.fallback_matrix = None
        self.fallback_items = []

        self.load_data()

        if self.use_chroma:
            try:
                chroma_host = os.getenv("CHROMA_HOST")
                chroma_port = os.getenv("CHROMA_PORT")
                
                if chroma_host:
                    print(f"Connecting to remote ChromaDB server at {chroma_host}:{chroma_port or 8000}...")
                    headers = {}
                    api_key = os.getenv("CHROMA_API_KEY") or os.getenv("CHROMA_AUTH_TOKEN")
                    if api_key:
                        headers["X-Chroma-Token"] = api_key
                        headers["Authorization"] = f"Bearer {api_key}"
                        
                    ssl_str = os.getenv("CHROMA_SSL", "false").lower()
                    ssl_enabled = ssl_str in ["true", "1", "yes"]
                    
                    tenant = os.getenv("CHROMA_TENANT", "default_tenant")
                    database = os.getenv("CHROMA_DATABASE", "default_database")
                    
                    self.client = chromadb.HttpClient(
                        host=chroma_host,
                        port=int(chroma_port) if chroma_port else 8000,
                        ssl=ssl_enabled,
                        headers=headers,
                        tenant=tenant,
                        database=database
                    )
                else:
                    # Initialize ChromaDB persistent client
                    self.client = chromadb.PersistentClient(path=self.db_path)
                    
                self.collection = self.client.get_or_create_collection("education_resources_v5")
                self.seed_chroma()
            except Exception as e:
                print(f"Error initializing ChromaDB: {e}. Falling back to TF-IDF vector search.")
                self.use_chroma = False

        if not self.use_chroma:
            self.init_fallback_search()

    def load_data(self):
        """Load course and certification datasets from CSV files."""
        try:
            self.courses_df = pd.read_csv("datasets/couses.csv")
            self.courses_df["Type"] = "Course"
        except Exception as e:
            print(f"Error loading datasets/couses.csv: {e}")
            self.courses_df = pd.DataFrame(columns=["Title", "Provider", "Type", "Skills", "Description"])

        try:
            self.certs_df = pd.read_csv("datasets/certifications.csv")
            self.certs_df["Type"] = "Certification"
        except Exception as e:
            print(f"Error loading datasets/certifications.csv: {e}")
            self.certs_df = pd.DataFrame(columns=["Title", "Provider", "Type", "Skills", "Description"])

    def seed_chroma(self):
        """Seed educational data into the ChromaDB collection if empty."""
        try:
            if self.collection.count() > 0:
                return  # Database already seeded
        except Exception:
            pass

        documents = []
        metadatas = []
        ids = []

        df = pd.concat([self.courses_df, self.certs_df], ignore_index=True)
        for idx, row in df.iterrows():
            title = str(row["Title"])
            provider = str(row["Provider"])
            item_type = str(row["Type"])
            skills = str(row["Skills"])
            desc = str(row["Description"])

            # Format the document for embedding models to parse semantic relationships
            doc_text = f"Title: {title}\nProvider: {provider}\nType: {item_type}\nSkills: {skills}\nDescription: {desc}"
            
            documents.append(doc_text)
            metadatas.append({
                "title": title,
                "provider": provider,
                "type": item_type,
                "skills": skills,
                "description": desc,
                "link": clean_link(row.get("Link", "#"))
            })
            ids.append(f"edu_res_{idx}")

        if documents:
            try:
                self.collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                print(f"Successfully seeded {len(documents)} resources into ChromaDB.")
            except Exception as e:
                print(f"ChromaDB seeding failed: {e}. Activating TF-IDF fallback.")
                self.use_chroma = False

    def init_fallback_search(self):
        """Initialize scikit-learn TF-IDF Vectorizer as a robust fallback search engine."""
        from sklearn.feature_extraction.text import TfidfVectorizer

        df = pd.concat([self.courses_df, self.certs_df], ignore_index=True)
        self.fallback_items = []
        documents = []

        for _, row in df.iterrows():
            item = {
                "title": str(row["Title"]),
                "provider": str(row["Provider"]),
                "type": str(row["Type"]),
                "skills": str(row["Skills"]),
                "description": str(row["Description"]),
                "link": clean_link(row.get("Link", "#"))
            }
            self.fallback_items.append(item)
            # Combine fields to build a robust indexable string
            doc_text = f"{item['title']} {item['provider']} {item['type']} {item['skills']} {item['description']}"
            documents.append(doc_text)

        if documents:
            try:
                self.fallback_vectorizer = TfidfVectorizer(stop_words='english')
                self.fallback_matrix = self.fallback_vectorizer.fit_transform(documents)
                print(f"Successfully initialized TF-IDF Fallback search with {len(documents)} resources.")
            except Exception as e:
                print(f"Failed to initialize TF-IDF fallback search: {e}")

    def get_recommendations(self, career_query, limit=5):
        """Query recommendations semantically (using ChromaDB or Fallback TF-IDF)."""
        if self.use_chroma and self.collection:
            try:
                results = self.collection.query(
                    query_texts=[career_query],
                    n_results=limit
                )
                recommendations = []
                if results and "metadatas" in results and results["metadatas"]:
                    for item in results["metadatas"][0]:
                        recommendations.append(item)
                return recommendations
            except Exception as e:
                print(f"ChromaDB query failed: {e}. Falling back to TF-IDF.")
                # Don't throw, proceed to fallback logic below

        # TF-IDF Cosine Similarity Fallback Search
        if not self.fallback_items or not self.fallback_vectorizer:
            self.init_fallback_search()

        if not self.fallback_items or not self.fallback_vectorizer:
            return []

        from sklearn.metrics.pairwise import cosine_similarity

        try:
            # Transform user query
            query_vec = self.fallback_vectorizer.transform([career_query])
            similarities = cosine_similarity(query_vec, self.fallback_matrix).flatten()
            
            # Sort from highest to lowest similarity
            top_indices = similarities.argsort()[::-1][:limit]
            
            recommendations = []
            for idx in top_indices:
                # Check if similarity is above zero to filter out completely irrelevant results
                if similarities[idx] > 0.0:
                    recommendations.append(self.fallback_items[idx])
            
            # If nothing matches above 0, return top anyway to avoid empty list
            if not recommendations:
                recommendations = [self.fallback_items[idx] for idx in top_indices[:limit]]
                
            return recommendations
        except Exception as e:
            print(f"Fallback search query failed: {e}")
            # Absolute baseline: return first few items
            return self.fallback_items[:limit]

    def get_dynamic_recommendations_with_groq(self, career, api_key, limit=6):
        """Uses Groq to dynamically generate relevant courses & certifications with links."""
        try:
            from groq import Groq
            import json
            import re
            
            client = Groq(api_key=api_key)
            prompt = f"""
Suggest 3 popular online courses and 3 professional certifications for a career in "{career}".
For each, provide: Title, Provider, Type ("Course" or "Certification"), Skills (comma-separated list of target skills), Description, and Link (a realistic URL to Coursera, Udemy, or vendor registration).
Return ONLY a JSON list of objects, each with keys "title", "provider", "type", "skills", "description", and "link". Do not include markdown formatting or explanation.
"""
            completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-8b-instant",
                temperature=0.3,
                max_tokens=1000
            )
            response_text = completion.choices[0].message.content.strip()
            
            json_match = re.search(r'(\[.*\])', response_text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(1))
                if isinstance(parsed, list):
                    recommendations = []
                    for item in parsed:
                        recommendations.append({
                            "title": item.get("title", ""),
                            "provider": item.get("provider", ""),
                            "type": item.get("type", "Course"),
                            "skills": item.get("skills", ""),
                            "description": item.get("description", ""),
                            "link": clean_link(item.get("link", "#"))
                        })
                    return recommendations
        except Exception as e:
            print(f"Error in Groq educational recommendation: {e}. Falling back to ChromaDB.")
            
        return self.get_recommendations(career, limit)
    def save_user_profile(self, profile_id, name, email, skills_text, interests, recommended_career, match_score, submission_type):
        """Save user profile to a collection in ChromaDB under user_profiles_v1."""
        if not self.use_chroma:
            return False
        try:
            user_collection = self.client.get_or_create_collection("user_profiles_v1")
            
            # Format text representation for semantic embeddings
            doc_text = f"Name: {name}\nEmail: {email}\nSkills text: {skills_text}\nInterests: {interests}\nRecommended Career: {recommended_career}\nMatch Score: {match_score}%\nSubmission Type: {submission_type}"
            
            # Build metadata dict
            metadata = {
                "profile_id": int(profile_id),
                "name": str(name),
                "email": str(email),
                "interests": str(interests if interests else ""),
                "recommended_career": str(recommended_career),
                "match_score": float(match_score),
                "submission_type": str(submission_type)
            }
            
            user_collection.add(
                documents=[doc_text],
                metadatas=[metadata],
                ids=[f"user_profile_{profile_id}"]
            )
            print(f"ChromaDB: Successfully saved profile ID {profile_id}")
            return True
        except Exception as e:
            print(f"Warning: Failed to save profile to ChromaDB: {e}")
            return False

    def delete_user_profile_from_chroma(self, profile_id):
        """Delete user profile from ChromaDB collection."""
        if not self.use_chroma:
            return False
        try:
            user_collection = self.client.get_or_create_collection("user_profiles_v1")
            user_collection.delete(ids=[f"user_profile_{profile_id}"])
            print(f"ChromaDB: Successfully deleted profile ID {profile_id}")
            return True
        except Exception as e:
            print(f"Warning: Failed to delete profile from ChromaDB: {e}")
            return False



if __name__ == "__main__":
    # Test the advisor
    advisor = EducationAdvisor(db_path="test_chroma_db")
    print(f"Using ChromaDB? {advisor.use_chroma}")
    
    results = advisor.get_recommendations("Machine Learning")
    print(f"\nRecommendations for 'Machine Learning' (Total: {len(results)}):")
    for r in results:
        print(f"- [{r['type']}] {r['title']} by {r['provider']} (Skills: {r['skills']})")
