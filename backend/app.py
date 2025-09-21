from flask import Flask, request, jsonify
from ingest import crawler_ingest
from rag import init_store, add_document, chat_with_retrieval, get_stats, get_urls, delete_document, get_document_content, get_all_documents, delete_all_documents, delete_chat_session, delete_all_chat_sessions
import os

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), 'rag_store.db')

# Initialize (loads embeddings and vector index if present)
init_store(DB_PATH)

@app.route('/ingest', methods=['POST'])
def ingest():
    data = request.json
    url = data.get('url')
    max_pages = int(data.get('max_pages', 50))
    depth = int(data.get('depth', 2))
    if not url:
        return jsonify({'error': 'url required'}), 400
    docs = crawler_ingest(url, max_pages=max_pages, max_depth=depth)
    added = 0
    for d in docs:
        add_document(DB_PATH, d['url'], d['text'])
        added += 1
    return jsonify({'ingested': added, 'base_url': url})

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    session_id = data.get('session_id', 'default')
    message = data.get('message')
    top_k = int(data.get('top_k', 4))
    if not message:
        return jsonify({'error': 'message required'}), 400
    resp = chat_with_retrieval(DB_PATH, session_id, message, top_k=top_k)
    return jsonify(resp)

@app.route('/stats', methods=['GET'])
def stats():
    return jsonify(get_stats(DB_PATH))

@app.route('/urls', methods=['GET'])
def urls():
    return jsonify(get_urls(DB_PATH))

@app.route('/delete', methods=['POST'])
def delete():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({'error': 'url required'}), 400
    success = delete_document(DB_PATH, url)
    return jsonify({'success': success})

@app.route('/content/<path:url>', methods=['GET'])
def get_content(url):
    content = get_document_content(DB_PATH, url)
    if content is None:
        return jsonify({'error': 'Document not found'}), 404
    return jsonify({'url': url, 'content': content})

@app.route('/documents', methods=['GET'])
def documents():
    return jsonify(get_all_documents(DB_PATH))

@app.route('/delete_all', methods=['POST'])
def delete_all():
    deleted_count = delete_all_documents(DB_PATH)
    return jsonify({'success': True, 'deleted_count': deleted_count})

@app.route('/delete_chat_session', methods=['POST'])
def delete_chat_session_endpoint():
    data = request.json
    session_id = data.get('session_id')
    if not session_id:
        return jsonify({'error': 'session_id required'}), 400
    deleted_count = delete_chat_session(DB_PATH, session_id)
    return jsonify({'success': True, 'deleted_count': deleted_count})

@app.route('/delete_all_chat_sessions', methods=['POST'])
def delete_all_chat_sessions_endpoint():
    deleted_count = delete_all_chat_sessions(DB_PATH)
    return jsonify({'success': True, 'deleted_count': deleted_count})

if __name__ == '__main__':
    app.run(port=8000, debug=True)
