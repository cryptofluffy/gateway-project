import { useState, useEffect } from 'react';
import { Router, Globe, Plus, Trash2, Search, RefreshCw } from 'lucide-react';
import { gatewayApi } from '../services/api';

function GatewayManager() {
  const [activeTab, setActiveTab] = useState('routes');
  const [routes, setRoutes] = useState([]);
  const [dnsRecords, setDnsRecords] = useState([]);
  const [dnsStats, setDnsStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showAddRoute, setShowAddRoute] = useState(false);
  const [showAddDns, setShowAddDns] = useState(false);

  const [routeForm, setRouteForm] = useState({
    path: '',
    targetUrl: '',
    methods: ['GET'],
    loadBalancing: 'round-robin'
  });

  const [dnsForm, setDnsForm] = useState({
    hostname: '',
    ip: '',
    description: ''
  });

  useEffect(() => {
    fetchData();
  }, [activeTab]);

  const fetchData = async () => {
    try {
      if (activeTab === 'routes') {
        const response = await gatewayApi.getRoutes();
        setRoutes(response.data.data || []);
      } else if (activeTab === 'dns') {
        const [recordsResponse, statsResponse] = await Promise.all([
          gatewayApi.getDnsRecords(),
          gatewayApi.getDnsStats()
        ]);
        setDnsRecords(recordsResponse.data.data || []);
        setDnsStats(statsResponse.data.data || {});
      }
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddRoute = async (e) => {
    e.preventDefault();
    try {
      const routeData = {
        path: routeForm.path,
        targets: [{ url: routeForm.targetUrl, healthy: true, weight: 1 }],
        methods: routeForm.methods,
        loadBalancing: routeForm.loadBalancing
      };
      
      await gatewayApi.addRoute(routeData);
      setShowAddRoute(false);
      setRouteForm({ path: '', targetUrl: '', methods: ['GET'], loadBalancing: 'round-robin' });
      fetchData();
    } catch (error) {
      console.error('Error adding route:', error);
      alert('Error adding route: ' + (error.response?.data?.error || error.message));
    }
  };

  const handleRemoveRoute = async (path) => {
    if (!confirm('Are you sure you want to remove this route?')) return;
    
    try {
      await gatewayApi.removeRoute({ path });
      fetchData();
    } catch (error) {
      console.error('Error removing route:', error);
      alert('Error removing route: ' + (error.response?.data?.error || error.message));
    }
  };

  const handleAddDnsRecord = async (e) => {
    e.preventDefault();
    try {
      await gatewayApi.addDnsRecord(dnsForm);
      setShowAddDns(false);
      setDnsForm({ hostname: '', ip: '', description: '' });
      fetchData();
    } catch (error) {
      console.error('Error adding DNS record:', error);
      alert('Error adding DNS record: ' + (error.response?.data?.error || error.message));
    }
  };

  const handleRemoveDnsRecord = async (hostname) => {
    if (!confirm('Are you sure you want to remove this DNS record?')) return;
    
    try {
      await gatewayApi.removeDnsRecord(hostname);
      fetchData();
    } catch (error) {
      console.error('Error removing DNS record:', error);
      alert('Error removing DNS record: ' + (error.response?.data?.error || error.message));
    }
  };

  const renderRoutes = () => (
    <div className="routes-section">
      <div className="section-header">
        <h3>Dynamic Routes</h3>
        <button 
          className="btn btn-primary"
          onClick={() => setShowAddRoute(true)}
        >
          <Plus size={16} />
          Add Route
        </button>
      </div>

      {showAddRoute && (
        <div className="modal-overlay">
          <div className="modal">
            <div className="modal-header">
              <h3>Add Route</h3>
              <button className="btn-close" onClick={() => setShowAddRoute(false)}>×</button>
            </div>
            <form onSubmit={handleAddRoute} className="route-form">
              <div className="form-group">
                <label>Path Pattern</label>
                <input
                  type="text"
                  value={routeForm.path}
                  onChange={(e) => setRouteForm(prev => ({ ...prev, path: e.target.value }))}
                  placeholder="/api/service/*"
                  required
                />
              </div>
              <div className="form-group">
                <label>Target URL</label>
                <input
                  type="url"
                  value={routeForm.targetUrl}
                  onChange={(e) => setRouteForm(prev => ({ ...prev, targetUrl: e.target.value }))}
                  placeholder="http://localhost:3001"
                  required
                />
              </div>
              <div className="form-group">
                <label>HTTP Methods</label>
                <div className="checkbox-group">
                  {['GET', 'POST', 'PUT', 'DELETE'].map(method => (
                    <label key={method} className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={routeForm.methods.includes(method)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setRouteForm(prev => ({ ...prev, methods: [...prev.methods, method] }));
                          } else {
                            setRouteForm(prev => ({ ...prev, methods: prev.methods.filter(m => m !== method) }));
                          }
                        }}
                      />
                      {method}
                    </label>
                  ))}
                </div>
              </div>
              <div className="form-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowAddRoute(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Add Route
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="routes-list">
        {routes.map((route, index) => (
          <div key={index} className="route-card">
            <div className="route-header">
              <div className="route-path">
                <Router size={20} />
                <span>{route.path}</span>
              </div>
              <button
                className="btn-icon danger"
                onClick={() => handleRemoveRoute(route.path)}
              >
                <Trash2 size={16} />
              </button>
            </div>
            <div className="route-details">
              <div className="detail-item">
                <span>Target:</span>
                <span>{route.targets?.[0]?.url || 'N/A'}</span>
              </div>
              <div className="detail-item">
                <span>Methods:</span>
                <span>{route.methods?.join(', ') || 'N/A'}</span>
              </div>
              <div className="detail-item">
                <span>Load Balancing:</span>
                <span>{route.loadBalancing || 'round-robin'}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  const renderDns = () => (
    <div className="dns-section">
      <div className="section-header">
        <h3>DNS Management</h3>
        <div className="header-actions">
          <button 
            className="btn btn-secondary"
            onClick={fetchData}
          >
            <RefreshCw size={16} />
            Refresh
          </button>
          <button 
            className="btn btn-primary"
            onClick={() => setShowAddDns(true)}
          >
            <Plus size={16} />
            Add Record
          </button>
        </div>
      </div>

      {dnsStats && (
        <div className="dns-stats">
          <div className="stat-card">
            <h4>Total Queries</h4>
            <span>{dnsStats.totalQueries || 0}</span>
          </div>
          <div className="stat-card">
            <h4>Cache Hits</h4>
            <span>{dnsStats.cacheHits || 0}</span>
          </div>
          <div className="stat-card">
            <h4>Cache Miss</h4>
            <span>{dnsStats.cacheMiss || 0}</span>
          </div>
          <div className="stat-card">
            <h4>Success Rate</h4>
            <span>{dnsStats.successRate || '0%'}</span>
          </div>
        </div>
      )}

      {showAddDns && (
        <div className="modal-overlay">
          <div className="modal">
            <div className="modal-header">
              <h3>Add DNS Record</h3>
              <button className="btn-close" onClick={() => setShowAddDns(false)}>×</button>
            </div>
            <form onSubmit={handleAddDnsRecord} className="dns-form">
              <div className="form-group">
                <label>Hostname</label>
                <input
                  type="text"
                  value={dnsForm.hostname}
                  onChange={(e) => setDnsForm(prev => ({ ...prev, hostname: e.target.value }))}
                  placeholder="example.local"
                  required
                />
              </div>
              <div className="form-group">
                <label>IP Address</label>
                <input
                  type="text"
                  value={dnsForm.ip}
                  onChange={(e) => setDnsForm(prev => ({ ...prev, ip: e.target.value }))}
                  placeholder="192.168.1.100"
                  required
                />
              </div>
              <div className="form-group">
                <label>Description</label>
                <input
                  type="text"
                  value={dnsForm.description}
                  onChange={(e) => setDnsForm(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="Description..."
                />
              </div>
              <div className="form-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowAddDns(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Add Record
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="dns-records">
        {dnsRecords.map((record, index) => (
          <div key={index} className="dns-record">
            <div className="record-header">
              <div className="record-name">
                <Globe size={20} />
                <span>{record.hostname}</span>
              </div>
              <button
                className="btn-icon danger"
                onClick={() => handleRemoveDnsRecord(record.hostname)}
              >
                <Trash2 size={16} />
              </button>
            </div>
            <div className="record-details">
              <div className="detail-item">
                <span>IP:</span>
                <span>{record.ip}</span>
              </div>
              {record.description && (
                <div className="detail-item">
                  <span>Description:</span>
                  <span>{record.description}</span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  return (
    <div className="gateway-manager">
      <div className="gateway-header">
        <h2>Gateway Management</h2>
        <div className="tab-buttons">
          <button 
            className={`tab-button ${activeTab === 'routes' ? 'active' : ''}`}
            onClick={() => setActiveTab('routes')}
          >
            <Router size={16} />
            Routes
          </button>
          <button 
            className={`tab-button ${activeTab === 'dns' ? 'active' : ''}`}
            onClick={() => setActiveTab('dns')}
          >
            <Globe size={16} />
            DNS
          </button>
        </div>
      </div>

      {loading ? (
        <div className="loading-container">
          <RefreshCw className="loading-spinner" size={32} />
          <p>Loading gateway data...</p>
        </div>
      ) : (
        <div className="tab-content">
          {activeTab === 'routes' ? renderRoutes() : renderDns()}
        </div>
      )}
    </div>
  );
}

export default GatewayManager;