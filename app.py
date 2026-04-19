"""WhisperForge Streamlit UI.

Thin presentation layer on top of the `whisperforge_core` package. The UI owns
session state and progress surfaces; all business logic (audio chunking,
Whisper transcription, LLM content generation, Notion export, prompt
management) lives in ``whisperforge_core`` so microservices in services/ can
share the same code.
"""

import os
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from whisperforge_core import adapters, audio, llm, notion, pipeline
from whisperforge_core import prompts as prompts_mod
from whisperforge_core.config import DEFAULT_PROMPTS, LLM_MODELS

import styles

load_dotenv()

_adapters = adapters.get_adapters()


# ---- UI helpers -----------------------------------------------------------

def local_css():
    """Inject the WhisperForge cyberpunk theme (styles.CSS)."""
    st.markdown(styles.CSS, unsafe_allow_html=True)


# ---- Delegates for the UI -------------------------------------------------
# These wrap whisperforge_core with the signatures the legacy UI expects and
# with streamlit-aware progress / error surfaces where useful.

def get_available_users():
    return prompts_mod.list_users()


def load_user_knowledge_base(user):
    return prompts_mod.load_knowledge_base(user)


def get_available_models(provider):
    return list(LLM_MODELS.get(provider, {}).values())


def get_custom_prompt(user, prompt_type, users_prompts, default_prompts):
    return prompts_mod.get_prompt(user, prompt_type, users_prompts) or default_prompts.get(prompt_type, "")


def transcribe_audio(audio_file):
    """Route an uploaded Streamlit file (or path string) through the core
    transcriber, surfacing errors via st.error."""
    try:
        if isinstance(audio_file, str):
            return _adapters.transcriber.transcribe(audio_file)
        suffix = "." + audio_file.name.rsplit(".", 1)[-1] if "." in audio_file.name else ".mp3"
        return _adapters.transcriber.transcribe(audio_file.getvalue(), suffix=suffix)
    except Exception as e:
        st.error(f"Transcription error: {e}")
        return ""


def generate_short_title(text):
    return llm.generate_title(text)


def create_content_notion_entry(title, transcript, wisdom=None, outline=None,
                                social_content=None, image_prompts=None, article=None):
    """Build a ContentBundle from session_state + args, save to Notion."""
    audio_filename = None
    if getattr(st.session_state, "audio_file", None):
        audio_filename = st.session_state.audio_file.name

    if not title or title.startswith("Transcription -") or title.startswith("Content -"):
        title = f"WHISPER: {llm.generate_title(transcript)}"

    summary = llm.generate_summary(transcript)
    tags = llm.generate_tags((transcript or "") + " " + (wisdom or ""), max_tags=5) or ["audio", "transcription", "content", "notes", "whisperforge"]

    models_used = []
    provider = getattr(st.session_state, "ai_provider", None)
    model = getattr(st.session_state, "ai_model", None)
    if provider and model:
        models_used.append(f"{provider} {model}")
    if transcript:
        models_used.append("OpenAI Whisper-1")

    bundle = notion.ContentBundle(
        title=title,
        transcript=transcript or "",
        wisdom=wisdom or "",
        outline=outline or "",
        social_content=social_content or "",
        image_prompts=image_prompts or "",
        article=article or "",
        summary=summary,
        tags=tags,
        audio_filename=audio_filename,
        models_used=models_used,
    )
    try:
        url = _adapters.storage.save(bundle)
    except Exception as e:
        st.error(f"Detailed error creating Notion entry: {e}")
        return False
    if url:
        st.success("Successfully saved to Notion!")
        st.markdown(f"[Open in Notion]({url})")
        return url
    st.error("Notion save failed — see logs.")
    return False


def _generate(content_type, context, provider, model, custom_prompt, knowledge_base):
    """Shared delegate body for all five legacy generate_* wrappers."""
    return _adapters.processor.generate(content_type, context, provider, model,
                                        prompt=custom_prompt, knowledge_base=knowledge_base)


