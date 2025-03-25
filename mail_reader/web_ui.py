"""
Web UI for Email Reader application using Streamlit
"""
import streamlit as st
import os
from dotenv import load_dotenv
from core.email_reader import EmailReader
import pandas as pd
import plotly.express as px
import time
from datetime import datetime
import threading
import queue
import pathlib

def save_credentials(host, port, username, password, spam_folder):
    """Save credentials to .env file"""
    with open('.env', 'w') as f:
        f.write(f'EMAIL_HOST={host}\n')
        f.write(f'EMAIL_PORT={port}\n')
        f.write(f'EMAIL_USER={username}\n')
        f.write(f'EMAIL_PASSWORD={password}\n')
        f.write(f'SPAM_FOLDER={spam_folder}\n')

def initialize_session_state():
    """Initialize session state variables"""
    if 'processing' not in st.session_state:
        st.session_state.processing = False
    if 'progress' not in st.session_state:
        st.session_state.progress = 0
    if 'processed_emails' not in st.session_state:
        st.session_state.processed_emails = 0
    if 'current_stats' not in st.session_state:
        st.session_state.current_stats = {
            'total_emails': 0,
            'advertisements': 0,
            'unique_senders': set(),
            'processing_times': [],
            'ad_rate': 0
        }
    if 'live_updates' not in st.session_state:
        st.session_state.live_updates = queue.Queue()

def process_email_with_updates(reader, num_emails):
    """Process emails and update session state"""
    try:
        st.session_state.processing = True
        st.session_state.progress = 0
        st.session_state.processed_emails = 0
        
        def update_callback(email_info):
            """Callback function to update processing stats"""
            st.session_state.processed_emails += 1
            st.session_state.progress = st.session_state.processed_emails / num_emails
            
            # Update current stats
            stats = st.session_state.current_stats
            stats['total_emails'] += 1
            stats['unique_senders'].add(email_info['sender'])
            if email_info['is_ad']:
                stats['advertisements'] += 1
            stats['ad_rate'] = (stats['advertisements'] / stats['total_emails']) * 100
            stats['processing_times'].append(datetime.now())
            
            # Add update to queue
            st.session_state.live_updates.put(email_info)

        # Set the callback in the reader
        reader.set_update_callback(update_callback)
        reader.process_emails(num_emails=num_emails)
        
    finally:
        st.session_state.processing = False

