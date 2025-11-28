// static/app.js

document.addEventListener('DOMContentLoaded', () => {
    const chatHistoryContainer = document.getElementById('chat-history-container');
    const chatForm = document.getElementById('chat-form');

    // 1. Function to load chat history
    async function loadChatHistory() {
        if (!chatHistoryContainer) return;

        try {
            const response = await fetch('/chat/history');
            if (response.ok) {
                const html = await response.text();
                chatHistoryContainer.innerHTML = html;
                // Scroll to the bottom of the chat
                chatHistoryContainer.scrollTop = chatHistoryContainer.scrollHeight;
            } else {
                chatHistoryContainer.innerHTML = '<p class="text-red-500">Failed to load chat history.</p>';
            }
        } catch (error) {
            console.error("Error loading chat history:", error);
            chatHistoryContainer.innerHTML = '<p class="text-red-500">Network error loading chat history.</p>';
        }
    }

    // 2. Function to handle chat form submission (ask or summarize)
    if (chatForm) {
        chatForm.addEventListener('submit', async (event) => {
            event.preventDefault(); // Stop default form submission

            const formData = new FormData(chatForm);
            const queryInput = document.getElementById('query-input');

            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    body: formData
                });

                if (response.ok) {
                    const htmlFragment = await response.text();
                    
                    // Append the new message fragment to the container
                    chatHistoryContainer.insertAdjacentHTML('beforeend', htmlFragment);
                    
                    // Clear the input field and scroll to bottom
                    if (queryInput) queryInput.value = '';
                    chatHistoryContainer.scrollTop = chatHistoryContainer.scrollHeight;
                    
                } else {
                    const errorHtml = await response.text();
                    // Display error message from the server (handled by main.py exception handler)
                    chatHistoryContainer.insertAdjacentHTML('beforeend', errorHtml);
                }
            } catch (error) {
                console.error("Chat submission error:", error);
                // Simple error message
                chatHistoryContainer.insertAdjacentHTML('beforeend', '<p class="text-xs text-red-500 p-2">An unexpected error occurred.</p>');
            }
        });
    }

    // Load history when the page first loads
    loadChatHistory();
});

// Helper function to render a single report card
function renderReportCard(report) {
    return `
        <div style="border: 1px solid #ccc; margin-bottom: 10px; padding: 10px; border-radius: 6px; background-color: #fff;">
            <strong>${report.title}</strong> 
            <span style="float: right; font-size: 0.8em; color: #777;">${new Date(report.upload_date).toLocaleDateString()}</span>
            <p style="margin: 5px 0 0;">Type: ${report.report_type}</p>
            ${report.description ? `<p style="font-size: 0.9em; color: #555; margin-top: 5px;">${report.description}</p>` : ''}
        </div>
    `;
}

// Function 3. Load Reports List
async function loadReportsList() {
    const reportsListContainer = document.getElementById('reports-list-container');
    if (!reportsListContainer) return;

    reportsListContainer.innerHTML = '<p style="text-align: center; color: #777;">Fetching reports...</p>';

    try {
        const response = await fetch('/reports');
        if (response.ok) {
            const reports = await response.json();
            if (reports.length === 0) {
                reportsListContainer.innerHTML = '<p style="text-align: center; color: #777;">No medical reports found yet.</p>';
                return;
            }
            
            reportsListContainer.innerHTML = reports.map(renderReportCard).join('');

        } else {
            reportsListContainer.innerHTML = '<p style="color: red; text-align: center;">Failed to load reports.</p>';
        }
    } catch (error) {
        console.error("Error loading reports:", error);
        reportsListContainer.innerHTML = '<p style="color: red; text-align: center;">Network error while fetching reports.</p>';
    }
}

// Function 4. Handle Report Submission
const reportForm = document.getElementById('report-form');
if (reportForm) {
    reportForm.addEventListener('submit', async (event) => {
        event.preventDefault();

        const formData = new FormData(reportForm);
        const data = Object.fromEntries(formData.entries());
        const reportMessage = document.getElementById('report-message');
        
        // Remove description if it's empty to match the optional Pydantic field
        if (data.description === "") {
            delete data.description;
        }

        try {
            const response = await fetch('/reports', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            if (response.status === 201) {
                reportMessage.style.color = 'green';
                reportMessage.textContent = 'Report submitted successfully!';
                reportForm.reset(); // Clear form
                loadReportsList(); // Refresh the list
            } else {
                const error = await response.json();
                reportMessage.style.color = 'red';
                reportMessage.textContent = `Submission failed: ${error.detail || 'Unknown error'}`;
            }
        } catch (error) {
            console.error("Report submission error:", error);
            reportMessage.style.color = 'red';
            reportMessage.textContent = 'An unexpected network error occurred.';
        }
    });
}
loadReportsList();