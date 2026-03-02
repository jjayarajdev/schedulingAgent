import { createContext, useContext, useState, useEffect } from 'react';
import api from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [tenant, setTenant] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check for existing token on mount
    const token = localStorage.getItem('token');
    if (token) {
      verifyToken();
    } else {
      setLoading(false);
    }
  }, []);

  const verifyToken = async () => {
    try {
      const data = await api.verifyToken();
      if (data.valid) {
        setUser(data.user);
        // Restore tenant from localStorage
        const savedTenant = localStorage.getItem('tenant');
        if (savedTenant) {
          setTenant(JSON.parse(savedTenant));
        }
      } else {
        logout();
      }
    } catch (error) {
      console.error('Token verification failed:', error);
      logout();
    } finally {
      setLoading(false);
    }
  };

  const login = async (username, password, tenantId = '') => {
    const data = await api.login(username, password, tenantId);

    if (data.token) {
      setUser(data.user);
      setTenant(data.tenant);

      if (data.tenant) {
        localStorage.setItem('tenant', JSON.stringify(data.tenant));
      }

      return data;
    }

    throw new Error('Login failed');
  };

  const logout = () => {
    api.setToken(null);
    setUser(null);
    setTenant(null);
    localStorage.removeItem('token');
    localStorage.removeItem('tenant');
  };

  const value = {
    user,
    tenant,
    loading,
    login,
    logout,
    isAuthenticated: !!user,
    isAdmin: user?.role === 'admin',
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}

export default AuthContext;
