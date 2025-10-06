import streamlit as st
import requests, os, time, uuid
import json
from datetime import datetime

API = st.secrets.get('API_BASE') if 'API_BASE' in st.secrets else os.environ.get('API_BASE','http://localhost:8000')

def load_chat_sessions_from_backend():
    try:
        r = requests.get(f'{API}/chat_sessions')
        if r.status_code == 200:
            sessions = r.json()
            # Convert keys to str (in case session_id is not str)
            sessions = {str(k): v for k, v in sessions.items()}
            return sessions
    except Exception as e:
        st.warning(f"Could not load chat sessions: {e}")
    return {}

# Restore chat sessions from backend on first load
if 'chat_sessions' not in st.session_state or not st.session_state['chat_sessions']:
    st.session_state['chat_sessions'] = load_chat_sessions_from_backend()
    # Set the most recent session as current, if any
    if st.session_state['chat_sessions']:
        st.session_state['current_session'] = list(st.session_state['chat_sessions'].keys())[-1]
    else:
        st.session_state['current_session'] = None

st.set_page_config(page_title='RAG App', layout='wide')

# Initialize session state
if 'chat_sessions' not in st.session_state:
    st.session_state.chat_sessions = {}
if 'current_session' not in st.session_state:
    st.session_state.current_session = None
if 'ingestion_results' not in st.session_state:
    st.session_state.ingestion_results = None

st.title('RAG App - Dashboard / Ingest / Chat')

tabs = st.tabs(['About','Dashboard','Ingestion','Chat'])

with tabs[1]:
    col1, col2 = st.columns([3, 1])
    with col1:
        st.header('Dashboard')
    with col2:
        if st.button('Refresh Stats'):
            st.rerun()
    
    try:
        stats = requests.get(f'{API}/stats').json()
    except Exception as e:
        st.error(f"Error fetching stats: {e}")
        stats = {'docs':0,'chats':0}
    
    col1, col2, col3 = st.columns(3)
    col1.metric('URLs ingested', stats.get('docs',0))
    col2.metric('Sessions', stats.get('conversations',0))
    col3.metric('Queries Solved', stats.get('queries',0))
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader('Content Sources')
    with col2:
        if st.button('Remove All', type='secondary'):
            try:
                response = requests.post(f'{API}/delete_all')
                if response.json().get('success'):
                    deleted_count = response.json().get('deleted_count', 0)
                    st.success(f"Removed {deleted_count} content sources")
                    st.rerun()
                else:
                    st.error("Failed to remove all sources")
            except Exception as e:
                st.error(f"Error removing sources: {e}")
    
    try:
        urls = requests.get(f'{API}/urls').json()
        if urls:
            for i, url in enumerate(urls[:20]):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(url)
                with col2:
                    if st.button("Remove", key=f"delete_{i}", help="Delete this source"):
                        try:
                            response = requests.post(f'{API}/delete', json={'url': url})
                            if response.json().get('success'):
                                st.success(f"Deleted: {url}")
                                st.rerun()
                            else:
                                st.error("Failed to delete source")
                        except Exception as e:
                            st.error(f"Error deleting source: {e}")
        else:
            st.info("No content sources found. Start by ingesting some URLs in the Ingestion tab.")
    except Exception as e:
        st.error(f"Error fetching URLs: {e}")

