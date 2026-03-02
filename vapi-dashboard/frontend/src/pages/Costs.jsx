import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { DollarSign, TrendingUp, CreditCard, PieChart as PieChartIcon, X, Phone, Clock, CheckCircle, XCircle, ChevronRight } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LabelList } from 'recharts';
import StatsCard from '../components/StatsCard';
import { usePhone } from '../context/PhoneContext';
import api from '../services/api';

function Costs() {
  const [costs, setCosts] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [days, setDays] = useState(7);

  // Global phone filter from context
  const { selectedPhoneId } = usePhone();

  // Drill-down modal state
  const [selectedDate, setSelectedDate] = useState(null);
  const [dayCalls, setDayCalls] = useState([]);
  const [dayCallsLoading, setDayCallsLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);

  const navigate = useNavigate();

  useEffect(() => {
    if (selectedPhoneId) {
      fetchData();
    }
  }, [days, selectedPhoneId]);

  const fetchData = async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await api.getCosts(days, selectedPhoneId);
      setCosts(data.costs);
    } catch (err) {
      setError(err.message || 'Failed to load cost data');
    } finally {
      setLoading(false);
    }
  };

  // Handle bar click for drill-down
  const handleBarClick = async (data) => {
    if (!data || !data.date) return;

    setSelectedDate(data.date);
    setShowModal(true);
    setDayCallsLoading(true);

    try {
      const result = await api.getCallsByDate(data.date, selectedPhoneId);
      setDayCalls(result.calls || []);
    } catch (err) {
      console.error('Failed to fetch calls for date:', err);
      setDayCalls([]);
    } finally {
      setDayCallsLoading(false);
    }
  };

  const closeModal = () => {
    setShowModal(false);
    setSelectedDate(null);
    setDayCalls([]);
  };

  const formatDuration = (seconds) => {
    if (!seconds) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatTime = (dateStr) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  };

  const formatPhone = (phone) => {
    if (!phone) return '-';
    if (phone.length > 6) {
      return phone.slice(0, -4).replace(/\d/g, '*') + phone.slice(-4);
    }
    return phone;
  };

  const getStatusBadge = (call) => {
    const success = call.success_evaluation;
    if (success === 'true' || success === true) {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
          <CheckCircle className="w-3 h-3 mr-1" />
          Success
        </span>
      );
    } else if (success === 'false' || success === false) {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
          <XCircle className="w-3 h-3 mr-1" />
          Failed
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
        Unknown
      </span>
    );
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

  const formatCurrency = (amount) => `$${amount.toFixed(2)}`;

  // Prepare daily costs data
  const dailyCostData = costs?.daily
    ? Object.entries(costs.daily)
        .map(([date, cost]) => ({ date, cost: parseFloat(cost.toFixed(2)) }))
        .sort((a, b) => a.date.localeCompare(b.date))
    : [];

  // Prepare breakdown data
  const breakdownData = costs?.breakdown
    ? Object.entries(costs.breakdown)
        .filter(([_, value]) => value > 0)
        .map(([name, value]) => ({
          name: name.toUpperCase(),
          value: parseFloat(value.toFixed(2))
        }))
    : [];

  const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

  // Calculate average daily cost
  const avgDailyCost = costs?.total / days || 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Cost Analytics</h1>
          <p className="text-gray-500">Track and analyze your VAPI spending</p>
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
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatsCard
          title="Total Spend"
          value={formatCurrency(costs?.total || 0)}
          subtitle={`Last ${days} days`}
          icon={DollarSign}
          color="purple"
        />
        <StatsCard
          title="Avg Per Call"
          value={formatCurrency(costs?.avg_per_call || 0)}
          subtitle={`${costs?.call_count || 0} calls`}
          icon={CreditCard}
          color="blue"
        />
        <StatsCard
          title="Daily Average"
          value={formatCurrency(avgDailyCost)}
          icon={TrendingUp}
          color="green"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Daily Costs */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Daily Costs
            <span className="text-sm font-normal text-gray-500 ml-2">(click bar to drill down)</span>
          </h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={dailyCostData} margin={{ top: 20, right: 10, left: 10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11 }}
                  tickFormatter={(date) => new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                />
                <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `$${v}`} />
                <Tooltip
                  labelFormatter={(date) => new Date(date).toLocaleDateString()}
                  formatter={(value) => [`$${value.toFixed(2)}`, 'Cost']}
                  cursor={{ fill: 'rgba(139, 92, 246, 0.1)' }}
                />
                <Bar
                  dataKey="cost"
                  fill="#8b5cf6"
                  radius={[4, 4, 0, 0]}
                  cursor="pointer"
                  onClick={(data) => handleBarClick(data)}
                >
                  <LabelList
                    dataKey="cost"
                    position="top"
                    formatter={(v) => `$${v.toFixed(2)}`}
                    style={{ fontSize: 10, fill: '#6b7280' }}
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Cost Breakdown */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Cost Breakdown</h3>
          <div className="h-64 flex items-center">
            <ResponsiveContainer width="60%" height="100%">
              <PieChart>
                <Pie
                  data={breakdownData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={70}
                  paddingAngle={5}
                  dataKey="value"
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  labelLine={false}
                >
                  {breakdownData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => `$${value.toFixed(2)}`} />
              </PieChart>
            </ResponsiveContainer>
            <div className="w-40 space-y-3">
              {breakdownData.map((item, index) => (
                <div key={item.name} className="flex items-center justify-between">
                  <div className="flex items-center">
                    <div
                      className="w-3 h-3 rounded-full mr-2"
                      style={{ backgroundColor: COLORS[index % COLORS.length] }}
                    />
                    <span className="text-sm text-gray-600">{item.name}</span>
                  </div>
                  <span className="text-sm font-medium text-gray-900">
                    ${item.value.toFixed(2)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Detailed Breakdown Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Cost Components</h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-sm text-gray-500 border-b border-gray-200">
                <th className="pb-3 font-medium">Component</th>
                <th className="pb-3 font-medium text-right">Total Cost</th>
                <th className="pb-3 font-medium text-right">% of Total</th>
                <th className="pb-3 font-medium text-right">Avg Per Call</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {breakdownData.map((item) => (
                <tr key={item.name} className="text-sm">
                  <td className="py-3">
                    <div className="flex items-center">
                      <div
                        className="w-2 h-2 rounded-full mr-2"
                        style={{ backgroundColor: COLORS[breakdownData.indexOf(item) % COLORS.length] }}
                      />
                      {item.name}
                    </div>
                  </td>
                  <td className="py-3 text-right font-medium">${item.value.toFixed(2)}</td>
                  <td className="py-3 text-right text-gray-500">
                    {((item.value / costs.total) * 100).toFixed(1)}%
                  </td>
                  <td className="py-3 text-right text-gray-500">
                    ${(item.value / costs.call_count).toFixed(4)}
                  </td>
                </tr>
              ))}
              <tr className="text-sm font-semibold bg-gray-50">
                <td className="py-3">Total</td>
                <td className="py-3 text-right">${costs.total.toFixed(2)}</td>
                <td className="py-3 text-right">100%</td>
                <td className="py-3 text-right">${costs.avg_per_call.toFixed(4)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Drill-Down Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-4xl w-full max-h-[80vh] flex flex-col">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-4 border-b border-gray-200">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">
                  Calls for {selectedDate ? new Date(selectedDate).toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }) : ''}
                </h2>
                <p className="text-sm text-gray-500">
                  {dayCalls.length} call{dayCalls.length !== 1 ? 's' : ''} • Total: ${dayCalls.reduce((sum, c) => sum + (c.cost || 0), 0).toFixed(2)}
                </p>
              </div>
              <button
                onClick={closeModal}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>

            {/* Modal Content */}
            <div className="flex-1 overflow-auto p-4">
              {dayCallsLoading ? (
                <div className="flex items-center justify-center h-32">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
                </div>
              ) : dayCalls.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  No calls found for this date
                </div>
              ) : (
                <div className="space-y-3">
                  {dayCalls.map((call) => (
                    <div
                      key={call.id}
                      className="bg-gray-50 rounded-lg p-4 hover:bg-gray-100 cursor-pointer transition-colors"
                      onClick={() => {
                        closeModal();
                        navigate(`/calls/${call.id}`);
                      }}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-4">
                          <div className="flex-shrink-0">
                            <Phone className="w-5 h-5 text-gray-400" />
                          </div>
                          <div>
                            <div className="flex items-center space-x-2">
                              <span className="font-medium text-gray-900">
                                {formatPhone(call.customer_number)}
                              </span>
                              {getStatusBadge(call)}
                            </div>
                            <div className="flex items-center space-x-3 text-sm text-gray-500 mt-1">
                              <span>{formatTime(call.created_at)}</span>
                              <span className="flex items-center">
                                <Clock className="w-3 h-3 mr-1" />
                                {formatDuration(call.duration_seconds)}
                              </span>
                              <span className="text-primary-600 font-medium">${call.cost?.toFixed(2) || '0.00'}</span>
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center">
                          <span className="text-xs text-gray-400 mr-2 max-w-xs truncate">
                            {call.summary || call.ended_reason?.replace(/-/g, ' ') || '-'}
                          </span>
                          <ChevronRight className="w-5 h-5 text-gray-400" />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-gray-200 bg-gray-50 rounded-b-xl">
              <button
                onClick={closeModal}
                className="w-full px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Costs;
