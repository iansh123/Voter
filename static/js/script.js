document.addEventListener('DOMContentLoaded', function() {
    const votingForm = document.getElementById('voting-form');
    const startBtn = document.getElementById('start-btn');
    const stopBtn = document.getElementById('stop-btn');
    const statusCard = document.getElementById('status-card');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    const voteStats = document.getElementById('vote-stats');
    const logContainer = document.getElementById('log-container');
    const successCount = document.getElementById('success-count');
    const errorCount = document.getElementById('error-count');
    
    // For storing the status check interval
    let statusCheckInterval = null;
    
    // Add log message to the log container
    function addLogMessage(message) {
        const logEntry = document.createElement('div');
        logEntry.className = 'log-message';
        logEntry.textContent = message;
        logContainer.appendChild(logEntry);
        
        // Scroll to bottom
        logContainer.scrollTop = logContainer.scrollHeight;
    }
    
    // Clear the log container
    function clearLog() {
        logContainer.innerHTML = '';
    }
    
    // Start the voting process
    votingForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const formData = new FormData(votingForm);
        const numVotes = parseInt(formData.get('num_votes'));
        
        if (isNaN(numVotes) || numVotes <= 0) {
            alert('Please enter a valid number of votes.');
            return;
        }
        
        // Update UI state
        startBtn.disabled = true;
        stopBtn.disabled = false;
        statusCard.style.display = 'block';
        clearLog();
        addLogMessage('Starting voting process...');
        
        // Send request to start voting
        fetch('/start_voting', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                addLogMessage(`Successfully started voting process for ${numVotes} votes.`);
                
                // Start status checking
                if (statusCheckInterval) {
                    clearInterval(statusCheckInterval);
                }
                
                statusCheckInterval = setInterval(checkStatus, 1000);
            } else {
                addLogMessage(`Error: ${data.message}`);
                startBtn.disabled = false;
                stopBtn.disabled = true;
            }
        })
        .catch(error => {
            addLogMessage(`Error: ${error.message}`);
            startBtn.disabled = false;
            stopBtn.disabled = true;
        });
    });
    
    // Stop the voting process
    stopBtn.addEventListener('click', function() {
        fetch('/stop_voting', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            addLogMessage(`Stopping voting process...`);
            stopBtn.disabled = true;
        })
        .catch(error => {
            addLogMessage(`Error stopping process: ${error.message}`);
        });
    });
    
    // Check the status of the voting process
    function checkStatus() {
        fetch('/check_status')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'error') {
                // Handle no active session or other errors
                clearInterval(statusCheckInterval);
                startBtn.disabled = false;
                stopBtn.disabled = true;
                return;
            }
            
            // Update progress bar
            const totalVotes = data.total_votes;
            const completedVotes = data.completed_votes;
            const percentage = (completedVotes / totalVotes) * 100;
            
            progressBar.style.width = `${percentage}%`;
            
            // Show batch information if available
            if (data.total_batches) {
                voteStats.textContent = `${completedVotes}/${totalVotes} votes (Batch ${data.current_batch}/${data.total_batches})`;
            } else {
                voteStats.textContent = `${completedVotes}/${totalVotes} votes`;
            }
            
            progressText.textContent = data.current_status;
            
            // Update success/error counts
            successCount.textContent = data.success_count;
            errorCount.textContent = data.error_count;
            
            // Update log with new messages
            const logMessages = data.log_messages;
            
            // Only add new log messages that aren't already displayed
            const currentLogCount = logContainer.children.length;
            if (logMessages.length > currentLogCount) {
                for (let i = currentLogCount; i < logMessages.length; i++) {
                    addLogMessage(logMessages[i]);
                }
            }
            
            // If process is no longer running, allow starting a new session
            if (!data.is_running) {
                clearInterval(statusCheckInterval);
                statusCheckInterval = null;
                startBtn.disabled = false;
                stopBtn.disabled = true;
                addLogMessage('Voting process completed or stopped.');
            }
        })
        .catch(error => {
            addLogMessage(`Error checking status: ${error.message}`);
        });
    }
});
