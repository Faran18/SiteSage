import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Search } from 'lucide-react';
import toast from 'react-hot-toast';
import { agentService } from '../services/agentService';
import AgentList from '../components/agents/AgentList';
import CreateAgentModal from '../components/agents/CreateAgentModal';
import UpdateAgentModal from '../components/agents/UpdateAgentModal';

export default function MyAgents() {
  const navigate = useNavigate();
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [updateModalOpen, setUpdateModalOpen] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState(null);

  useEffect(() => {
    fetchAgents();
  }, [filterStatus]);

  const fetchAgents = async () => {
    try {
      setLoading(true);
      const status = filterStatus === 'all' ? null : filterStatus;
      const response = await agentService.getAgents(status);
      setAgents(response.agents || []);
    } catch (error) {
      toast.error('Failed to fetch agents');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateAgent = async (name, role) => {
    try {
      const result = await agentService.createAgent(name, role);
      toast.success('Agent created successfully!');
      setCreateModalOpen(false);

      // Go straight to the new agent instead of dropping back into the
      // list - with duplicate names/roles it's too easy to click the
      // wrong row and end up scraping one agent while chatting with
      // another (identical-looking) one.
      navigate(`/agents/${result.agent.agent_id}/chat`);
    } catch (error) {
      toast.error('Failed to create agent');
      console.error(error);
    }
  };

  const handleUpdateAgent = async (agentId, data) => {
    try {
      await agentService.updateAgent(agentId, data);
      toast.success('Agent updated successfully!');
      setUpdateModalOpen(false);
      fetchAgents();
    } catch (error) {
      toast.error('Failed to update agent');
      console.error(error);
    }
  };

  const handleDeleteAgent = async (agentId) => {
    if (!window.confirm('Are you sure you want to delete this agent? This will also delete all its data.')) {
      return;
    }

    try {
      await agentService.deleteAgent(agentId);
      toast.success('Agent deleted successfully');
      fetchAgents();
    } catch (error) {
      toast.error('Failed to delete agent');
      console.error(error);
    }
  };

  const handleToggleStatus = async (agentId, currentStatus) => {
    const newStatus = currentStatus === 'active' ? 'inactive' : 'active';
    
    try {
      await agentService.updateAgentStatus(agentId, newStatus);
      toast.success(`Agent ${newStatus === 'active' ? 'activated' : 'deactivated'}`);
      fetchAgents();
    } catch (error) {
      toast.error('Failed to update status');
      console.error(error);
    }
  };

  const filteredAgents = agents.filter(agent =>
    agent.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    agent.role.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">My Agents</h1>
          <p className="text-gray-600 mt-1">
            Manage your AI agents and their knowledge bases
          </p>
        </div>
        <button
          onClick={() => setCreateModalOpen(true)}
          className="px-6 py-3 bg-gradient-to-r from-primary-500 to-secondary-500 text-white rounded-xl font-semibold hover:shadow-lg transition-all duration-300 flex items-center space-x-2"
        >
          <Plus className="w-5 h-5" />
          <span>Create Agent</span>
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white p-4 rounded-xl shadow-sm space-y-4">
        <div className="flex flex-col md:flex-row gap-4">
          {/* Search */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search agents..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>

          {/* Status Filter */}
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          >
            <option value="all">All Status</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </div>
      </div>

      {/* Agents List */}
      <AgentList
        agents={filteredAgents}
        loading={loading}
        onDelete={handleDeleteAgent}
        onToggleStatus={handleToggleStatus}
        onUpdate={(agent) => {
          setSelectedAgent(agent);
          setUpdateModalOpen(true);
        }}
      />

      {/* Modals */}
      <CreateAgentModal
        isOpen={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        onSubmit={handleCreateAgent}
      />

      {selectedAgent && (
        <UpdateAgentModal
          isOpen={updateModalOpen}
          onClose={() => {
            setUpdateModalOpen(false);
            setSelectedAgent(null);
          }}
          agent={selectedAgent}
          onSubmit={handleUpdateAgent}
        />
      )}
    </div>
  );
}