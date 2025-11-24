/**
 * ProjectForce API Integration
 * Simplified - All API calls go through the Flask backend to avoid CORS issues
 */

// Get token from localStorage
function getPFToken() {
    return localStorage.getItem('pf_access_token');
}

function getPFClientId() {
    return localStorage.getItem('pf_client_id') || '09PF05VD';
}

function getPFUserId() {
    return localStorage.getItem('pf_user_id') || '1645869';
}

/**
 * ProjectForce API Integration
 * All calls go through Flask backend which proxies to real API
 */
const ProjectForceAPI = {
    /**
     * Test API connectivity by sending a simple test message to the backend
     * The backend will invoke the Bedrock agent which will call ProjectForce API
     */
    async testConnection() {
        const token = getPFToken();
        const clientId = getPFClientId();
        const userId = getPFUserId();

        if (!token) {
            return {
                success: false,
                message: 'No token available. Please get a token first.'
            };
        }

        try {
            // Get BACKEND_URL from window or use default
            const backendUrl = window.BACKEND_URL || 'http://localhost:5001';

            // Send a simple test query through the backend
            const response = await fetch(`${backendUrl}/api/classify`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: 'List my projects',
                    pf_token: token,
                    pf_client_id: clientId,
                    pf_user_id: userId
                })
            });

            if (!response.ok) {
                throw new Error(`Backend error: ${response.status}`);
            }

            const result = await response.json();

            // Check if we got a valid response
            if (result.response && result.response.length > 0) {
                return {
                    success: true,
                    message: 'API connection successful',
                    clientName: 'ProjectForce User',
                    clientId: clientId,
                    testResponse: result.response
                };
            } else {
                return {
                    success: false,
                    message: 'Got response but no data. Token might be invalid.'
                };
            }

        } catch (error) {
            return {
                success: false,
                message: error.message
            };
        }
    },

    /**
     * Get customer projects (for testing - returns simplified result)
     */
    async getCustomerProjects() {
        // This is just a placeholder for the UI
        // Actual project data comes through the Bedrock agent
        return {
            data: [],
            message: 'Use the chat interface to query projects'
        };
    }
};

// Export for use in test_ui.html
if (typeof window !== 'undefined') {
    window.ProjectForceAPI = ProjectForceAPI;
}