with tabs[2]:
    st.header('Ingestion')
    
    # Create sub-tabs for ingestion
    ingestion_tabs = st.tabs(['Ingest New Content', 'View Contents'])
    
    with ingestion_tabs[0]:
        url = st.text_input('Base URL to ingest (include https://)', placeholder='https://example.com')
        col1, col2 = st.columns(2)
        with col1:
            max_pages = st.number_input('Max pages to crawl', value=20, min_value=1, max_value=100)
        with col2:
            depth = st.number_input('Max crawl depth', value=2, min_value=0, max_value=5)
        
        if st.button('Start Ingestion', type='primary'):
            if not url:
                st.error('Please enter a URL')
            else:
                with st.spinner('Ingesting content... This may take a few minutes.'):
                    try:
                        r = requests.post(f'{API}/ingest', json={'url':url,'max_pages':int(max_pages),'depth':int(depth)})
                        if r.status_code == 200:
                            result = r.json()
                            st.session_state.ingestion_results = result
                            st.success(f"✅ Successfully ingested {result.get('ingested')} pages from {result.get('base_url')}")
                            
                            # Show popup with ingested content
                            if st.session_state.ingestion_results:
                                with st.expander("View Ingested Content Details", expanded=True):
                                    st.write(f"**Base URL:** {result.get('base_url')}")
                                    st.write(f"**Pages Ingested:** {result.get('ingested')}")
                                    st.write(f"**Max Pages:** {max_pages}")
                                    st.write(f"**Crawl Depth:** {depth}")
                                    st.write(f"**Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                        else:
                            st.error(f"Error during ingestion: {r.text}")
                    except Exception as e:
                        st.error(f"Error during ingestion: {e}")
    
    with ingestion_tabs[1]:
        st.subheader('All Ingested Contents')
        try:
            documents = requests.get(f'{API}/documents').json()
            if documents:
                for i, doc in enumerate(documents):
                    with st.expander(f"{doc['url']}", expanded=False):
                        st.write(f"**URL:** {doc['url']}")
                        st.write(f"**Ingested:** {datetime.fromtimestamp(doc['created_at']).strftime('%Y-%m-%d %H:%M:%S')}")
                        st.write(f"**Content Preview:**")
                        content_preview = doc['content'][:500] + "..." if len(doc['content']) > 500 else doc['content']
                        st.text_area("", value=content_preview, height=100, key=f"content_{i}", disabled=True)
                        
                        col1, col2 = st.columns([3, 1])
                        with col2:
                            if st.button("Remove", key=f"delete_doc_{i}"):
                                try:
                                    response = requests.post(f'{API}/delete', json={'url': doc['url']})
                                    if response.json().get('success'):
                                        st.success(f"Deleted: {doc['url']}")
                                        st.rerun()
                                    else:
                                        st.error("Failed to delete document")
                                except Exception as e:
                                    st.error(f"Error deleting document: {e}")
            else:
                st.info("No documents found. Start by ingesting some URLs.")
        except Exception as e:
            st.error(f"Error fetching documents: {e}")

with tabs[3]:
    st.header('Interactive Chat')
    
    # Create two columns: sidebar for sessions and main chat area
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.subheader("Chat Sessions")
        
        # New chat button
        if st.button("New Chat", type='primary', use_container_width=True):
            new_session_id = f"session_{str(uuid.uuid4())[:8]}"
            st.session_state.chat_sessions[new_session_id] = {
                'name': f"Chat {len(st.session_state.chat_sessions) + 1}",
                'messages': [],
                'created_at': time.time()
            }
            st.session_state.current_session = new_session_id
            st.rerun()
        
        # Remove all chats button
        if st.button("Remove All", type='secondary', use_container_width=True):
            if st.session_state.chat_sessions:
                try:
                    response = requests.post(f'{API}/delete_all_chat_sessions')
                    if response.json().get('success'):
                        deleted_count = response.json().get('deleted_count', 0)
                        st.success(f"Removed {deleted_count} chat messages from database")
                    st.session_state.chat_sessions = {}
                    st.session_state.current_session = None
                    st.rerun()
                except Exception as e:
                    st.error(f"Error removing chat sessions: {e}")
                    st.session_state.chat_sessions = {}
                    st.session_state.current_session = None
                    st.rerun()
        
        st.divider()
        
        # Display existing sessions
        if st.session_state.chat_sessions:
            for session_id, session_data in st.session_state.chat_sessions.items():
                # Check if this session is being edited
                edit_key = f"edit_{session_id}"
                if edit_key not in st.session_state:
                    st.session_state[edit_key] = False
                
                if st.session_state[edit_key]:
                    # Edit mode
                    new_name = st.text_input("Edit name:", value=session_data['name'], key=f"name_input_{session_id}")
                    col_save, col_cancel = st.columns(2)
                    with col_save:
                        if st.button("Save", key=f"save_{session_id}"):
                            st.session_state.chat_sessions[session_id]['name'] = new_name
                            st.session_state[edit_key] = False
                            st.rerun()
                    with col_cancel:
                        if st.button("Cancel", key=f"cancel_{session_id}"):
                            st.session_state[edit_key] = False
                            st.rerun()
                else:
                    # Normal mode
                    col_session, col_edit, col_delete = st.columns([3, 1, 1])
                    with col_session:
                        if st.button(session_data['name'], key=f"select_{session_id}", use_container_width=True):
                            st.session_state.current_session = session_id
                            st.rerun()
                    with col_edit:
                        if st.button("Edit", key=f"edit_btn_{session_id}", help="Edit session name"):
                            st.session_state[edit_key] = True
                            st.rerun()
                    with col_delete:
                        if st.button("🗑️", key=f"del_{session_id}", help="Delete session", use_container_width=True):
                            try:
                                response = requests.post(f'{API}/delete_chat_session', json={'session_id': session_id})
                                if response.json().get('success'):
                                    deleted_count = response.json().get('deleted_count', 0)
                                    st.success(f"Removed {deleted_count} messages from database")
                                del st.session_state.chat_sessions[session_id]
                                if st.session_state.current_session == session_id:
                                    st.session_state.current_session = None
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error removing chat session: {e}")
                                del st.session_state.chat_sessions[session_id]
                                if st.session_state.current_session == session_id:
                                    st.session_state.current_session = None
                                st.rerun()
        else:
            st.info("No chat sessions yet. Create a new chat to get started!")
    
    with col2:
        # Main chat area
        if st.session_state.current_session and st.session_state.current_session in st.session_state.chat_sessions:
            current_session_data = st.session_state.chat_sessions[st.session_state.current_session]
            
            # Display session name
            st.subheader(f"{current_session_data['name']}")
        
            # Chat messages display
            chat_container = st.container()
            with chat_container:
                for message in current_session_data['messages']:
                    if message['role'] == 'user':
                        with st.chat_message("user"):
                            st.write(message['content'])
                    else:
                        with st.chat_message("assistant"):
                            st.markdown(message['content'])
                            if 'sources' in message and message['sources']:
                                with st.expander("Sources"):
                                    for source in message['sources']:
                                        st.write(f"• {source}")
            
            # Chat input
            user_input = st.chat_input("Ask a question about your ingested content...")
            
            if user_input:
                # Add user message to session
                current_session_data['messages'].append({
                    'role': 'user',
                    'content': user_input,
                    'timestamp': time.time()
                })
                
                # Display user message immediately
                with st.chat_message("user"):
                    st.write(user_input)
                
                # Get AI response
                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        try:
                            payload = {
                                'session_id': st.session_state.current_session,
                                'message': user_input,
                                'top_k': 4
                            }
                            response = requests.post(f'{API}/chat', json=payload)
                            
                            if response.status_code == 200:
                                result = response.json()
                                answer = result.get('answer', 'No response received')
                                sources = result.get('sources', [])
                                
                                # Display AI response
                                st.markdown(answer)
                                
                                # Display sources
                                if sources:
                                    with st.expander("Sources"):
                                        for source in sources:
                                            st.write(f"• {source}")
                                
                                # Add assistant message to session
                                current_session_data['messages'].append({
                                    'role': 'assistant',
                                    'content': answer,
                                    'sources': sources,
                                    'timestamp': time.time()
                                })
                            else:
                                error_msg = f"Error: {response.text}"
                                st.error(error_msg)
                                current_session_data['messages'].append({
                                    'role': 'assistant',
                                    'content': error_msg,
                                    'timestamp': time.time()
                                })
                        except Exception as e:
                            error_msg = f"Error: {str(e)}"
                            st.error(error_msg)
                            current_session_data['messages'].append({
                                'role': 'assistant',
                                'content': error_msg,
                                'timestamp': time.time()
                            })
        else:
            st.info("Select a chat session from the left panel or create a new one to start chatting!")
            
            # Show some example questions
            st.subheader("Example Questions")
            example_questions = [
                "What is the main topic of the ingested content?",
                "Can you summarize the key points?",
                "What are the most important details mentioned?",
                "Are there any specific examples or case studies?"
            ]
            
            for question in example_questions:
                if st.button(question, key=f"example_{question}"):
                    if not st.session_state.current_session:
                        # Create a new session
                        new_session_id = f"session_{str(uuid.uuid4())[:8]}"
                        st.session_state.chat_sessions[new_session_id] = {
                            'name': f"Chat {len(st.session_state.chat_sessions) + 1}",
                            'messages': [],
                            'created_at': time.time()
                        }
                        st.session_state.current_session = new_session_id
                    
                    # Add the example question as user input
                    st.session_state.example_question = question
                    st.rerun()
            
            # Handle example question
            if 'example_question' in st.session_state:
                user_input = st.session_state.example_question
                del st.session_state.example_question
                
                current_session_data = st.session_state.chat_sessions[st.session_state.current_session]
                
                # Add user message to session
                current_session_data['messages'].append({
                    'role': 'user',
                    'content': user_input,
                    'timestamp': time.time()
                })
                
                # Get AI response
                with st.spinner("Thinking..."):
                    try:
                        payload = {
                            'session_id': st.session_state.current_session,
                            'message': user_input,
                            'top_k': 4
                        }
                        response = requests.post(f'{API}/chat', json=payload)
                        
                        if response.status_code == 200:
                            result = response.json()
                            answer = result.get('answer', 'No response received')
                            sources = result.get('sources', [])
                            
                            # Add assistant message to session
                            current_session_data['messages'].append({
                                'role': 'assistant',
                                'content': answer,
                                'sources': sources,
                                'timestamp': time.time()
                            })
                            
                            st.rerun()
                        else:
                            st.error(f"Error: {response.text}")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
with tabs[0]:
    st.header("About This Application")

    st.subheader("What is this?")
    st.markdown("""
    This application is a sophisticated **web scraping and AI-powered chat platform** designed to help users easily extract, store, and interact with web content.  
    It is perfect for anyone who wants to transform lengthy webpages into concise, searchable insights without needing programming knowledge.
    """)

    st.subheader("How It Works")
    st.markdown("""
    The process is straightforward yet powerful:  
    1. **Scraping:** Simply input the URL of a webpage, and the system automatically extracts the relevant text content for you.  
    2. **Storage:** The extracted data is securely saved into a database, ensuring your information is organized and persistent.  
    3. **Processing:** A backend API efficiently indexes and prepares the content for quick retrieval and natural language querying.  
    4. **Chat Interaction:** Engage with the content by asking detailed questions, getting instant, AI-generated answers based on the scraped material.
    """)

    st.subheader("Key Features")
    st.markdown("""
    - Automated **web scraping** for hassle-free content extraction  
    - **Conversational AI chat interface** to query and explore data naturally  
    - Support for **multiple URLs and data sources**, enabling wide-ranging research  
    - Intuitive, clean, and **responsive interface** suitable for all users  
    - Privacy-conscious and secure **data storage mechanism**  
    """)

    st.subheader("Why Use This Application?")
    st.markdown("""
    - **Save hours** by avoiding manual reading and note-taking from lengthy web pages  
    - Gain **quick insights** from complex or extensive information  
    - Ideal for **researchers, students, analysts, and curious minds** who need rapid access to knowledge  
    - No prior technical skills required — **user-friendly design with clear navigation**  
    - Accessible on any device with a modern web browser  
    """)

    st.subheader("How to Use")
    st.markdown("""
    Getting started is simple and intuitive:  
    1. **Enter URL:** Paste the link of the webpage you want to analyze.  
    2. **Scrape Content:** Click the scrape button to extract the relevant information automatically.  
    3. **View & Store:** Review the scraped content and it will be saved securely in the system.  
    4. **Ask Questions:** Use the chat interface to query the data in natural language.  
    5. **Refine & Explore:** Continue interacting, adding multiple URLs, and exploring insights seamlessly.
    """)

    st.divider()
    st.info("""
    This project combines the power of automated data extraction with cutting-edge AI to make web information accessible and interactive like never before.  
    Whether for academic work, market research, or general learning, this tool adapts to your needs and streamlines information discovery.
    """)
