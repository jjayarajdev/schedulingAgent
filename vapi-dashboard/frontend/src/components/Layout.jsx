import { Outlet } from 'react-router-dom';
import { Phone } from 'lucide-react';
import Sidebar from './Sidebar';
import { useAuth } from '../context/AuthContext';
import { usePhone } from '../context/PhoneContext';

function Layout() {
  const { user, tenant } = useAuth();
  const { phoneNumbers, selectedPhone, selectPhone, loading: phoneLoading } = usePhone();

  return (
    <div className="min-h-screen bg-gray-100">
      <Sidebar />

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Top bar */}
        <header className="bg-white shadow-sm border-b border-gray-200">
          <div className="px-4 sm:px-6 lg:px-8 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <h2 className="text-lg font-semibold text-gray-800">
                  {tenant?.name || 'VAPI Dashboard'}
                </h2>
                {/* Global Phone Filter */}
                {!phoneLoading && phoneNumbers.length > 0 && (
                  <div className="flex items-center gap-2">
                    <Phone className="w-4 h-4 text-gray-400" />
                    <select
                      value={selectedPhone?.id || ''}
                      onChange={(e) => selectPhone(e.target.value)}
                      className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 bg-white"
                    >
                      {phoneNumbers.map((phone) => (
                        <option key={phone.id} value={phone.id}>
                          {phone.name} ({phone.number})
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>
              <div className="flex items-center space-x-4">
                <span className="text-sm text-gray-600">
                  {user?.name || user?.username}
                </span>
                {user?.role === 'admin' && (
                  <span className="px-2 py-1 text-xs bg-purple-100 text-purple-700 rounded-full">
                    Admin
                  </span>
                )}
              </div>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="p-4 sm:p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default Layout;
