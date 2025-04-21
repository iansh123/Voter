import os
import logging
import threading
import time
import json
import math
import uuid
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
        session_id = str(uuid.uuid4())
        session['voting_session_id'] = session_id
        
        # Calculate batch information for large vote counts
        batch_size = 100  # Process votes in batches of 100
        total_batches = math.ceil(num_votes / batch_size)
        
        # Initialize status for this session
        vote_status[session_id] = {
            'total_votes': num_votes,
            'completed_votes': 0,
            'current_status': f'Starting vote process with {total_batches} batches...',
            'log_messages': [],
            'is_running': True,
            'success_count': 0,
            'error_count': 0,
            'batch_size': batch_size,
            'total_batches': total_batches,
            'current_batch': 1
        }
        
        # Start voting in a separate thread
        voting_thread = threading.Thread(
            target=batch_voting_manager,
            args=(session_id, num_votes, batch_size)
        )
        voting_thread.daemon = True
        voting_thread.start()
        
        return jsonify({
            'status': 'success', 
            'message': f'Started voting process for {num_votes} votes (in {total_batches} batches)',
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
        
        # Call the voting function with callback for updates
        success = vote_in_poll(
            callback=lambda msg: update_status(session_id, f"Vote {vote_num+1}: {msg}")
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

def run_voting_process(session_id, start_index, num_votes, batch_number=1, total_batches=1):
    """Run the voting process with multiple concurrent votes"""
    try:
        # Determine the number of concurrent threads to use
        # We'll use a maximum of 3 concurrent threads to avoid freezing and server issues
        max_concurrent = min(3, num_votes)
        
        update_status(session_id, f"Starting batch {batch_number}/{total_batches} with up to {max_concurrent} concurrent votes...")
        
        # Create and start threads for each vote
        threads = []
        alive_check_interval = 5  # Check if threads are alive every 5 votes
        
        for i in range(num_votes):
            # Check if the process should be stopped
            if session_id not in vote_status or not vote_status[session_id]['is_running']:
                update_status(session_id, "Voting process stopped by user")
                break
                
            # Check for any frozen threads and clean them up
            if i % alive_check_interval == 0 and threads:
                new_threads = []
                for t in threads:
                    if t.is_alive():
                        new_threads.append(t)
                    else:
                        logging.debug(f"Thread was not responsive, replacing it")
                threads = new_threads
            
            # Global vote number (across all batches)
            global_vote_num = start_index + i
            
            # Create a thread for this vote
            vote_thread = threading.Thread(
                target=vote_task,
                args=(session_id, global_vote_num, vote_status[session_id]['total_votes'])
            )
            vote_thread.daemon = True
            threads.append(vote_thread)
            
            # Start the thread
            vote_thread.start()
            
            # If we've reached the max concurrent threads or this is the last vote,
            # wait for the oldest thread to complete before starting more
            if len(threads) >= max_concurrent:
                try:
                    # Wait for the oldest thread to complete with a timeout
                    threads[0].join(timeout=60)  # 60 second timeout to prevent freezing
                    
                    # If thread is still alive after timeout, leave it but don't wait for it
                    if not threads[0].is_alive():
                        threads.pop(0)
                    else:
                        logging.warning("Thread timed out, continuing with new threads")
                        # Keep track of it but don't wait for it again
                        threads.pop(0)
                except Exception as thread_err:
                    logging.error(f"Error waiting for thread: {str(thread_err)}")
            
            # Add a small delay between starting threads to avoid overwhelming the server
            time.sleep(0.5)
        
        # Wait for remaining threads with a timeout
        for thread in threads:
            try:
                thread.join(timeout=30)  # 30 second timeout per thread
            except Exception as join_err:
                logging.error(f"Error joining thread: {str(join_err)}")
        
        update_status(session_id, f"Completed batch {batch_number}/{total_batches}")
            
    except Exception as e:
        logging.error(f"Error in voting process: {str(e)}")
        if session_id in vote_status:
            update_status(session_id, f"Error in batch {batch_number}: {str(e)}", False)
            
    return True  # Return True to indicate the batch completed (even with errors)

def batch_voting_manager(session_id, total_votes, batch_size=100):
    """Manage voting in batches to handle large number of votes"""
    try:
        # Calculate the number of batches
        total_batches = math.ceil(total_votes / batch_size)
        update_status(session_id, f"Starting {total_votes} votes in {total_batches} batches of {batch_size}")
        
        # Process each batch
        for batch_num in range(1, total_batches + 1):
            # Check if the process should be stopped
            if session_id not in vote_status or not vote_status[session_id]['is_running']:
                break
                
            # Calculate the start index and number of votes for this batch
            start_index = (batch_num - 1) * batch_size
            votes_in_batch = min(batch_size, total_votes - start_index)
            
            # Update status with batch information
            vote_status[session_id]['current_batch'] = batch_num
            update_status(session_id, f"Starting batch {batch_num}/{total_batches} with {votes_in_batch} votes...")
            
            # Run this batch
            batch_result = run_voting_process(
                session_id, 
                start_index, 
                votes_in_batch, 
                batch_num, 
                total_batches
            )
            
            # Short delay between batches
            time.sleep(5)
            
        # Mark the session as completed
        if session_id in vote_status and vote_status[session_id]['is_running']:
            vote_status[session_id]['is_running'] = False
            vote_status[session_id]['current_status'] = "All batches completed"
            
    except Exception as e:
        logging.error(f"Error in batch voting manager: {str(e)}")
        if session_id in vote_status:
            vote_status[session_id]['is_running'] = False
            vote_status[session_id]['current_status'] = f"Error: {str(e)}"
