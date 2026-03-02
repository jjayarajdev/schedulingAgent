import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Phone, Clock, DollarSign, CheckCircle, XCircle, User, Bot, Calendar } from 'lucide-react';
import api from '../services/api';

function CallDetail() {
  const { callId } = useParams();
  const navigate = useNavigate();
  const [call, setCall] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchCall();
  }, [callId]);

  const fetchCall = async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await api.getCall(callId);
      setCall(data.call);
    } catch (err) {
      setError(err.message || 'Failed to load call details');
    } finally {
      setLoading(false);
    }
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
    return date.toLocaleString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      year: 'numeric',
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
      <div className="space-y-4">
        <button
          onClick={() => navigate('/calls')}
          className="flex items-center text-gray-600 hover:text-gray-900"
        >
          <ArrowLeft className="w-5 h-5 mr-2" />
          Back to Calls
        </button>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          {error}
        </div>
      </div>
    );
  }

  if (!call) {
    return (
      <div className="space-y-4">
        <button
          onClick={() => navigate('/calls')}
          className="flex items-center text-gray-600 hover:text-gray-900"
        >
          <ArrowLeft className="w-5 h-5 mr-2" />
          Back to Calls
        </button>
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-gray-700">
          Call not found
        </div>
      </div>
    );
  }

  const success = call.success_evaluation;
  const isSuccess = success === 'true' || success === true;
  const isFailed = success === 'false' || success === false;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <button
            onClick={() => navigate('/calls')}
            className="flex items-center text-gray-600 hover:text-gray-900 mr-4"
          >
            <ArrowLeft className="w-5 h-5 mr-2" />
            Back
          </button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Call Details</h1>
            <p className="text-gray-500 text-sm font-mono">{call.id}</p>
          </div>
        </div>
        <div>
          {isSuccess ? (
            <span className="inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium bg-green-100 text-green-800">
              <CheckCircle className="w-4 h-4 mr-1.5" />
              Successful
            </span>
          ) : isFailed ? (
            <span className="inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium bg-red-100 text-red-800">
              <XCircle className="w-4 h-4 mr-1.5" />
              Failed
            </span>
          ) : (
            <span className="inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium bg-gray-100 text-gray-800">
              Unknown
            </span>
          )}
        </div>
      </div>

      {/* Info Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
          <div className="flex items-center">
            <div className="p-2 bg-blue-50 rounded-lg mr-3">
              <Calendar className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Date & Time</p>
              <p className="font-medium text-gray-900">{formatDate(call.created_at)}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
          <div className="flex items-center">
            <div className="p-2 bg-green-50 rounded-lg mr-3">
              <Clock className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Duration</p>
              <p className="font-medium text-gray-900">{formatDuration(call.duration_seconds)}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
          <div className="flex items-center">
            <div className="p-2 bg-purple-50 rounded-lg mr-3">
              <DollarSign className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Cost</p>
              <p className="font-medium text-gray-900">${call.cost?.toFixed(2) || '0.00'}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
          <div className="flex items-center">
            <div className="p-2 bg-yellow-50 rounded-lg mr-3">
              <Phone className="w-5 h-5 text-yellow-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">End Reason</p>
              <p className="font-medium text-gray-900">{call.ended_reason?.replace(/-/g, ' ') || '-'}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Summary & Analysis */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Summary */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Summary</h3>
          <p className="text-gray-700 leading-relaxed">
            {call.summary || 'No summary available for this call.'}
          </p>
        </div>

        {/* Cost Breakdown */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Cost Breakdown</h3>
          {call.cost_breakdown ? (
            <div className="space-y-3">
              {Object.entries(call.cost_breakdown).map(([key, value]) => (
                <div key={key} className="flex justify-between items-center">
                  <span className="text-gray-600 capitalize">{key.replace(/_/g, ' ')}</span>
                  <span className="font-medium text-gray-900">${value?.toFixed(4) || '0.0000'}</span>
                </div>
              ))}
              <div className="pt-3 border-t border-gray-200 flex justify-between items-center">
                <span className="font-semibold text-gray-900">Total</span>
                <span className="font-bold text-gray-900">${call.cost?.toFixed(2) || '0.00'}</span>
              </div>
            </div>
          ) : (
            <p className="text-gray-500">No cost breakdown available</p>
          )}
        </div>
      </div>

      {/* Transcript */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Transcript</h3>
        {call.transcript && call.transcript.length > 0 ? (
          <div className="space-y-4 max-h-96 overflow-y-auto">
            {call.transcript.map((message, index) => (
              <div
                key={index}
                className={`flex ${message.role === 'assistant' ? 'justify-start' : 'justify-end'}`}
              >
                <div
                  className={`max-w-3xl px-4 py-3 rounded-lg ${
                    message.role === 'assistant'
                      ? 'bg-gray-100 text-gray-800'
                      : 'bg-primary-600 text-white'
                  }`}
                >
                  <div className="flex items-center mb-1">
                    {message.role === 'assistant' ? (
                      <Bot className="w-4 h-4 mr-1" />
                    ) : (
                      <User className="w-4 h-4 mr-1" />
                    )}
                    <span className="text-xs font-medium opacity-75 capitalize">
                      {message.role === 'assistant' ? 'AI' : 'Customer'}
                    </span>
                  </div>
                  <p className="text-sm">{message.message || message.content}</p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500">No transcript available for this call.</p>
        )}
      </div>

      {/* Analysis (if available) */}
      {call.analysis && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">AI Analysis</h3>
          <div className="prose prose-sm max-w-none text-gray-700">
            {typeof call.analysis === 'string' ? (
              <p>{call.analysis}</p>
            ) : (
              <pre className="bg-gray-50 p-4 rounded-lg overflow-x-auto text-sm">
                {JSON.stringify(call.analysis, null, 2)}
              </pre>
            )}
          </div>
        </div>
      )}

      {/* Metadata */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Metadata</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-500">Call ID:</span>
            <span className="ml-2 font-mono text-gray-900">{call.id}</span>
          </div>
          <div>
            <span className="text-gray-500">Phone Number ID:</span>
            <span className="ml-2 font-mono text-gray-900">{call.phone_number_id || '-'}</span>
          </div>
          <div>
            <span className="text-gray-500">Assistant ID:</span>
            <span className="ml-2 font-mono text-gray-900">{call.assistant_id || '-'}</span>
          </div>
          <div>
            <span className="text-gray-500">Type:</span>
            <span className="ml-2 text-gray-900 capitalize">{call.type || '-'}</span>
          </div>
          <div>
            <span className="text-gray-500">Created:</span>
            <span className="ml-2 text-gray-900">{formatDate(call.created_at)}</span>
          </div>
          <div>
            <span className="text-gray-500">Ended:</span>
            <span className="ml-2 text-gray-900">{formatDate(call.ended_at)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default CallDetail;