def generate_wisdom(transcript, ai_provider, model, custom_prompt=None, knowledge_base=None):
    return _generate("wisdom_extraction", {"transcript": transcript},
                     ai_provider, model, custom_prompt, knowledge_base)


def generate_outline(transcript, wisdom, ai_provider, model, custom_prompt=None, knowledge_base=None):
    return _generate("outline_creation", {"transcript": transcript, "wisdom": wisdom or ""},
                     ai_provider, model, custom_prompt, knowledge_base)


def generate_social_content(wisdom, outline, ai_provider, model, custom_prompt=None, knowledge_base=None):
    return _generate("social_media", {"wisdom": wisdom or "", "outline": outline or ""},
                     ai_provider, model, custom_prompt, knowledge_base)


def generate_image_prompts(wisdom, outline, ai_provider, model, custom_prompt=None, knowledge_base=None):
    return _generate("image_prompts", {"wisdom": wisdom or "", "outline": outline or ""},
                     ai_provider, model, custom_prompt, knowledge_base)


def generate_article(transcript, wisdom, outline, ai_provider, model, custom_prompt=None, knowledge_base=None):
    return _generate("article_writing",
                     {"transcript": transcript, "wisdom": wisdom or "", "outline": outline or ""},
                     ai_provider, model, custom_prompt, knowledge_base)


def process_all_content(text, ai_provider, model, knowledge_base=None):
    """Run the full 5-stage pipeline with a streamlit progress bar."""
    bar = st.progress(0)
    status = st.empty()

    def cb(frac, label):
        bar.progress(min(max(frac, 0.0), 1.0))
        status.text(label)

    result = _adapters.processor.run_pipeline(text, ai_provider, model,
                                              knowledge_base=knowledge_base, progress=cb)
    status.text("Content generation complete!")
    return {
        "wisdom": result.wisdom,
        "outline": result.outline,
        "social_posts": result.social_posts,
        "image_prompts": result.image_prompts,
        "article": result.article,
    }


def configure_prompts(selected_user, users_prompts):
    """Configure custom prompts for the selected user"""
    st.subheader("Custom Prompts")
    st.write("Configure custom prompts for different content types:")
    
    # List of prompt types
    prompt_types = ["wisdom_extraction", "summary", "outline_creation", "social_media", "image_prompts"]
    
    for prompt_type in prompt_types:
        # Get current prompt for the user and type
        current_prompt = get_custom_prompt(selected_user, prompt_type, users_prompts, DEFAULT_PROMPTS)
        
        # Display text area for editing
        new_prompt = st.text_area(
            f"{prompt_type.replace('_', ' ').title()}",
            value=current_prompt,
            height=150,
            key=f"prompt_{prompt_type}"
        )
        
        # Save button for this prompt
        if st.button(f"Save {prompt_type.replace('_', ' ').title()} Prompt"):
            # Create user directory if it doesn't exist
            user_dir = os.path.join("prompts", selected_user)
            os.makedirs(user_dir, exist_ok=True)
            
            # Save the prompt
            with open(os.path.join(user_dir, f"{prompt_type}.md"), "w") as f:
                f.write(new_prompt)
            
            st.success(f"Saved custom {prompt_type} prompt for {selected_user}")
            
            # Update the in-memory prompts
            if selected_user not in users_prompts:
                users_prompts[selected_user] = {}
            users_prompts[selected_user][prompt_type] = new_prompt


