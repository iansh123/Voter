import os
import logging
import threading
import time
import json
from flask import Flask, render_template, request, jsonify, session
from vote_automation import vote_in_poll
from proxy_manager import proxy_manager

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Set up Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key")

# Store voting progress and status for each session
vote_status = {}

@app.route('/')
def index():
    """Render the main page"""
    # Fetch initial proxies
    proxy_manager.refresh_proxies()
    
    # Count the number of available proxies
    proxy_count = len(proxy_manager.proxies)
    
    return render_template('index.html', proxy_count=proxy_count)

@app.route('/start_voting', methods=['POST'])
def start_voting():
    """Start the voting process with the given number of votes"""
    try:
        num_votes = int(request.form.get('num_votes', 1))
        
        # Check if a valid number was provided
        if num_votes <= 0:
            return jsonify({'status': 'error', 'message': 'Please enter a positive number of votes'}), 400
        
        # Check if proxies should be used
        use_proxies = request.form.get('use_proxies') == 'on'
        
        # Get custom proxies if provided
        custom_proxies = []
        custom_proxies_text = request.form.get('custom_proxies', '').strip()
        if custom_proxies_text:
            custom_proxies = [p.strip() for p in custom_proxies_text.split('\n') if p.strip()]
            
            # Load the custom proxies into the proxy manager if using proxies
            if use_proxies and custom_proxies:
                proxy_manager.load_custom_proxies(custom_proxies)
                # Force refresh of proxies to use the custom ones
                proxy_manager.refresh_proxies(force=True)
        
        # Generate a unique session ID for this voting session
        session_id = str(int(time.time()))
        session['voting_session_id'] = session_id
        
        # Initialize status for this session
        vote_status[session_id] = {
            'total_votes': num_votes,
            'completed_votes': 0,
            'current_status': 'Starting...',
            'log_messages': [],
            'is_running': True,
            'success_count': 0,
            'error_count': 0,
            'use_proxies': use_proxies
        }
        
        # Start voting in a separate thread
        voting_thread = threading.Thread(
            target=run_voting_process,
            args=(session_id, num_votes)
        )
        voting_thread.daemon = True
        voting_thread.start()
        
        proxy_message = ""
        if use_proxies:
            proxy_count = len(proxy_manager.proxies)
            proxy_message = f" using {proxy_count} proxies"
            if custom_proxies:
                proxy_message += f" ({len(custom_proxies)} custom)"
        
        return jsonify({
            'status': 'success', 
            'message': f'Started voting process for {num_votes} votes{proxy_message}',
            'session_id': session_id
        })
    
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Please enter a valid number'}), 400
    except Exception as e:
        logging.error(f"Error starting voting process: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Error: {str(e)}'}), 500

@app.route('/check_status', methods=['GET'])
def check_status():
    """Check the status of the current voting process"""
    session_id = session.get('voting_session_id')
    
    if not session_id or session_id not in vote_status:
        return jsonify({'status': 'error', 'message': 'No active voting session found'}), 404
    
    # Return the current status
    return jsonify(vote_status[session_id])

@app.route('/stop_voting', methods=['POST'])
def stop_voting():
    """Stop the current voting process"""
    session_id = session.get('voting_session_id')
    
    if not session_id or session_id not in vote_status:
        return jsonify({'status': 'error', 'message': 'No active voting session found'}), 404
    
    # Mark the session as stopped
    vote_status[session_id]['is_running'] = False
    vote_status[session_id]['current_status'] = 'Stopped by user'
    
    return jsonify({
        'status': 'success',
        'message': 'Voting process stopped'
    })

def update_status(session_id, message, success=None):
    """Update the status of the voting process"""
    if session_id in vote_status:
        vote_status[session_id]['current_status'] = message
        vote_status[session_id]['log_messages'].append(message)
        
        # If this is a vote result, update the count
        if success is not None:
            if success:
                vote_status[session_id]['success_count'] += 1
            else:
                vote_status[session_id]['error_count'] += 1

def vote_task(session_id, vote_num, total_votes):
    """Run a single voting task in a thread"""
    try:
        # Update status for this vote
        update_status(session_id, f"Starting vote attempt {vote_num+1} of {total_votes}...")
        
        # Check if proxies should be used for this session
        use_proxy = vote_status[session_id].get('use_proxies', False)
        
        # Call the voting function with callback for updates
        if use_proxy:
            # Get next proxy from manager if using proxies
            success = vote_in_poll(
                callback=lambda msg: update_status(session_id, f"Vote {vote_num+1}: {msg}")
            )
        else:
            # Don't use proxy
            success = vote_in_poll(
                callback=lambda msg: update_status(session_id, f"Vote {vote_num+1}: {msg}"),
                custom_proxy=None  # Explicitly disable proxy
            )
        
        # Update status with the result
        if success:
            update_status(session_id, f"Vote {vote_num+1} completed successfully!", True)
        else:
            update_status(session_id, f"Vote {vote_num+1} failed or could not be confirmed", False)
        
        # Update completed votes
        with threading.Lock():
            vote_status[session_id]['completed_votes'] += 1
            
            # Check if all votes are complete
            if vote_status[session_id]['completed_votes'] >= vote_status[session_id]['total_votes']:
                vote_status[session_id]['is_running'] = False
                vote_status[session_id]['current_status'] = "Voting process completed"
    
    except Exception as e:
        logging.error(f"Error in voting task {vote_num+1}: {str(e)}")
        update_status(session_id, f"Error in vote {vote_num+1}: {str(e)}", False)

def run_voting_process(session_id, num_votes):
    """Run the voting process with multiple concurrent votes"""
    try:
        # Determine the number of concurrent threads to use
        # We'll use a maximum of 5 concurrent threads or the number of votes, whichever is smaller
        max_concurrent = min(5, num_votes)
        
        update_status(session_id, f"Starting voting process with up to {max_concurrent} concurrent votes...")
        
        # Create and start threads for each vote
        threads = []
        for i in range(num_votes):
            # Check if the process should be stopped
            if session_id not in vote_status or not vote_status[session_id]['is_running']:
                break
            
            # Create a thread for this vote
            vote_thread = threading.Thread(
                target=vote_task,
                args=(session_id, i, num_votes)
            )
            vote_thread.daemon = True
            threads.append(vote_thread)
            
            # Start the thread
            vote_thread.start()
            
            # If we've reached the max concurrent threads or this is the last vote,
            # wait for the oldest thread to complete before starting more
            if len(threads) >= max_concurrent:
                # Wait for the oldest thread to complete (first in the list)
                threads[0].join()
                threads.pop(0)
            
            # Add a small delay between starting threads to avoid overwhelming the server
            time.sleep(0.5)
        
        # Wait for any remaining threads to complete
        for thread in threads:
            thread.join()
            
    except Exception as e:
        logging.error(f"Error in voting process: {str(e)}")
        if session_id in vote_status:
            vote_status[session_id]['is_running'] = False
            vote_status[session_id]['current_status'] = f"Error: {str(e)}"
