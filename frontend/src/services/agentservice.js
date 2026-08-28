import api from './api';

export const agentService = {
  // Create new agent
  createAgent: async (name, role) => {
    const response = await api.post('/agents/create', { name, role });
    return response.data;
  },

  // Get all agents
  getAgents: async (status = null) => {
    const params = status ? { status } : {};
    const response = await api.get('/agents/list', { params });
    return response.data;
  },

  // Get agent by ID
  getAgent: async (agentId) => {
    const response = await api.get(`/agents/${agentId}`);
    return response.data;
  },

  // Update agent
  updateAgent: async (agentId, data) => {
    const response = await api.patch(`/agents/${agentId}`, data);
    return response.data;
  },

  // Update agent status
  updateAgentStatus: async (agentId, status) => {
    const response = await api.patch(`/agents/${agentId}/status`, { status });
    return response.data;
  },

  // Delete agent
  deleteAgent: async (agentId) => {
    const response = await api.delete(`/agents/${agentId}`);
    return response.data;
  },

  // Scrape URL for agent
  scrapeUrl: async (agentId, url, options = {}) => {
    const response = await api.post('/scrape', {
      agent_id: agentId,
      url,
      ...options
    });
    return response.data;
  },

  // Refresh agent data
  refreshAgent: async (agentId) => {
    const response = await api.post(`/scrape/refresh/${agentId}`);
    return response.data;
  },

  // Chat with agent
  chat: async (agentId, query) => {
    const response = await api.post('/process', {
      agent_id: agentId,
      query
    });
    return response.data;
  },

  // Start a fresh conversation (clears stored history for this agent)
  resetChat: async (agentId) => {
    const response = await api.post(`/agents/${agentId}/chat/reset`);
    return response.data;
  },
};