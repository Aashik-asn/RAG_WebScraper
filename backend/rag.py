import sqlite3, os, json, pickle, time
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.neighbors import NearestNeighbors
from groq import Groq
from transformers import pipeline
from threading import Lock

MODEL_NAME = 'all-MiniLM-L6-v2'  # for fallback embeddings
EMBED_DIM = 384
lock = Lock()

def get_db_conn(path):
    conn = sqlite3.connect(path, check_same_thread=False)
    return conn

def init_store(db_path):
    # create tables if not present
    conn = get_db_conn(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS docs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT UNIQUE,
        content TEXT,
        embedding BLOB,
        created_at REAL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS chats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        role TEXT,
        message TEXT,
        created_at REAL
    )''')
    conn.commit()
    conn.close()
    # load embedding model (fallback)
    global embedder, vector_index, embeddings_matrix, doc_ids
    embedder = SentenceTransformer(MODEL_NAME)
    embeddings_matrix = None
    doc_ids = []
    vector_index = None
    rebuild_index(db_path)

def add_document(db_path, url, content):
    conn = get_db_conn(db_path)
    c = conn.cursor()
    now = time.time()
    # compute embedding (try OpenAI then fallback)
    emb = compute_embedding(content)
    emb_blob = pickle.dumps(emb)
    try:
        c.execute('INSERT OR REPLACE INTO docs (url, content, embedding, created_at) VALUES (?,?,?,?)',
                  (url, content, emb_blob, now))
        conn.commit()
    finally:
        conn.close()
    rebuild_index(db_path)

def rebuild_index(db_path):
    global embeddings_matrix, doc_ids, vector_index
    conn = get_db_conn(db_path)
    c = conn.cursor()
    c.execute('SELECT id, embedding FROM docs')
    rows = c.fetchall()
    conn.close()
    mats = []
    ids = []
    for r in rows:
        ids.append(r[0])
        emb = pickle.loads(r[1])
        mats.append(emb)
    if mats:
        X = np.vstack(mats)
        vector_index = NearestNeighbors(n_neighbors=10, metric='cosine').fit(X)
        embeddings_matrix = X
        doc_ids = ids
    else:
        embeddings_matrix = None
        doc_ids = []
        vector_index = None

def compute_embedding(text):
    # Use local sentence-transformers for embeddings (Groq doesn't have embedding models)
    global embedder
    emb = embedder.encode(text, normalize_embeddings=True)
    return emb.astype('float32')

def retrieve(db_path, query, top_k=4):
    # compute query embedding
    q_emb = compute_embedding(query)
    if vector_index is None:
        return []
    dists, idxs = vector_index.kneighbors([q_emb], n_neighbors=min(top_k, len(doc_ids)))
    results = []
    for dist, idx in zip(dists[0], idxs[0]):
        doc_id = doc_ids[idx]
        # fetch doc
        conn = get_db_conn(db_path)
        c = conn.cursor()
        c.execute('SELECT url, content FROM docs WHERE id=?',(doc_id,))
        row = c.fetchone()
        conn.close()
        if row:
            results.append({'url': row[0], 'content': row[1], 'score': float(1 - dist)})
    return results

def save_chat(db_path, session_id, role, message):
    conn = get_db_conn(db_path)
    c = conn.cursor()
    now = time.time()
    c.execute('INSERT INTO chats (session_id, role, message, created_at) VALUES (?,?,?,?)',
              (session_id, role, message, now))
    conn.commit()
    conn.close()

def chat_with_retrieval(db_path, session_id, message, top_k=4):
    # save user message
    save_chat(db_path, session_id, 'user', message)
    # retrieve relevant docs
    hits = retrieve(db_path, message, top_k=top_k)
    context = '\n\n'.join([f'URL: {h["url"]}\n{h["content"][:2000]}' for h in hits])
    # Create a clean, focused prompt that doesn't expose system instructions
    system_message = """You are a helpful AI assistant that answers questions based on the provided context. 
    - Base your answer ONLY on the provided context
    - If the answer isn't in the context, say "I don't have enough information in the ingested data to answer this question."
    - Provide well-formatted responses with clear headings, bullet points, and proper spacing
    - Always cite the source URLs at the end
    - Be concise but comprehensive"""
    
    user_message = f"""Context:
{context}

Question: {message}

Please provide a well-structured answer based on the context above."""
    # call LLM with proper system and user messages
    resp_text = call_completion(system_message, user_message)
    # save assistant reply
    save_chat(db_path, session_id, 'assistant', resp_text)
    return {'answer': resp_text, 'sources': [h['url'] for h in hits]}

def call_completion(system_message, user_message):
    # Try Groq LLM first
    groq_key = os.environ.get('GROQ_API_KEY')
    if groq_key:
        try:
            client = Groq(api_key=groq_key)
            completion = client.chat.completions.create(
                model='deepseek-r1-distill-llama-70b',  # Fast and efficient model
                messages=[
                    {'role':'system','content':system_message},
                    {'role':'user','content':user_message}
                ],
                max_tokens=1024,
                temperature=0.0,
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            print('Groq completion failed, falling back:', e)
    
    # Try Hugging Face Inference API if key present
    hf_key = os.environ.get('HUGGINGFACE_API_KEY')
    if hf_key:
        try:
            headers = {'Authorization': f'Bearer {hf_key}'}
            import requests
            API_URL = 'https://api-inference.huggingface.co/models/microsoft/DialoGPT-medium'
            # Combine system and user messages for HF API
            combined_prompt = f"{system_message}\n\n{user_message}"
            payload = {'inputs': combined_prompt, 'parameters': {'max_new_tokens': 256, 'temperature': 0.0}}
            r = requests.post(API_URL, headers=headers, json=payload, timeout=30)
            data = r.json()
            if isinstance(data, list) and 'generated_text' in data[0]:
                return data[0]['generated_text'].strip()
            if isinstance(data, dict) and 'error' in data:
                print('HF Inference error', data['error'])
            # sometimes returns dict with 'generated_text'
            if isinstance(data, dict) and 'generated_text' in data:
                return data['generated_text']
        except Exception as e:
            print('HF inference failed:', e)
    
    # Fallback to local transformers (may require model download)
    try:
        generator = pipeline('text-generation', model='distilgpt2')
        # Combine system and user messages for local model
        combined_prompt = f"{system_message}\n\n{user_message}"
        out = generator(combined_prompt, max_length=300, do_sample=False)
        return out[0]['generated_text'].strip()
    except Exception as e:
        print('Local generation failed:', e)
    return "I don't know based on ingested data."

def get_stats(db_path):
    conn = get_db_conn(db_path)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM docs')
    docs = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM chats')
    chats = c.fetchone()[0]
    conn.close()
    
    # Get additional metrics
    chat_sessions = get_chat_session_count(db_path)
    conversations = get_conversation_count(db_path)
    queries = get_query_count(db_path)
    
    return {
        'docs': docs, 
        'chats': chats,
        'chat_sessions': chat_sessions,
        'conversations': conversations,
        'queries': queries
    }

def get_urls(db_path):
    conn = get_db_conn(db_path)
    c = conn.cursor()
    c.execute('SELECT url FROM docs ORDER BY created_at DESC LIMIT 100')
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

def delete_document(db_path, url):
    """Delete a document by URL and rebuild the index"""
    conn = get_db_conn(db_path)
    c = conn.cursor()
    c.execute('DELETE FROM docs WHERE url = ?', (url,))
    deleted_count = c.rowcount
    conn.commit()
    conn.close()
    if deleted_count > 0:
        rebuild_index(db_path)
    return deleted_count > 0

def get_document_content(db_path, url):
    """Get the content of a specific document by URL"""
    conn = get_db_conn(db_path)
    c = conn.cursor()
    c.execute('SELECT content FROM docs WHERE url = ?', (url,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def get_all_documents(db_path):
    """Get all documents with their URLs and content"""
    conn = get_db_conn(db_path)
    c = conn.cursor()
    c.execute('SELECT url, content, created_at FROM docs ORDER BY created_at DESC')
    rows = c.fetchall()
    conn.close()
    return [{'url': row[0], 'content': row[1], 'created_at': row[2]} for row in rows]

def delete_all_documents(db_path):
    """Delete all documents and rebuild the index"""
    conn = get_db_conn(db_path)
    c = conn.cursor()
    c.execute('DELETE FROM docs')
    deleted_count = c.rowcount
    conn.commit()
    conn.close()
    if deleted_count > 0:
        rebuild_index(db_path)
    return deleted_count

def delete_chat_session(db_path, session_id):
    """Delete all chats for a specific session"""
    conn = get_db_conn(db_path)
    c = conn.cursor()
    c.execute('DELETE FROM chats WHERE session_id = ?', (session_id,))
    deleted_count = c.rowcount
    conn.commit()
    conn.close()
    return deleted_count

def delete_all_chat_sessions(db_path):
    """Delete all chats from all sessions"""
    conn = get_db_conn(db_path)
    c = conn.cursor()
    c.execute('DELETE FROM chats')
    deleted_count = c.rowcount
    conn.commit()
    conn.close()
    return deleted_count

def get_chat_session_count(db_path):
    """Get count of unique chat sessions"""
    conn = get_db_conn(db_path)
    c = conn.cursor()
    c.execute('SELECT COUNT(DISTINCT session_id) FROM chats')
    count = c.fetchone()[0]
    conn.close()
    return count

def get_query_count(db_path):
    """Get count of user queries (user messages)"""
    conn = get_db_conn(db_path)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM chats WHERE role = "user"')
    count = c.fetchone()[0]
    conn.close()
    return count

def get_conversation_count(db_path):
    """Get count of conversations (user+assistant pairs)"""
    conn = get_db_conn(db_path)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM chats WHERE role = "user"')
    count = c.fetchone()[0]
    conn.close()
    return count

def get_all_chat_sessions(db_path):
    """Return all chat sessions and their messages."""
    conn = get_db_conn(db_path)
    c = conn.cursor()
    c.execute('SELECT session_id, role, message, created_at FROM chats ORDER BY created_at ASC')
    rows = c.fetchall()
    conn.close()
    sessions = {}
    for session_id, role, message, created_at in rows:
        if session_id not in sessions:
            sessions[session_id] = {
                'name': session_id,
                'messages': [],
                'created_at': created_at
            }
        sessions[session_id]['messages'].append({
            'role': role,
            'content': message,
            'timestamp': created_at
        })
    return sessions
