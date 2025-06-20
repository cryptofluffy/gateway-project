import { useState, useEffect } from 'react';
import { Network, Wifi, Search, RefreshCw, Monitor } from 'lucide-react';
import { gatewayApi } from '../services/api';

function NetworkMonitor() {
  const [networkData, setNetworkData] = useState({
    interfaces: [],
    services: [],
    topology: null,
    report: null
  });
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [activeTab, setActiveTab] = useState('interfaces');

  useEffect(() => {
    fetchNetworkData();
  }, []);

  const fetchNetworkData = async () => {
    try {
      const [interfacesResponse, servicesResponse, topologyResponse, reportResponse] = await Promise.all([
        gatewayApi.getNetworkInterfaces(),
        gatewayApi.getNetworkServices(),
        gatewayApi.getNetworkTopology(),
        gatewayApi.getNetworkReport()
      ]);

      setNetworkData({
        interfaces: interfacesResponse.data.data || [],
        services: servicesResponse.data.data || [],
        topology: topologyResponse.data.data || null,
        report: reportResponse.data.data || null
      });
    } catch (error) {
      console.error('Error fetching network data:', error);
    } finally {
      setLoading(false);
    }
  };

  const performNetworkScan = async () => {
    setScanning(true);
    try {
      await gatewayApi.performNetworkScan();
      await fetchNetworkData();
    } catch (error) {
      console.error('Error performing network scan:', error);
      alert('Error performing network scan: ' + (error.response?.data?.error || error.message));
    } finally {
      setScanning(false);
    }
  };

  const renderInterfaces = () => (
    <div className="interfaces-section">
      <div className="section-header">
        <h3>Network Interfaces</h3>
        <button 
          className="btn btn-secondary"
          onClick={fetchNetworkData}
          disabled={loading}
        >
          <RefreshCw size={16} className={loading ? 'spin' : ''} />
          Refresh
        </button>
      </div>
      
      <div className="interfaces-grid">
        {networkData.interfaces.map((iface, index) => (
          <div key={index} className="interface-card">
            <div className="interface-header">
              <Network size={20} />
              <span className="interface-name">{iface.name || `Interface ${index + 1}`}</span>
              <div className={`status-dot ${iface.status === 'up' ? 'active' : 'inactive'}`}></div>
            </div>
            <div className="interface-details">
              <div className="detail-row">
                <span>Status:</span>
                <span className={`status ${iface.status === 'up' ? 'active' : 'inactive'}`}>
                  {iface.status || 'Unknown'}
                </span>
              </div>
              <div className="detail-row">
                <span>IP Address:</span>
                <span>{iface.ip || 'N/A'}</span>
              </div>
              <div className="detail-row">
                <span>MAC Address:</span>
                <span>{iface.mac || 'N/A'}</span>
              </div>
              <div className="detail-row">
                <span>Type:</span>
                <span>{iface.type || 'N/A'}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  const renderServices = () => (
    <div className="services-section">
      <div className="section-header">
        <h3>Discovered Services</h3>
        <button 
          className="btn btn-primary"
          onClick={performNetworkScan}
          disabled={scanning}
        >
          <Search size={16} className={scanning ? 'spin' : ''} />
          {scanning ? 'Scanning...' : 'Scan Network'}
        </button>
      </div>
      
      <div className="services-grid">
        {networkData.services.map((service, index) => (
          <div key={index} className="service-card">
            <div className="service-header">
              <Wifi size={20} />
              <span className="service-name">{service.name || `Service ${index + 1}`}</span>
            </div>
            <div className="service-details">
              <div className="detail-row">
                <span>Host:</span>
                <span>{service.host || 'N/A'}</span>
              </div>
              <div className="detail-row">
                <span>Port:</span>
                <span>{service.port || 'N/A'}</span>
              </div>
              <div className="detail-row">
                <span>Protocol:</span>
                <span>{service.protocol || 'N/A'}</span>
              </div>
              <div className="detail-row">
                <span>Status:</span>
                <span className={`status ${service.status === 'up' ? 'active' : 'inactive'}`}>
                  {service.status || 'Unknown'}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  const renderTopology = () => (
    <div className="topology-section">
      <div className="section-header">
        <h3>Network Topology</h3>
      </div>
      
      {networkData.topology ? (
        <div className="topology-visualization">
          <div className="topology-info">
            <div className="info-card">
              <h4>Gateway Information</h4>
              <div className="info-details">
                <div className="detail-row">
                  <span>Gateway IP:</span>
                  <span>{networkData.topology.gateway || 'N/A'}</span>
                </div>
                <div className="detail-row">
                  <span>Subnet:</span>
                  <span>{networkData.topology.subnet || 'N/A'}</span>
                </div>
                <div className="detail-row">
                  <span>DNS Server:</span>
                  <span>{networkData.topology.dns || 'N/A'}</span>
                </div>
              </div>
            </div>
            
            <div className="info-card">
              <h4>Connected Devices</h4>
              <div className="devices-list">
                {networkData.topology.devices?.map((device, index) => (
                  <div key={index} className="device-item">
                    <div className="device-info">
                      <span className="device-ip">{device.ip}</span>
                      <span className="device-mac">{device.mac}</span>
                    </div>
                    <div className={`device-status ${device.online ? 'online' : 'offline'}`}>
                      {device.online ? 'Online' : 'Offline'}
                    </div>
                  </div>
                )) || []}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="no-data">
          <Monitor size={48} />
          <p>No topology data available</p>
          <button className="btn btn-primary" onClick={performNetworkScan}>
            <Search size={16} />
            Scan Network
          </button>
        </div>
      )}
    </div>
  );

  const renderReport = () => (
    <div className="report-section">
      <div className="section-header">
        <h3>Network Report</h3>
        <div className="report-timestamp">
          {networkData.report?.timestamp && (
            <span>Last updated: {new Date(networkData.report.timestamp).toLocaleString()}</span>
          )}
        </div>
      </div>
      
      {networkData.report ? (
        <div className="report-content">
          <div className="report-summary">
            <div className="summary-card">
              <h4>Network Summary</h4>
              <div className="summary-stats">
                <div className="stat-item">
                  <span>Total Interfaces:</span>
                  <span>{networkData.report.totalInterfaces || 0}</span>
                </div>
                <div className="stat-item">
                  <span>Active Services:</span>
                  <span>{networkData.report.activeServices || 0}</span>
                </div>
                <div className="stat-item">
                  <span>Connected Devices:</span>
                  <span>{networkData.report.connectedDevices || 0}</span>
                </div>
                <div className="stat-item">
                  <span>Health Score:</span>
                  <span className={`health-score ${networkData.report.healthScore > 80 ? 'good' : networkData.report.healthScore > 60 ? 'warning' : 'critical'}`}>
                    {networkData.report.healthScore || 0}%
                  </span>
                </div>
              </div>
            </div>
            
            {networkData.report.issues && networkData.report.issues.length > 0 && (
              <div className="issues-card">
                <h4>Network Issues</h4>
                <div className="issues-list">
                  {networkData.report.issues.map((issue, index) => (
                    <div key={index} className={`issue-item ${issue.severity}`}>
                      <div className="issue-title">{issue.title}</div>
                      <div className="issue-description">{issue.description}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="no-data">
          <Monitor size={48} />
          <p>No report data available</p>
          <button className="btn btn-primary" onClick={fetchNetworkData}>
            <RefreshCw size={16} />
            Generate Report
          </button>
        </div>
      )}
    </div>
  );

  return (
    <div className="network-monitor">
      <div className="network-header">
        <h2>Network Monitor</h2>
        <div className="tab-buttons">
          <button 
            className={`tab-button ${activeTab === 'interfaces' ? 'active' : ''}`}
            onClick={() => setActiveTab('interfaces')}
          >
            <Network size={16} />
            Interfaces
          </button>
          <button 
            className={`tab-button ${activeTab === 'services' ? 'active' : ''}`}
            onClick={() => setActiveTab('services')}
          >
            <Wifi size={16} />
            Services
          </button>
          <button 
            className={`tab-button ${activeTab === 'topology' ? 'active' : ''}`}
            onClick={() => setActiveTab('topology')}
          >
            <Monitor size={16} />
            Topology
          </button>
          <button 
            className={`tab-button ${activeTab === 'report' ? 'active' : ''}`}
            onClick={() => setActiveTab('report')}
          >
            <RefreshCw size={16} />
            Report
          </button>
        </div>
      </div>

      {loading ? (
        <div className="loading-container">
          <Network className="loading-spinner" size={32} />
          <p>Loading network data...</p>
        </div>
      ) : (
        <div className="tab-content">
          {activeTab === 'interfaces' && renderInterfaces()}
          {activeTab === 'services' && renderServices()}
          {activeTab === 'topology' && renderTopology()}
          {activeTab === 'report' && renderReport()}
        </div>
      )}
    </div>
  );
}

export default NetworkMonitor;