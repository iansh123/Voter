// Wait for DOM to load
document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const form = document.getElementById('voting-form');
    const startBtn = document.getElementById('start-btn');
    const stopBtn = document.getElementById('stop-btn');
    const statusCard = document.getElementById('status-card');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    const voteStats = document.getElementById('vote-stats');
    const successCount = document.getElementById('success-count');
    const errorCount = document.getElementById('error-count');
    const logContainer = document.getElementById('log-container');
    const useProxiesCheckbox = document.getElementById('use_proxies');
    const customProxySection = document.getElementById('custom-proxy-section');
    
    // Initialize update interval
    let statusInterval = null;
    
    // Handle proxy checkbox toggle
    if (useProxiesCheckbox) {
        useProxiesCheckbox.addEventListener('change', function() {
            if (this.checked) {
                customProxySection.style.display = 'block';
            } else {
                customProxySection.style.display = 'none';
            }
        });
    }
    
    // Add a log message to the container
    function addLogMessage(message) {
        const logEntry = document.createElement('div');
        logEntry.className = 'log-message';
        logEntry.textContent = message;
        logContainer.appendChild(logEntry);
        
        // Scroll to bottom
        logContainer.scrollTop = logContainer.scrollHeight;
        
        // Limit log entries to prevent browser slowdown
        if (logContainer.children.length > 100) {
            logContainer.removeChild(logContainer.children[0]);
        }
    }
    
    // Clear the log
    function clearLog() {
        while (logContainer.firstChild) {
            logContainer.removeChild(logContainer.firstChild);
        }
    }
    
    // Check the voting status
    function checkStatus() {
        fetch('/check_status')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                // Update progress
                const percent = (data.completed_votes / data.total_votes) * 100;
                progressBar.style.width = `${percent}%`;
                progressText.textContent = data.current_status;
                voteStats.textContent = `${data.completed_votes}/${data.total_votes} votes`;
                
                // Update counts
                successCount.textContent = data.success_count;
                errorCount.textContent = data.error_count;
                
                // Add any new log messages
                if (data.log_messages && data.log_messages.length > 0) {
                    // Get current log messages
                    const currentMessages = Array.from(logContainer.querySelectorAll('.log-message')).map(el => el.textContent);
                    
                    // Add only new messages
                    for (const message of data.log_messages) {
                        if (!currentMessages.includes(message)) {
                            addLogMessage(message);
                        }
                    }
                }
                
                // Check if process is still running
                if (!data.is_running) {
                    clearInterval(statusInterval);
                    startBtn.disabled = false;
                    stopBtn.disabled = true;
                }
            })
            .catch(error => {
                console.error('Error checking status:', error);
            });
    }
    
    // Handle form submission to start voting
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Disable button to prevent multiple submissions
        startBtn.disabled = true;
        stopBtn.disabled = false;
        
        // Clear log
        clearLog();
        
        // Show status card
        statusCard.style.display = 'block';
        
        // Reset progress
        progressBar.style.width = '0%';
        progressText.textContent = 'Starting...';
        voteStats.textContent = '0/0 votes';
        successCount.textContent = '0';
        errorCount.textContent = '0';
        
        // Make API call to start voting
        const formData = new FormData(form);
        
        fetch('/start_voting', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                addLogMessage(`Started voting process: ${data.message}`);
                
                // Start periodic status updates
                statusInterval = setInterval(checkStatus, 1000);
            } else {
                addLogMessage(`Error: ${data.message}`);
                startBtn.disabled = false;
                stopBtn.disabled = true;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            addLogMessage(`Error: ${error.message}`);
            startBtn.disabled = false;
            stopBtn.disabled = true;
        });
    });
    
    // Handle stop button
    stopBtn.addEventListener('click', function() {
        fetch('/stop_voting', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                addLogMessage('Stopping voting process...');
                progressText.textContent = 'Stopping...';
            }
        })
        .catch(error => {
            console.error('Error stopping process:', error);
        });
    });
});