def main():
    st.set_page_config(
        page_title="Email Reader Dashboard",
        page_icon="📧",
        layout="wide"
    )

    # Initialize session state
    initialize_session_state()

    st.title("📧 Email Reader Dashboard")

    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        
        # Email Server Settings
        st.subheader("Email Server Settings")
        host = st.text_input("Email Host", value="pop.gmail.com")
        port = st.number_input("Port", value=995, min_value=1, max_value=65535)
        username = st.text_input("Email Username")
        password = st.text_input("Password", type="password")

        # Spam Folder Settings
        st.subheader("Spam Management")
        spam_folder = st.text_input(
            "Spam Storage Folder",
            value=os.path.join(os.path.expanduser("~"), "MailReader", "spam"),
            help="Folder where deleted spam emails will be stored"
        )
        delete_spam = st.checkbox(
            "Delete spam from server",
            value=True,
            help="If enabled, spam emails will be deleted from the server and stored locally"
        )

        # Processing Parameters
        st.subheader("Processing Parameters")
        num_emails = st.number_input("Number of Emails to Process", 
                                   value=10, min_value=1, max_value=1000)
        num_processes = st.number_input("Number of Parallel Processes", 
                                      value=max(1, os.cpu_count() - 1), 
                                      min_value=1, 
                                      max_value=os.cpu_count())
        
        # Advertisement Detection Settings
        st.subheader("Advertisement Detection")
        min_indicators = st.slider("Minimum Ad Indicators", 
                                 min_value=1, max_value=5, value=2,
                                 help="Minimum number of advertisement indicators required to classify as ad")

        # Save credentials and start processing
        if st.button("Start Processing", type="primary", disabled=st.session_state.processing):
            # Create spam folder if it doesn't exist
            os.makedirs(spam_folder, exist_ok=True)
            
            save_credentials(host, port, username, password, spam_folder)
            reader = EmailReader()
            reader.num_processes = num_processes
            reader.delete_spam = delete_spam
            
            # Start processing in a separate thread
            processing_thread = threading.Thread(
                target=process_email_with_updates,
                args=(reader, num_emails)
            )
            processing_thread.start()

    # Main content area
    if st.session_state.processing:
        # Show progress bar
        st.progress(st.session_state.progress)
        st.write(f"Processed {st.session_state.processed_emails} of {num_emails} emails")

        # Real-time metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Processed Emails", st.session_state.current_stats['total_emails'])
        with col2:
            st.metric("Advertisements", st.session_state.current_stats['advertisements'])
        with col3:
            st.metric("Unique Senders", len(st.session_state.current_stats['unique_senders']))
        with col4:
            st.metric("Ad Rate", f"{st.session_state.current_stats['ad_rate']:.1f}%")

        # Real-time charts
        tab1, tab2 = st.tabs(["📈 Live Analytics", "📋 Recent Emails"])
        
        with tab1:
            col1, col2 = st.columns(2)
            
            with col1:
                # Real-time email processing rate
                if st.session_state.current_stats['processing_times']:
                    times_df = pd.DataFrame({
                        'time': st.session_state.current_stats['processing_times'],
                        'count': range(1, len(st.session_state.current_stats['processing_times']) + 1)
                    })
                    fig = px.line(times_df, x='time', y='count',
                                title='Email Processing Rate',
                                labels={'count': 'Emails Processed', 'time': 'Time'})
                    st.plotly_chart(fig, use_container_width=True)

            with col2:
                # Real-time ad vs non-ad ratio
                fig = px.pie(
                    values=[st.session_state.current_stats['advertisements'],
                           st.session_state.current_stats['total_emails'] - st.session_state.current_stats['advertisements']],
                    names=['Advertisements', 'Regular Emails'],
                    title='Advertisement Distribution (Live)',
                    color_discrete_sequence=['#ff9999', '#66b3ff']
                )
                st.plotly_chart(fig, use_container_width=True)

        with tab2:
            # Show recent emails in a table
            if not st.session_state.live_updates.empty():
                recent_emails = []
                while not st.session_state.live_updates.empty():
                    recent_emails.append(st.session_state.live_updates.get())
                
                recent_df = pd.DataFrame(recent_emails)
                st.dataframe(recent_df, use_container_width=True)

    # Show historical data if available
    if not st.session_state.processing and os.path.exists('email_contacts.csv'):
        st.header("Historical Data")
        contacts_df = pd.read_csv('email_contacts.csv')
        
        # Display statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Contacts", len(contacts_df))
        with col2:
            ad_rate = (contacts_df['is_advertisement'].sum() / len(contacts_df) * 100)
            st.metric("Advertisement Rate", f"{ad_rate:.1f}%")
        with col3:
            st.metric("Total Emails", contacts_df['total_emails'].sum())

        # Create tabs for different views
        tab1, tab2 = st.tabs(["📊 Analytics", "📋 Raw Data"])
        
        with tab1:
            # Email volume over time
            st.subheader("Email Activity")
            contacts_df['last_contact'] = pd.to_datetime(contacts_df['last_contact'])
            daily_counts = contacts_df.groupby(contacts_df['last_contact'].dt.date).size()
            fig = px.line(daily_counts, 
                        title='Email Volume Over Time',
                        labels={'value': 'Number of Emails', 'index': 'Date'})
            st.plotly_chart(fig, use_container_width=True)

            # Advertisement distribution
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Advertisement Distribution")
                fig = px.pie(contacts_df, 
                           names='is_advertisement', 
                           title='Advertisement vs Regular Emails',
                           color_discrete_sequence=['#ff9999', '#66b3ff'])
                st.plotly_chart(fig)

            with col2:
                st.subheader("Top Senders")
                top_senders = contacts_df.nlargest(10, 'total_emails')[['email', 'total_emails']]
                fig = px.bar(top_senders, 
                            x='email', y='total_emails',
                            title='Top 10 Email Senders')
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig)

        with tab2:
            st.subheader("Email Contacts Data")
            st.dataframe(contacts_df, use_container_width=True)

if __name__ == "__main__":
    main() 