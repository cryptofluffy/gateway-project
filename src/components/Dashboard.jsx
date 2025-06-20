import { useState, useEffect } from 'react';
import { Server, Network, Router, Activity, AlertTriangle, CheckCircle } from 'lucide-react';
import { vpsApi, gatewayApi } from '../services/api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

function Dashboard({ systemHealth }) {
  const [vpsStatus, setVpsStatus] = useState(null);
  const [portForwards, setPortForwards] = useState([]);
  const [networkStats, setNetworkStats] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [vpsResponse, forwardsResponse] = await Promise.all([
          vpsApi.getStatus(),
          vpsApi.getPortForwards()
        ]);
        
        setVpsStatus(vpsResponse.data);
        setPortForwards(forwardsResponse.data.data || []);
        
        // Mock network stats for chart
        setNetworkStats([
          { time: '00:00', cpu: 20, memory: 45, network: 12 },
          { time: '04:00', cpu: 25, memory: 48, network: 18 },
          { time: '08:00', cpu: 60, memory: 62, network: 35 },
          { time: '12:00', cpu: 45, memory: 55, network: 28 },
          { time: '16:00', cpu: 70, memory: 68, network: 42 },
          { time: '20:00', cpu: 30, memory: 52, network: 22 },
        ]);
      } catch (error) {
        console.error('Error fetching dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="dashboard-loading">
        <Activity className="loading-spinner" size={32} />
        <p>Loading dashboard...</p>
      </div>
    );
  }

  const formatUptime = (uptime) => {
    const hours = Math.floor(uptime / 3600);
    const minutes = Math.floor((uptime % 3600) / 60);
    return `${hours}h ${minutes}m`;
  };

  const formatBytes = (bytes) => {
    const sizes = ['B', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 B';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h2>System Overview</h2>
        <div className="last-updated">
          Last updated: {new Date().toLocaleTimeString()}
        </div>
      </div>

      <div className="status-grid">
        <div className="status-card">
          <div className="status-card-header">
            <Server size={24} />
            <h3>Gateway Status</h3>
          </div>
          <div className="status-card-content">
            <div className={`status-indicator ${systemHealth?.status === 'OK' ? 'healthy' : 'unhealthy'}`}>
              {systemHealth?.status === 'OK' ? <CheckCircle size={20} /> : <AlertTriangle size={20} />}
              <span>{systemHealth?.status || 'Unknown'}</span>
            </div>
            <div className="status-details">
              <div className="detail-item">
                <span>Services:</span>
                <span>{systemHealth?.services ? Object.keys(systemHealth.services).length : 0}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="status-card">
          <div className="status-card-header">
            <Router size={24} />
            <h3>VPS Status</h3>
          </div>
          <div className="status-card-content">
            <div className="status-indicator healthy">
              <CheckCircle size={20} />
              <span>{vpsStatus?.status || 'Unknown'}</span>
            </div>
            <div className="status-details">
              <div className="detail-item">
                <span>Uptime:</span>
                <span>{vpsStatus?.uptime ? formatUptime(vpsStatus.uptime) : 'N/A'}</span>
              </div>
              <div className="detail-item">
                <span>Memory:</span>
                <span>{vpsStatus?.memory ? formatBytes(vpsStatus.memory.heapUsed) : 'N/A'}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="status-card">
          <div className="status-card-header">
            <Network size={24} />
            <h3>Port Forwards</h3>
          </div>
          <div className="status-card-content">
            <div className="status-indicator healthy">
              <CheckCircle size={20} />
              <span>{portForwards.length} Active</span>
            </div>
            <div className="status-details">
              <div className="detail-item">
                <span>TCP:</span>
                <span>{portForwards.filter(f => f.protocol === 'tcp').length}</span>
              </div>
              <div className="detail-item">
                <span>UDP:</span>
                <span>{portForwards.filter(f => f.protocol === 'udp').length}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="charts-section">
        <div className="chart-card">
          <div className="chart-header">
            <h3>System Performance</h3>
          </div>
          <div className="chart-content">
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={networkStats}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="cpu" stroke="#8884d8" name="CPU %" />
                <Line type="monotone" dataKey="memory" stroke="#82ca9d" name="Memory %" />
                <Line type="monotone" dataKey="network" stroke="#ffc658" name="Network %" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="recent-activity">
        <div className="activity-card">
          <div className="activity-header">
            <h3>Recent Port Forwards</h3>
          </div>
          <div className="activity-content">
            {portForwards.slice(0, 5).map((forward, index) => (
              <div key={index} className="activity-item">
                <div className="activity-icon">
                  <Network size={16} />
                </div>
                <div className="activity-details">
                  <div className="activity-title">
                    Port {forward.publicPort} → {forward.targetIP}:{forward.targetPort}
                  </div>
                  <div className="activity-subtitle">
                    {forward.protocol?.toUpperCase()} • {forward.description || 'No description'}
                  </div>
                </div>
                <div className={`activity-status ${forward.enabled ? 'active' : 'inactive'}`}>
                  {forward.enabled ? 'Active' : 'Inactive'}
                </div>
              </div>
            ))}
            {portForwards.length === 0 && (
              <div className="no-activity">
                <p>No port forwards configured</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;