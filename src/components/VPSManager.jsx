import { useState, useEffect } from 'react';
import { Plus, Trash2, Server, Network, Play, Pause } from 'lucide-react';
import { vpsApi } from '../services/api';

function VPSManager() {
  const [portForwards, setPortForwards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [formData, setFormData] = useState({
    publicPort: '',
    targetIP: '',
    targetPort: '',
    protocol: 'tcp',
    description: ''
  });

  useEffect(() => {
    fetchPortForwards();
  }, []);

  const fetchPortForwards = async () => {
    try {
      const response = await vpsApi.getPortForwards();
      setPortForwards(response.data.data || []);
    } catch (error) {
      console.error('Error fetching port forwards:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddPortForward = async (e) => {
    e.preventDefault();
    try {
      await vpsApi.addPortForward(formData);
      setShowAddForm(false);
      setFormData({
        publicPort: '',
        targetIP: '',
        targetPort: '',
        protocol: 'tcp',
        description: ''
      });
      fetchPortForwards();
    } catch (error) {
      console.error('Error adding port forward:', error);
      alert('Error adding port forward: ' + (error.response?.data?.error || error.message));
    }
  };

  const handleRemovePortForward = async (forwardId) => {
    if (!confirm('Are you sure you want to remove this port forward?')) return;
    
    try {
      await vpsApi.removePortForward(forwardId);
      fetchPortForwards();
    } catch (error) {
      console.error('Error removing port forward:', error);
      alert('Error removing port forward: ' + (error.response?.data?.error || error.message));
    }
  };

  const handleTogglePortForward = async (forwardId, currentEnabled) => {
    try {
      await vpsApi.togglePortForward(forwardId, !currentEnabled);
      fetchPortForwards();
    } catch (error) {
      console.error('Error toggling port forward:', error);
      alert('Error toggling port forward: ' + (error.response?.data?.error || error.message));
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  if (loading) {
    return (
      <div className="loading-container">
        <Server className="loading-spinner" size={32} />
        <p>Loading VPS data...</p>
      </div>
    );
  }

  return (
    <div className="vps-manager">
      <div className="vps-header">
        <h2>VPS Port Forwarding Manager</h2>
        <button 
          className="btn btn-primary"
          onClick={() => setShowAddForm(true)}
        >
          <Plus size={16} />
          Add Port Forward
        </button>
      </div>

      {showAddForm && (
        <div className="modal-overlay">
          <div className="modal">
            <div className="modal-header">
              <h3>Add Port Forward</h3>
              <button 
                className="btn-close"
                onClick={() => setShowAddForm(false)}
              >
                ×
              </button>
            </div>
            <form onSubmit={handleAddPortForward} className="port-forward-form">
              <div className="form-grid">
                <div className="form-group">
                  <label htmlFor="publicPort">Public Port</label>
                  <input
                    type="number"
                    id="publicPort"
                    name="publicPort"
                    value={formData.publicPort}
                    onChange={handleInputChange}
                    min="1"
                    max="65535"
                    required
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="targetIP">Target IP</label>
                  <input
                    type="text"
                    id="targetIP"
                    name="targetIP"
                    value={formData.targetIP}
                    onChange={handleInputChange}
                    placeholder="192.168.1.100"
                    required
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="targetPort">Target Port</label>
                  <input
                    type="number"
                    id="targetPort"
                    name="targetPort"
                    value={formData.targetPort}
                    onChange={handleInputChange}
                    min="1"
                    max="65535"
                    required
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="protocol">Protocol</label>
                  <select
                    id="protocol"
                    name="protocol"
                    value={formData.protocol}
                    onChange={handleInputChange}
                  >
                    <option value="tcp">TCP</option>
                    <option value="udp">UDP</option>
                  </select>
                </div>
              </div>
              <div className="form-group">
                <label htmlFor="description">Description</label>
                <input
                  type="text"
                  id="description"
                  name="description"
                  value={formData.description}
                  onChange={handleInputChange}
                  placeholder="Web server, SSH, etc."
                />
              </div>
              <div className="form-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowAddForm(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Add Port Forward
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="port-forwards-list">
        {portForwards.length === 0 ? (
          <div className="empty-state">
            <Network size={48} />
            <h3>No Port Forwards</h3>
            <p>Create your first port forward to start routing traffic</p>
          </div>
        ) : (
          <div className="port-forwards-grid">
            {portForwards.map((forward) => (
              <div key={forward.id} className="port-forward-card">
                <div className="card-header">
                  <div className="card-title">
                    <Network size={20} />
                    <span>Port {forward.publicPort}</span>
                  </div>
                  <div className="card-actions">
                    <button
                      className={`btn-icon ${forward.enabled ? 'active' : 'inactive'}`}
                      onClick={() => handleTogglePortForward(forward.id, forward.enabled)}
                      title={forward.enabled ? 'Disable' : 'Enable'}
                    >
                      {forward.enabled ? <Pause size={16} /> : <Play size={16} />}
                    </button>
                    <button
                      className="btn-icon danger"
                      onClick={() => handleRemovePortForward(forward.id)}
                      title="Remove"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
                <div className="card-content">
                  <div className="forward-details">
                    <div className="detail-row">
                      <span className="detail-label">Target:</span>
                      <span className="detail-value">{forward.targetIP}:{forward.targetPort}</span>
                    </div>
                    <div className="detail-row">
                      <span className="detail-label">Protocol:</span>
                      <span className="detail-value protocol">{forward.protocol?.toUpperCase()}</span>
                    </div>
                    {forward.description && (
                      <div className="detail-row">
                        <span className="detail-label">Description:</span>
                        <span className="detail-value">{forward.description}</span>
                      </div>
                    )}
                  </div>
                  <div className={`status-badge ${forward.enabled ? 'active' : 'inactive'}`}>
                    {forward.enabled ? 'Active' : 'Inactive'}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default VPSManager;