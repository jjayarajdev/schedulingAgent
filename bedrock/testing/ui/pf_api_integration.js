/**
 * ProjectForce API Integration
 * Uses the regenerated token from localStorage to call real ProjectForce APIs
 */

const PF_API_BASE = 'https://api-cx-portal.dev.projectsforce.com';

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
 * ProjectForce API calls that match the scheduling agent needs
 */
const ProjectForceAPI = {
    /**
     * Get all projects for a customer
     */
    async getCustomerProjects(customerId = '1645869') {
        const token = getPFToken();
        const clientId = getPFClientId();

        if (!token) {
            throw new Error('No token available. Please get/regenerate token first.');
        }

        const response = await fetch(`${PF_API_BASE}/cx-scheduled/projects?customer_id=${customerId}`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.status} ${response.statusText}`);
        }

        return await response.json();
    },

    /**
     * Get client details/configuration
     */
    async getClientDetails() {
        const token = getPFToken();

        const response = await fetch(`${PF_API_BASE}/system/client-details`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        return await response.json();
    },

    /**
     * Get all stores
     */
    async getStores() {
        const token = getPFToken();

        const response = await fetch(`${PF_API_BASE}/stores/all-stores`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        return await response.json();
    },

    /**
     * Get project categories
     */
    async getProjectCategories() {
        const token = getPFToken();

        const response = await fetch(`${PF_API_BASE}/projects/master/project-category`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        return await response.json();
    },

    /**
     * Get project types
     */
    async getProjectTypes() {
        const token = getPFToken();

        const response = await fetch(`${PF_API_BASE}/projects/master/project-type`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        return await response.json();
    },

    /**
     * Get project status list
     */
    async getProjectStatuses() {
        const token = getPFToken();

        const response = await fetch(`${PF_API_BASE}/system/status`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        return await response.json();
    },

    /**
     * Get customers list
     */
    async getCustomers() {
        const token = getPFToken();

        const response = await fetch(`${PF_API_BASE}/customers`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        return await response.json();
    },

    /**
     * Get user profile
     */
    async getUserProfile() {
        const token = getPFToken();

        const response = await fetch(`${PF_API_BASE}/auth/user/profile`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        return await response.json();
    },

    /**
     * Test API connectivity - calls client details as a health check
     */
    async testConnection() {
        try {
            const result = await this.getClientDetails();
            return {
                success: true,
                message: 'API connection successful',
                clientName: result.client_name,
                clientId: result.client_id
            };
        } catch (error) {
            return {
                success: false,
                message: error.message
            };
        }
    }
};

// Export for use in test_ui.html
if (typeof window !== 'undefined') {
    window.ProjectForceAPI = ProjectForceAPI;
}
