import api from './api';

export const reminderService = {
  // Create reminder
  createReminder: async (data) => {
    const response = await api.post('/reminders/create', data);
    return response.data;
  },

  // Get all reminders
  getReminders: async (active_only = true) => {
    const response = await api.get('/reminders/list', { 
      params: { active_only } 
    });
    return response.data;
  },

  // Get reminder by ID
  getReminder: async (reminderId) => {
    const response = await api.get(`/reminders/${reminderId}`);
    return response.data;
  },

  // Update reminder
  updateReminder: async (reminderId, data) => {
    const response = await api.patch(`/reminders/${reminderId}`, data);
    return response.data;
  },

  // Toggle reminder status
  toggleReminder: async (reminderId, is_active) => {
    const response = await api.patch(`/reminders/${reminderId}/toggle`, { is_active });
    return response.data;
  },

  // Delete reminder
  deleteReminder: async (reminderId) => {
    const response = await api.delete(`/reminders/${reminderId}`);
    return response.data;
  },

  // Trigger reminder now
  triggerNow: async (reminderId) => {
    const response = await api.post(`/reminders/${reminderId}/trigger`);
    return response.data;
  },
};