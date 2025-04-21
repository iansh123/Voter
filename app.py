import os
import logging
import threading
import time
import json
from flask import Flask, render_template, request, jsonify, session
from vote_automation import vote_in_poll

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
    return render_template('index.html')

@app.route('/start_voting', methods=['POST'])
def start_voting():
    """Start the voting process with the given number of votes"""
    try:
        num_votes = int(request.form.get('num_votes', 1))
        
        # Check if a valid number was provided
        if num_votes <= 0:
            return jsonify({'status': 'error', 'message': 'Please enter a positive number of votes'}), 400
        
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
            'error_count': 0
        }
        
        # Start voting in a separate thread
        voting_thread = threading.Thread(
            target=run_voting_process,
            args=(session_id, num_votes)
        )
        voting_thread.daemon = True
        voting_thread.start()
        
        return jsonify({
            'status': 'success', 
            'message': f'Started voting process for {num_votes} votes',
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

def run_voting_process(session_id, num_votes):
    """Run the voting process and update status"""
    try:
        for i in range(num_votes):
            # Check if the process should be stopped
            if session_id not in vote_status or not vote_status[session_id]['is_running']:
                break
                
            update_status(session_id, f"Starting vote attempt {i+1} of {num_votes}...")
            
            # Call the voting function with callback for updates
            success = vote_in_poll(
                callback=lambda msg: update_status(session_id, msg)
            )
            
            # Update status with the result
            if success:
                update_status(session_id, f"Vote {i+1} completed successfully!", True)
            else:
                update_status(session_id, f"Vote {i+1} failed or could not be confirmed", False)
            
            # Update completed votes
            vote_status[session_id]['completed_votes'] = i + 1
            
            # Add a delay between votes if not the last vote and still running
            if i < num_votes - 1 and session_id in vote_status and vote_status[session_id]['is_running']:
                delay = min(5 + (i * 0.5), 15)  # Increase delay slightly with each vote, max 15 seconds
                update_status(session_id, f"Waiting {delay:.1f} seconds before next vote...")
                time.sleep(delay)
        
        # Update final status
        if session_id in vote_status:
            vote_status[session_id]['is_running'] = False
            vote_status[session_id]['current_status'] = "Voting process completed"
            
    except Exception as e:
        logging.error(f"Error in voting process: {str(e)}")
        if session_id in vote_status:
            vote_status[session_id]['is_running'] = False
            vote_status[session_id]['current_status'] = f"Error: {str(e)}"
