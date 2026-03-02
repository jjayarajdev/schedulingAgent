// API Service for VAPI Dashboard
// Configure API_BASE_URL based on environment

const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://your-api-id.execute-api.us-east-1.amazonaws.com';

class ApiService {
  constructor() {
    this.baseUrl = API_BASE_URL;
    this.token = localStorage.getItem('token');
  }

  setToken(token) {
    this.token = token;
    if (token) {
      localStorage.setItem('token', token);
    } else {
      localStorage.removeItem('token');
    }
  }

  getToken() {
    return this.token || localStorage.getItem('token');
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.getToken()) {
      headers['Authorization'] = `Bearer ${this.getToken()}`;
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Request failed');
      }

      return data;
    } catch (error) {
      console.error('API Error:', error);
      throw error;
    }
  }

  // Auth endpoints
  async login(username, password, tenantId = '') {
    const data = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password, tenant_id: tenantId }),
    });

    if (data.token) {
      this.setToken(data.token);
    }

    return data;
  }

  async verifyToken() {
    return this.request('/auth/verify');
  }

  async logout() {
    const result = await this.request('/auth/logout', { method: 'POST' });
    this.setToken(null);
    return result;
  }

  // API endpoints
  async getCalls(params = {}, phoneNumberId = null) {
    if (phoneNumberId) {
      params.phoneNumberId = phoneNumberId;
    }
    const queryString = new URLSearchParams(params).toString();
    const endpoint = queryString ? `/api/calls?${queryString}` : '/api/calls';
    return this.request(endpoint);
  }

  async getCall(callId) {
    return this.request(`/api/call/${callId}`);
  }

  async getStats(days = 30, phoneNumberId = null) {
    let url = `/api/stats?days=${days}`;
    if (phoneNumberId) url += `&phoneNumberId=${phoneNumberId}`;
    return this.request(url);
  }

  async getCosts(days = 30, phoneNumberId = null) {
    let url = `/api/costs?days=${days}`;
    if (phoneNumberId) url += `&phoneNumberId=${phoneNumberId}`;
    return this.request(url);
  }

  async getPhoneNumbers() {
    return this.request('/api/phone-numbers');
  }

  async getCallsByDate(date, phoneNumberId = null) {
    // date should be YYYY-MM-DD format
    const startDate = `${date}T00:00:00Z`;
    const endDate = `${date}T23:59:59Z`;
    let url = `/api/calls?start_date=${startDate}&end_date=${endDate}&limit=100`;
    if (phoneNumberId) url += `&phoneNumberId=${phoneNumberId}`;
    return this.request(url);
  }

  async getTenants() {
    return this.request('/api/tenants');
  }

  // Reports endpoints
  async getReports(limit = 30) {
    return this.request(`/api/reports?limit=${limit}`);
  }

  async getReport(date) {
    return this.request(`/api/reports?date=${date}`);
  }
}

export const api = new ApiService();

// Named exports for convenience
export const getReports = (limit) => api.getReports(limit);
export const getReport = (date) => api.getReport(date);

export default api;
