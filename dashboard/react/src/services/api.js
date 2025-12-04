import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
});

export const fetchHealthStatus = () => {
  return api.get('/health');
};

export const fetchTeamInfo = () => {
  return api.get('/team/info');
};

export const fetchPerformanceHistory = (limit = 50) => {
  return api.get(`/performance/history?limit=${limit}`);
};

export const fetchLatestPredictions = (limit = 50) => {
  return api.get(`/predictions/latest?limit=${limit}`);
};

export const fetchTransferHistory = (limit = 50) => {
  return api.get(`/transfers/history?limit=${limit}`);
};

export const fetchAnalyticsSummary = () => {
  return api.get('/analytics/summary');
};

export const fetchSystemLogs = (lines = 100) => {
  return api.get(`/system/logs?lines=${lines}`);
};

export const triggerBotRun = () => {
  return api.post('/system/run');
};

export const fetchFeatureImportance = () => {
  return api.get('/ml/feature-importance');
};

export default api;