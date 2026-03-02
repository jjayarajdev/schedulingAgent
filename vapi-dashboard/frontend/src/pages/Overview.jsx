import { useState, useEffect } from 'react';
import { Phone, CheckCircle, XCircle, Clock, DollarSign, TrendingUp } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import StatsCard from '../components/StatsCard';
import { usePhone } from '../context/PhoneContext';
import api from '../services/api';

function Overview() {
  const [stats, setStats] = useState(null);
  const [costs, setCosts] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [days, setDays] = useState(7);

  const { selectedPhoneId } = usePhone();

  useEffect(() => {
    if (selectedPhoneId) {
      fetchData();
    }
  }, [days, selectedPhoneId]);

  const fetchData = async () => {
    setLoading(true);
    setError(null);

    try {
      const [statsData, costsData] = await Promise.all([
        api.getStats(days, selectedPhoneId),
        api.getCosts(days, selectedPhoneId)
      ]);

      setStats(statsData.stats);
      setCosts(costsData.costs);
    } catch (err) {
      setError(err.message || 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
        {error}
      </div>
    );
  }

  // Prepare chart data
  const dailyData = stats?.daily_counts
    ? Object.entries(stats.daily_counts)
        .map(([date, count]) => ({ date, calls: count }))
        .sort((a, b) => a.date.localeCompare(b.date))
    : [];

  const endReasonData = stats?.end_reasons
    ? Object.entries(stats.end_reasons).map(([name, value]) => ({
        name: name.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
        value
      }))
    : [];

  const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return `${mins}m ${secs}s`;
  };

  const formatCurrency = (amount) => {
    return `$${amount.toFixed(2)}`;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Overview</h1>
          <p className="text-gray-500">Call analytics at a glance</p>
        </div>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
        >
          <option value={7}>Last 7 days</option>
          <option value={14}>Last 14 days</option>
        </select>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatsCard
          title="Total Calls"
          value={stats?.total_calls || 0}
          icon={Phone}
          color="blue"
        />
        <StatsCard
          title="Success Rate"
          value={`${stats?.success_rate || 0}%`}
          subtitle={`${stats?.successful_calls || 0} successful`}
          icon={CheckCircle}
          color="green"
        />
        <StatsCard
          title="Avg Duration"
          value={formatDuration(stats?.avg_duration_seconds || 0)}
          icon={Clock}
          color="yellow"
        />
        <StatsCard
          title="Total Cost"
          value={formatCurrency(costs?.total || 0)}
          subtitle={`${formatCurrency(costs?.avg_per_call || 0)} per call`}
          icon={DollarSign}
          color="purple"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Calls Over Time */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Calls Over Time</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={dailyData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 12 }}
                  tickFormatter={(date) => new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip
                  labelFormatter={(date) => new Date(date).toLocaleDateString()}
                  formatter={(value) => [value, 'Calls']}
                />
                <Line
                  type="monotone"
                  dataKey="calls"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* End Reasons */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Call End Reasons</h3>
          <div className="h-64 flex items-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={endReasonData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {endReasonData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
            <div className="space-y-2">
              {endReasonData.map((item, index) => (
                <div key={item.name} className="flex items-center text-sm">
                  <div
                    className="w-3 h-3 rounded-full mr-2"
                    style={{ backgroundColor: COLORS[index % COLORS.length] }}
                  />
                  <span className="text-gray-600">{item.name}</span>
                  <span className="ml-2 font-medium text-gray-900">{item.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Quick Stats Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Summary</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-500">Successful Calls</p>
            <p className="text-xl font-bold text-green-600">{stats?.successful_calls || 0}</p>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-500">Failed Calls</p>
            <p className="text-xl font-bold text-red-600">{stats?.failed_calls || 0}</p>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-500">Total Duration</p>
            <p className="text-xl font-bold text-gray-900">{formatDuration(stats?.total_duration_seconds || 0)}</p>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-500">Avg Cost/Call</p>
            <p className="text-xl font-bold text-purple-600">{formatCurrency(costs?.avg_per_call || 0)}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Overview;
