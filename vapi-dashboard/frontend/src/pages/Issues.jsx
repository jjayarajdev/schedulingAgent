import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, TrendingDown, Clock, XCircle, ChevronRight, AlertCircle, FileQuestion } from 'lucide-react';
import { usePhone } from '../context/PhoneContext';
import api from '../services/api';

function Issues() {
  const [calls, setCalls] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [issueType, setIssueType] = useState('all');
  const navigate = useNavigate();
  const { selectedPhoneId } = usePhone();

  useEffect(() => {
    if (selectedPhoneId) {
      fetchCalls();
    }
  }, [selectedPhoneId]);

  const fetchCalls = async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await api.getCalls({ limit: 100 }, selectedPhoneId);
      setCalls(data.calls || []);
    } catch (err) {
      setError(err.message || 'Failed to load call data');
    } finally {
      setLoading(false);
    }
  };

  // Analyze calls for issues
  const analyzeIssues = () => {
    const issues = {
      failed: [],
      short: [],
      expensive: [],
      hangup: [],
      noSummary: []
    };

    // Filter out calls with no duration (incomplete calls)
    const completedCalls = calls.filter(c => c.duration_seconds > 0);

    // Calculate averages for comparison (only from completed calls)
    const avgDuration = completedCalls.length > 0
      ? completedCalls.reduce((sum, c) => sum + (c.duration_seconds || 0), 0) / completedCalls.length
      : 60;
    const avgCost = completedCalls.length > 0
      ? completedCalls.reduce((sum, c) => sum + (c.cost || 0), 0) / completedCalls.length
      : 0.5;

    calls.forEach(call => {
      // Failed calls
      if (call.success_evaluation === 'false' || call.success_evaluation === false) {
        issues.failed.push({ ...call, issueReason: 'Call marked as failed' });
      }

      // Very short calls (under 30 seconds) - might indicate issues
      // Only flag if call actually started (duration > 0)
      if (call.duration_seconds > 0 && call.duration_seconds < 30) {
        issues.short.push({ ...call, issueReason: `Only ${Math.round(call.duration_seconds)}s duration` });
      }

      // Expensive calls (2x average, minimum $0.50 threshold)
      if (call.cost && call.cost > Math.max(avgCost * 2, 0.50)) {
        issues.expensive.push({ ...call, issueReason: `Cost $${call.cost.toFixed(2)} (${Math.round((call.cost / avgCost) * 100)}% of avg)` });
      }

      // Customer hung up
      if (call.ended_reason?.includes('customer') && call.ended_reason?.includes('ended')) {
        issues.hangup.push({ ...call, issueReason: call.ended_reason?.replace(/-/g, ' ') });
      }

      // No summary - indicates potential transcription/analysis issue
      // Only flag if call had reasonable duration but no summary
      if (call.duration_seconds > 10 && (!call.summary || call.summary.trim() === '')) {
        issues.noSummary.push({ ...call, issueReason: 'No call summary available' });
      }
    });

    return issues;
  };

  const formatDuration = (seconds) => {
    if (!seconds) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
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

  const issues = analyzeIssues();

  const issueCategories = [
    { key: 'all', label: 'All Issues', icon: AlertTriangle, color: 'gray' },
    { key: 'failed', label: 'Failed Calls', icon: XCircle, color: 'red', count: issues.failed.length },
    { key: 'short', label: 'Very Short', icon: Clock, color: 'yellow', count: issues.short.length },
    { key: 'expensive', label: 'High Cost', icon: TrendingDown, color: 'purple', count: issues.expensive.length },
    { key: 'hangup', label: 'Customer Hangup', icon: AlertCircle, color: 'orange', count: issues.hangup.length },
    { key: 'noSummary', label: 'No Summary', icon: FileQuestion, color: 'blue', count: issues.noSummary.length },
  ];

  // Get filtered issues
  const getFilteredIssues = () => {
    if (issueType === 'all') {
      // Combine all unique issues
      const allIssues = new Map();
      Object.values(issues).flat().forEach(issue => {
        if (!allIssues.has(issue.id)) {
          allIssues.set(issue.id, issue);
        }
      });
      return Array.from(allIssues.values()).sort((a, b) =>
        new Date(b.created_at) - new Date(a.created_at)
      );
    }
    return issues[issueType] || [];
  };

  const filteredIssues = getFilteredIssues();
  const totalIssueCount = new Set(Object.values(issues).flat().map(i => i.id)).size;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Issues & Improvements</h1>
        <p className="text-gray-500">Calls that may need attention or indicate problems</p>
      </div>

      {/* Issue Stats */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {issueCategories.map(({ key, label, icon: Icon, color, count }) => {
          const colorClasses = {
            gray: 'bg-gray-50 text-gray-600 border-gray-200',
            red: 'bg-red-50 text-red-600 border-red-200',
            yellow: 'bg-yellow-50 text-yellow-600 border-yellow-200',
            purple: 'bg-purple-50 text-purple-600 border-purple-200',
            orange: 'bg-orange-50 text-orange-600 border-orange-200',
            blue: 'bg-blue-50 text-blue-600 border-blue-200',
          };

          const displayCount = key === 'all' ? totalIssueCount : count;

          return (
            <button
              key={key}
              onClick={() => setIssueType(key)}
              className={`p-4 rounded-xl border-2 transition-all ${
                issueType === key
                  ? `${colorClasses[color]} border-current`
                  : 'bg-white border-gray-200 hover:border-gray-300'
              }`}
            >
              <Icon className={`w-6 h-6 mx-auto mb-2 ${issueType === key ? '' : 'text-gray-400'}`} />
              <p className={`text-2xl font-bold ${issueType === key ? '' : 'text-gray-900'}`}>
                {displayCount}
              </p>
              <p className={`text-xs ${issueType === key ? '' : 'text-gray-500'}`}>{label}</p>
            </button>
          );
        })}
      </div>

      {/* Issue Insights */}
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
        <div className="flex items-start">
          <AlertTriangle className="w-5 h-5 text-amber-600 mr-3 mt-0.5" />
          <div>
            <h4 className="font-medium text-amber-800">Quick Insights</h4>
            <ul className="mt-2 text-sm text-amber-700 space-y-1">
              {issues.failed.length > 0 && (
                <li>• {issues.failed.length} calls were marked as failed - review transcripts for common issues</li>
              )}
              {issues.short.length > 0 && (
                <li>• {issues.short.length} calls under 30s - may indicate caller confusion or technical issues</li>
              )}
              {issues.expensive.length > 0 && (
                <li>• {issues.expensive.length} calls cost significantly more than average - check for long silences or loops</li>
              )}
              {issues.hangup.length > 0 && (
                <li>• {issues.hangup.length} customers hung up - consider improving conversation flow</li>
              )}
              {totalIssueCount === 0 && (
                <li>• No issues detected in recent calls - great job!</li>
              )}
            </ul>
          </div>
        </div>
      </div>

      {/* Issues Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="font-semibold text-gray-900">
            {issueCategories.find(c => c.key === issueType)?.label} ({filteredIssues.length})
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr className="text-left text-sm text-gray-500">
                <th className="px-6 py-3 font-medium">Time</th>
                <th className="px-6 py-3 font-medium">Duration</th>
                <th className="px-6 py-3 font-medium">Cost</th>
                <th className="px-6 py-3 font-medium">Issue</th>
                <th className="px-6 py-3 font-medium">Summary</th>
                <th className="px-6 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filteredIssues.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-gray-500">
                    <AlertTriangle className="w-8 h-8 mx-auto mb-2 text-gray-400" />
                    No issues found in this category
                  </td>
                </tr>
              ) : (
                filteredIssues.map((call) => (
                  <tr
                    key={call.id}
                    className="hover:bg-gray-50 cursor-pointer transition-colors"
                    onClick={() => navigate(`/calls/${call.id}`)}
                  >
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatDate(call.created_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      {formatDuration(call.duration_seconds)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      ${call.cost?.toFixed(2) || '0.00'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                        {call.issueReason}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600 max-w-xs truncate">
                      {call.summary || '-'}
                    </td>
                    <td className="px-6 py-4">
                      <ChevronRight className="w-5 h-5 text-gray-400" />
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Recommendations */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Improvement Recommendations</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 bg-blue-50 rounded-lg">
            <h4 className="font-medium text-blue-900 mb-2">Reduce Failed Calls</h4>
            <ul className="text-sm text-blue-700 space-y-1">
              <li>• Review failed call transcripts for patterns</li>
              <li>• Update AI prompts to handle edge cases</li>
              <li>• Add fallback responses for confusion</li>
            </ul>
          </div>
          <div className="p-4 bg-green-50 rounded-lg">
            <h4 className="font-medium text-green-900 mb-2">Improve Call Duration</h4>
            <ul className="text-sm text-green-700 space-y-1">
              <li>• Very short calls may need better greetings</li>
              <li>• Long calls might have unnecessary loops</li>
              <li>• Aim for efficient, helpful conversations</li>
            </ul>
          </div>
          <div className="p-4 bg-purple-50 rounded-lg">
            <h4 className="font-medium text-purple-900 mb-2">Reduce Costs</h4>
            <ul className="text-sm text-purple-700 space-y-1">
              <li>• Minimize AI response verbosity</li>
              <li>• Reduce wait times between turns</li>
              <li>• Optimize tool call efficiency</li>
            </ul>
          </div>
          <div className="p-4 bg-yellow-50 rounded-lg">
            <h4 className="font-medium text-yellow-900 mb-2">Customer Retention</h4>
            <ul className="text-sm text-yellow-700 space-y-1">
              <li>• Analyze why customers hang up</li>
              <li>• Improve first impression and greeting</li>
              <li>• Make key info available quickly</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Issues;
