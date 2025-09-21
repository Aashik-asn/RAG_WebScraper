# RAG Application with Flask Backend and Streamlit Frontend

A sophisticated Retrieval-Augmented Generation (RAG) application that allows you to ingest web content and chat with it using AI. The application features a modern, interactive interface similar to ChatGPT with multiple chat sessions, content management, and structured AI responses.

## 🚀 Features

### ✨ New Features Added
- **🗑️ Content Source Management**: Delete individual content sources from the dashboard
- **📋 Ingestion Results Popup**: View detailed ingestion results after crawling
- **📚 Contents Tab**: Browse and manage all ingested content with previews
- **💬 Interactive Chat Interface**: ChatGPT-like experience with:
  - Multiple chat sessions in sidebar
  - Session management (create, switch, delete)
  - Real-time chat interface
  - Source citations
- **🎯 Improved AI Responses**: Enhanced system prompt for structured, well-formatted answers
- **🔧 OpenAI API Fix**: Updated to use the latest OpenAI API format

### 🏗️ Core Features
- **Web Content Ingestion**: Crawl and ingest web pages with configurable depth and page limits
- **Vector Search**: Semantic search using embeddings (OpenAI or local fallback)
- **RAG Chat**: Context-aware conversations using retrieved content
- **Session Management**: Persistent chat history
- **Dashboard Analytics**: View ingestion stats and content sources

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- Groq API key (recommended for fast LLM responses)

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd rag_flask_streamlit
   ```

2. **Install backend dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Install frontend dependencies**
   ```bash
   cd ../frontend
   pip install -r requirements.txt
   ```

4. **Set up environment variables** (recommended)
   ```bash
   # Create .env file in the root directory
   echo "GROQ_API_KEY=your_groq_api_key_here" > .env
   ```

## 🚀 Running the Application

### Create a .env file in backend folder
 HUGGINGFACE_API_KEY=Your_Api_Key
 GROQ_API_KEY= Your_Api_Key


### Start the Backend Server
```bash
cd backend
python app.py
```
The backend will run on `http://localhost:8000`

### Start the Frontend Interface
```bash
cd frontend
streamlit run app.py
```
The frontend will be available at `http://localhost:8501`

## 📖 Usage Guide

### 1. Dashboard Tab
- **View Statistics**: See total ingested URLs, chat messages, and estimated sessions
- **Manage Content Sources**: View all ingested URLs with delete options
- **Refresh Data**: Update statistics and content lists

### 2. Ingestion Tab

#### Ingest New Content
- Enter a base URL (e.g., `https://example.com`)
- Configure crawl settings:
  - **Max Pages**: Number of pages to crawl (1-100)
  - **Max Depth**: Crawl depth (0-5)
- Click "Start Ingestion" to begin crawling
- View detailed results in the popup after completion

#### View Contents
- Browse all ingested documents
- Preview content for each document
- Delete individual documents
- See ingestion timestamps

### 3. Chat Tab

#### Creating and Managing Sessions
- **New Chat**: Create a new chat session from the sidebar
- **Switch Sessions**: Click on any session in the sidebar to switch
- **Delete Sessions**: Remove unwanted chat sessions
- **Session Names**: Automatically numbered (Chat 1, Chat 2, etc.)

#### Chatting
- Type questions in the chat input at the bottom
- AI responses include:
  - Structured, well-formatted answers
  - Source citations
  - Relevant context from ingested content
- View sources in expandable sections
- Chat history is preserved across sessions

#### Example Questions
- "What is the main topic of the ingested content?"
- "Can you summarize the key points?"
- "What are the most important details mentioned?"
- "Are there any specific examples or case studies?"

## 🔧 Configuration

### API Keys
- **Groq API Key**: Set `GROQ_API_KEY` environment variable for:
  - Fast LLM responses using Llama3-8b-8192 model
  - High-quality chat completions
  - Fallback to local models if not available

### Backend Configuration
- **Database**: SQLite database (`rag_store.db`) stores documents and chat history
- **Embeddings**: Uses local sentence-transformers for embeddings
- **LLM**: Groq API with Llama3-8b-8192 model for fast responses
- **Vector Search**: Cosine similarity with scikit-learn

### Frontend Configuration
- **API Base URL**: Configured via `API_BASE` environment variable
- **Default**: `http://localhost:8000`

## 🏗️ Architecture

### Backend (Flask)
- **`app.py`**: Main Flask application with API endpoints
- **`rag.py`**: RAG functionality, embeddings, and vector search
- **`ingest.py`**: Web crawling and content extraction

### Frontend (Streamlit)
- **`app.py`**: Complete Streamlit interface with tabs and interactive features

### API Endpoints
- `POST /ingest`: Ingest web content
- `POST /chat`: Chat with RAG system
- `GET /stats`: Get application statistics
- `GET /urls`: Get list of ingested URLs
- `POST /delete`: Delete a content source
- `GET /content/<url>`: Get specific document content
- `GET /documents`: Get all documents with metadata

## 🐛 Troubleshooting

### Groq API Issues
- **Rate Limits**: The app falls back to local models if Groq is unavailable
- **API Key**: Ensure your Groq API key is valid and has sufficient credits
- **Model Access**: The app uses `llama3-8b-8192` for fast, efficient responses

### Common Issues
- **Import Errors**: Ensure all dependencies are installed
- **Connection Errors**: Check that the backend is running on port 8000
- **Empty Responses**: Verify that content has been ingested before chatting

### Performance Tips
- **Local Models**: The app works without Groq API key using local models
- **Fast Responses**: Groq provides very fast LLM responses compared to other providers
- **Crawl Limits**: Adjust max_pages and depth based on your needs
- **Session Management**: Delete old chat sessions to improve performance

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📞 Support

For issues and questions:
1. Check the troubleshooting section
2. Review the API documentation
3. Create an issue in the repository

---

**Happy Chatting! 🚀**