const API_BASE = 'http://localhost:8000/api';

async function fetchJson(url, options = {}) {
  const res = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || 'Request failed');
  }
  return res.json();
}

// Health
export const checkHealth = () => fetchJson('/health');

// Payments
export const getPayments = (params = {}) => {
  const qs = new URLSearchParams(params).toString();
  return fetchJson(`/payments?${qs}`);
};
export const getPayment = (uetr) => fetchJson(`/payments/${uetr}`);
export const searchPayments = (q) => fetchJson(`/payments/search?q=${encodeURIComponent(q)}`);
export const createPayment = (data) =>
  fetchJson('/payments', { method: 'POST', body: JSON.stringify(data) });
export const updatePaymentStatus = (uetr, data) =>
  fetchJson(`/payments/${uetr}/status`, { method: 'PUT', body: JSON.stringify(data) });
export const tracePayment = (uetr) => fetchJson(`/payments/${uetr}/trace`);
export const getPaymentTypes = () => fetchJson('/payments/types');

// Initiations
export const getInitiations = (params = {}) => {
  const qs = new URLSearchParams(params).toString();
  return fetchJson(`/initiations?${qs}`);
};
export const createInitiation = (data) =>
  fetchJson('/initiations', { method: 'POST', body: JSON.stringify(data) });

// Statements
export const getStatements = (params = {}) => {
  const qs = new URLSearchParams(params).toString();
  return fetchJson(`/statements?${qs}`);
};
export const getStatement = (id) => fetchJson(`/statements/${id}`);

// Investigations
export const getInvestigations = (params = {}) => {
  const qs = new URLSearchParams(params).toString();
  return fetchJson(`/investigations?${qs}`);
};
export const getInvestigation = (caseId) => fetchJson(`/investigations/${caseId}`);
export const createInvestigation = (data) =>
  fetchJson('/investigations', { method: 'POST', body: JSON.stringify(data) });
export const resolveInvestigation = (caseId, data) =>
  fetchJson(`/investigations/${caseId}/resolve`, { method: 'PUT', body: JSON.stringify(data) });

// Mandates
export const getMandates = (params = {}) => {
  const qs = new URLSearchParams(params).toString();
  return fetchJson(`/mandates?${qs}`);
};

// Analytics
export const getDashboard = () => fetchJson('/analytics/dashboard');
export const getTopCorridors = () => fetchJson('/analytics/top-corridors');
export const getAgentActivity = () => fetchJson('/analytics/agent-activity');
export const getProcessingTimes = () => fetchJson('/analytics/processing-times');

// Value Props
export const getValuePropsSummary = () => fetchJson('/value-props/summary');
export const getValueProp = (name) => fetchJson(`/value-props/${name}`);

// AI Vector Search
export const getAISearchStatus = () => fetchJson('/ai-search/status');
export const naturalLanguageSearch = (data) =>
  fetchJson('/ai-search/natural-language', { method: 'POST', body: JSON.stringify(data) });
export const findSimilarTransactions = (data) =>
  fetchJson('/ai-search/similar-transactions', { method: 'POST', body: JSON.stringify(data) });
export const remittanceMatch = (data) =>
  fetchJson('/ai-search/remittance-match', { method: 'POST', body: JSON.stringify(data) });