def main():
    # Initialize session state variables first to avoid errors
    if 'transcription' not in st.session_state:
        st.session_state.transcription = ""
    if 'wisdom' not in st.session_state:
        st.session_state.wisdom = ""
    if 'audio_file' not in st.session_state:
        st.session_state.audio_file = None
    # Default to Claude Haiku 4.5 — fast, cheap, good-enough quality.
    # Override in the sidebar to switch to Sonnet/Opus for premium drafts
    # or Ollama (local) for private/offline runs.
    if 'ai_provider' not in st.session_state:
        st.session_state.ai_provider = "Anthropic"
    if 'ai_model' not in st.session_state:
        st.session_state.ai_model = "claude-haiku-4-5"
    
    # Apply the improved cyberpunk theme
    local_css()
    
    # Create a custom header with the refined styling
    st.markdown(f"""
    <div class="header-container">
        <div class="header-title">WhisperForge // Control_Center</div>
        <div class="header-date">{datetime.now().strftime('%a %d %b %Y · %H:%M')}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar configuration
    with st.sidebar:
        st.markdown('<div class="section-header">Configuration</div>', unsafe_allow_html=True)
        
        # Get available users
        selected_user = st.selectbox("User Profile", options=get_available_users(), key="user_profile")
        
        # Load knowledge base for selected user
        knowledge_base = load_user_knowledge_base(selected_user)
        
        # AI Provider selection in sidebar with clean UI
        ai_provider = st.selectbox(
            "AI Provider", 
            options=["OpenAI", "Anthropic"],
            key="ai_provider_select",
            on_change=lambda: setattr(st.session_state, 'ai_model', None)  # Reset model when provider changes
        )
        st.session_state.ai_provider = ai_provider
        
        # Fetch and display available models based on provider
        available_models = get_available_models(ai_provider)
        
        # Model descriptions for helpful UI
        model_descriptions = {
            "gpt-4": "Most capable OpenAI model",
            "gpt-3.5-turbo": "Faster, cost-effective OpenAI model",
            "claude-3-opus-20240229": "Most capable Anthropic model",
            "claude-3-sonnet-20240229": "Balanced Anthropic model",
            "claude-3-haiku-20240307": "Fast, efficient Anthropic model",
        }
        
        # If no model is selected or previous model isn't in new provider's list, select first
        if not st.session_state.ai_model or st.session_state.ai_model not in available_models:
            if available_models:
                st.session_state.ai_model = available_models[0]
        
        # AI Model selection in sidebar
        selected_model = st.selectbox(
            "AI Model",
            options=available_models,
            format_func=lambda x: f"{x}" + (f" ({model_descriptions[x]})" if x in model_descriptions else ""),
            key="ai_model_select"
        )
        st.session_state.ai_model = selected_model
        
        # Move system status to sidebar and clean up UI
        st.markdown('<div class="section-header">System Status</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="status-container">
            <div class="status-card">
                <h3>AI Provider</h3>
                <div class="status-value" id="ai-provider-value">OpenAI</div>
            </div>
            <div class="status-card">
                <h3>Security</h3>
                <div class="status-value" id="security-status">Encrypted</div>
            </div>
            <div class="status-card">
                <h3>Status</h3>
                <div class="status-value" id="content-status">Ready</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Update the status card with JavaScript
        st.markdown(f"""
        <script>
            document.getElementById('ai-provider-value').innerText = '{ai_provider}';
        </script>
        """, unsafe_allow_html=True)
        
        # Configure custom prompts in a cleaner way
        with st.expander("Custom Prompts", expanded=False):
            users_prompts = {}  # Initialize empty prompts dict
            configure_prompts(selected_user, users_prompts)
            
        # Knowledge Base Management
        with st.expander("Knowledge Base", expanded=False):
            st.markdown("### Knowledge Base Files")
            
            if knowledge_base:
                # Use selectbox instead of nested expanders
                selected_file = st.selectbox(
                    "Select file to view",
                    options=list(knowledge_base.keys()),
                    key="kb_file_selector"
                )
                if selected_file:
                    st.text_area(
                        "Content",
                        value=knowledge_base[selected_file],
                        height=100,
                        key=f"kb_{selected_file}",
                        disabled=True
                    )
            else:
                st.info("No knowledge base files found.")
            
            # Upload new knowledge base file
            st.markdown("### Add New Knowledge")
            
            uploaded_kb = st.file_uploader(
                "Add Knowledge Base File", 
                type=['txt', 'md'],
                key="kb_uploader"
            )
            
            if uploaded_kb:
                kb_name = st.text_input("File Name (without extension)", 
                                      value=os.path.splitext(uploaded_kb.name)[0])
                if st.button("Save to Knowledge Base"):
                    try:
                        kb_path = f'prompts/{selected_user}/knowledge_base'
                        os.makedirs(kb_path, exist_ok=True)
                        
                        with open(os.path.join(kb_path, f"{kb_name}.md"), "wb") as f:
                            f.write(uploaded_kb.getvalue())
                        st.success("Knowledge base file added successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error saving knowledge base file: {str(e)}")
    
    # Add tabs for input selection
    input_tabs = st.tabs(["Audio Upload", "Text Input"])
    
    # Tab 1: Audio Upload
    with input_tabs[0]:
        st.markdown('<div class="section-header">Audio Transcription</div>', unsafe_allow_html=True)
        
        # Update the file uploader with clear message about 500MB limit
        uploaded_file = st.file_uploader(
            "Upload your audio file", 
            type=['mp3', 'wav', 'ogg', 'm4a'],
            key="audio_uploader",
            help="Files up to 500MB are supported. Large files will be automatically chunked for processing."
        )
        
        # Add custom message about large file support
        st.markdown("""
        <div style="font-size: 0.85rem; color: var(--text-secondary); margin-top: -15px; margin-bottom: 15px;">
            Large files (up to 500MB) are automatically chunked for optimal processing.
        </div>
        """, unsafe_allow_html=True)
        
        # Display the audio player if a file is uploaded
        if uploaded_file is not None:
            st.audio(uploaded_file, format='audio/wav')
        
        # Always display the buttons and disable if no file
        col1, col2 = st.columns(2)
        
        with col1:
            transcribe_disabled = uploaded_file is None
            transcribe_button = st.button(
                "Transcribe Audio", 
                key="transcribe_button", 
                use_container_width=True,
                disabled=transcribe_disabled
            )
        
        with col2:
            lucky_disabled = uploaded_file is None
            lucky_button = st.button(
                "I'm Feeling Lucky", 
                key="lucky_button", 
                use_container_width=True,
                disabled=lucky_disabled
            )
        
        # Display a helpful message when no file is uploaded
        if uploaded_file is None:
            st.info("👆 Upload an audio file to begin transcription and processing")
        
        # Process based on which button was clicked
        if uploaded_file is not None:
            if transcribe_button:
                try:
                    with st.spinner("Transcribing..."):
                        # Process the audio file
                        transcription = transcribe_audio(uploaded_file)
                        st.session_state.transcription = transcription
                        st.session_state.audio_file = uploaded_file
                        
                        # Show transcription
                        st.text_area("Transcription", transcription, height=200)
                        
                        # Add a process content button after transcription
                        process_button = st.button("Process Content", key="process_after_transcribe", use_container_width=True)
                        if process_button:
                            with st.spinner("Processing content with AI..."):
                                results = process_all_content(
                                    transcription, 
                                    st.session_state.ai_provider, 
                                    st.session_state.ai_model,
                                    knowledge_base
                                )
                                for key, value in results.items():
                                    st.session_state[key] = value
                except Exception as e:
                    st.error(f"Transcription error: {str(e)}")
                    st.error("Please make sure your audio file is in a supported format and not corrupted.")
            
            elif lucky_button:
                try:
                    with st.spinner("Working magic - transcribing and processing audio..."):
                        # First transcribe
                        transcription = transcribe_audio(uploaded_file)
                        st.session_state.transcription = transcription
                        st.session_state.audio_file = uploaded_file
                        
                        # Show transcription
                        st.text_area("Transcription", transcription, height=200)
                        
                        # Now process everything and post to Notion in one go
                        with st.spinner("Generating content..."):
                            results = process_all_content(
                                transcription, 
                                st.session_state.ai_provider, 
                                st.session_state.ai_model,
                                knowledge_base
                            )
                            
                            if results:
                                for key, value in results.items():
                                    st.session_state[key] = value
                                
                                # Generate title for Notion
                                title = generate_short_title(transcription)
                                
                                # Post to Notion if credentials are available
                                notion_api_key = os.environ.get('NOTION_API_KEY', '')
                                notion_database_id = os.environ.get('NOTION_DATABASE_ID', '')
                                
                                if notion_api_key and notion_database_id:
                                    with st.spinner("Exporting to Notion..."):
                                        create_content_notion_entry(
                                            title,
                                            transcription,
                                            results.get('wisdom'),
                                            results.get('outline'),
                                            results.get('social_posts'),
                                            results.get('image_prompts'),
                                            results.get('article')
                                        )
                                        st.success("Everything processed and saved to Notion!")
                                else:
                                    st.success("Everything processed!")
                                    st.info("To export to Notion, configure NOTION_API_KEY and NOTION_DATABASE_ID environment variables.")
                except Exception as e:
                    st.error(f"Processing error: {str(e)}")
                    st.error("Please make sure your audio file is in a supported format and not corrupted.")
    
    # Tab 2: Text Input
    with input_tabs[1]:
        st.markdown('<div class="section-header">Text Processing</div>', unsafe_allow_html=True)
        
        text_input = st.text_area("Enter your text", height=200, key="text_input_area")
        
        if text_input:
            if st.button("I'm Feeling Lucky", key="text_lucky_button", use_container_width=True):
                # Create placeholder elements for streaming updates
                progress_placeholder = st.empty()
                wisdom_placeholder = st.empty()
                outline_placeholder = st.empty()
                social_placeholder = st.empty()
                image_placeholder = st.empty()
                article_placeholder = st.empty()
                export_placeholder = st.empty()
                
                # Store the text input as transcription
                st.session_state.transcription = text_input
                
                # Generate wisdom with streaming feedback
                with progress_placeholder.container():
                    st.info("Step 1/6: Extracting key insights...")
                
                wisdom = generate_wisdom(
                    text_input, 
                    st.session_state.ai_provider, 
                    st.session_state.ai_model,
                    knowledge_base=knowledge_base
                )
                st.session_state.wisdom = wisdom
                
                # Update wisdom placeholder
                with wisdom_placeholder.container():
                    st.subheader("Key Insights")
                    st.markdown(wisdom)
                
                # Create outline with streaming updates
                with progress_placeholder.container():
                    st.info("Step 2/6: Creating content outline...")
                
                outline = generate_outline(
                    text_input, 
                    wisdom,
                    st.session_state.ai_provider, 
                    st.session_state.ai_model,
                    knowledge_base=knowledge_base
                )
                st.session_state.outline = outline
                
                # Update outline placeholder
                with outline_placeholder.container():
                    st.subheader("Content Outline")
                    st.markdown(outline)
                
                # Social content
                with progress_placeholder.container():
                    st.info("Step 3/6: Generating social media posts...")
                
                social_content = generate_social_content(
                    wisdom,
                    outline,
                    st.session_state.ai_provider, 
                    st.session_state.ai_model,
                    knowledge_base=knowledge_base
                )
                st.session_state.social_posts = social_content
                
                # Update social placeholder
                with social_placeholder.container():
                    st.subheader("Social Media Posts")
                    st.markdown(social_content)
                
                # Image prompts
                with progress_placeholder.container():
                    st.info("Step 4/6: Creating image prompts...")
                
                image_prompts = generate_image_prompts(
                    wisdom,
                    outline,
                    st.session_state.ai_provider, 
                    st.session_state.ai_model,
                    knowledge_base=knowledge_base
                )
                st.session_state.image_prompts = image_prompts
                
                # Update image placeholder
                with image_placeholder.container():
                    st.subheader("Image Prompts")
                    st.markdown(image_prompts)
                
                # Article
                with progress_placeholder.container():
                    st.info("Step 5/6: Writing full article...")
                
                article = generate_article(
                    text_input,
                    wisdom,
                    outline,
                    st.session_state.ai_provider, 
                    st.session_state.ai_model,
                    knowledge_base=knowledge_base
                )
                st.session_state.article = article
                
                # Update article placeholder
                with article_placeholder.container():
                    st.subheader("Full Article")
                    st.markdown(article)
                
                # Generate title for Notion
                title = generate_short_title(text_input)
                
                # Post to Notion if credentials are available
                notion_api_key = os.environ.get('NOTION_API_KEY', '')
                notion_database_id = os.environ.get('NOTION_DATABASE_ID', '')
                
                if notion_api_key and notion_database_id:
                    with progress_placeholder.container():
                        st.info("Step 6/6: Exporting to Notion...")
                    
                    try:
                        notion_url = create_content_notion_entry(
                            title,
                            text_input,
                            wisdom,
                            outline,
                            social_content,
                            image_prompts,
                            article
                        )
                        
                        with export_placeholder.container():
                            st.success("Everything processed and saved to Notion!")
                            if notion_url:
                                st.markdown(f"[Open in Notion]({notion_url})")
                    except Exception as e:
                        with export_placeholder.container():
                            st.error(f"Error exporting to Notion: {str(e)}")
                else:
                    with progress_placeholder.container():
                        st.success("All content processed!")
                        st.info("To export to Notion, configure NOTION_API_KEY and NOTION_DATABASE_ID environment variables.")
                    
                # Final progress update
                with progress_placeholder.container():
                    st.success("Content generation complete!")
    
    # Display generated content in the main area, below the input tabs
    if st.session_state.transcription:
        if 'wisdom' in st.session_state and st.session_state.wisdom:
            st.markdown('<div class="section-header">Generated Content</div>', unsafe_allow_html=True)
            
            # Key Insights section
            st.markdown("### Key Insights")
            st.markdown(st.session_state.wisdom)
            
            # Display other generated content if available
            if 'outline' in st.session_state and st.session_state.outline:
                st.markdown("### Content Outline")
                st.markdown(st.session_state.outline)
            
            if 'social_content' in st.session_state and st.session_state.social_content:
                st.markdown("### Social Media Posts")
                st.markdown(st.session_state.social_content)
            
            if 'image_prompts' in st.session_state and st.session_state.image_prompts:
                st.markdown("### Image Generation Prompts")
                st.markdown(st.session_state.image_prompts)
            
            if 'article' in st.session_state and st.session_state.article:
                st.markdown("### Full Article")
                st.markdown(st.session_state.article)
            
            # Export to Notion section
            st.markdown('<div class="section-header">Export Options</div>', unsafe_allow_html=True)
            
            notion_api_key = os.environ.get('NOTION_API_KEY', '')
            notion_database_id = os.environ.get('NOTION_DATABASE_ID', '')
            
            if notion_api_key and notion_database_id:
                if st.button("Export to Notion"):
                    with st.spinner("Exporting to Notion..."):
                        try:
                            title = generate_short_title(st.session_state.transcription)
                            create_content_notion_entry(
                                title,
                                st.session_state.transcription,
                                st.session_state.wisdom if 'wisdom' in st.session_state else None,
                                st.session_state.outline if 'outline' in st.session_state else None,
                                st.session_state.social_content if 'social_content' in st.session_state else None,
                                st.session_state.image_prompts if 'image_prompts' in st.session_state else None,
                                st.session_state.article if 'article' in st.session_state else None
                            )
                            st.success("Successfully exported to Notion!")
                        except Exception as e:
                            st.error(f"Error exporting to Notion: {str(e)}")
            else:
                st.info("To export to Notion, please configure the NOTION_API_KEY and NOTION_DATABASE_ID environment variables.")
    
    # Add the footer
    st.markdown("""
    <div class="app-footer">
        <div class="footer-content">
            <div>WhisperForge Control Center v1.0</div>
            <div class="footer-status">
                <span class="status-secure"><span class="footer-status-dot"></span>Encrypted</span>
                <span class="status-sovereignty"><span class="footer-status-dot"></span>Knowledge Sovereignty</span>
                <span class="status-offline"><span class="footer-status-dot"></span>Offline Capable</span>
            </div>
            <div>© 2025 CypherMedia Group</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Default prompts in case user prompts are not available


if __name__ == "__main__":
    main()
