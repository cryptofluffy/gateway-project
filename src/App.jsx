import { useState, useEffect } from 'react';
import { Activity, Server, Network, Router, Shield, Settings, Key, LogOut } from 'lucide-react';
import Dashboard from './components/Dashboard';
import VPSManager from './components/VPSManager';
import GatewayManager from './components/GatewayManager';
import NetworkMonitor from './components/NetworkMonitor';
import LicenseManager from './components/LicenseManager';
import EmailLogin from './components/EmailLogin';
import { gatewayApi } from './services/api';
import './App.css';
import './styles/emailLogin.css';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [systemHealth, setSystemHealth] = useState(null);
  const [licenseInfo, setLicenseInfo] = useState(null);
  const [user, setUser] = useState(null);
  const [authenticated, setAuthenticated] = useState(false);

  const tabs = [
    { id: 'dashboard', label: 'Dashboard', icon: Activity },
    { id: 'vps', label: 'VPS Manager', icon: Server },
    { id: 'gateway', label: 'Gateway', icon: Router },
    { id: 'network', label: 'Network', icon: Network },
    { id: 'license', label: 'License', icon: Key },
  ];

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await gatewayApi.getHealth();
        setSystemHealth(response.data);
      } catch (error) {
        setSystemHealth({ status: 'ERROR', error: error.message });
      }
    };

    if (authenticated) {
      checkHealth();
      const interval = setInterval(checkHealth, 30000);
      return () => clearInterval(interval);
    }
  }, [authenticated]);

  const handleLogin = (userData) => {
    setUser(userData);
    setAuthenticated(true);
    
    // Set license info from FastSpring subscription data
    if (userData.subscription) {
      setLicenseInfo({
        plan: userData.subscription.plan,
        status: 'active',
        gatewaysLimit: userData.subscription.quantity,
        gatewaysUsed: 0, // This would be fetched from the API in a real implementation
        nextBillingDate: userData.subscription.nextBillingDate,
        subscriptionId: userData.subscription.id
      });
    }
  };

  const handleLogout = () => {
    setUser(null);
    setAuthenticated(false);
    setLicenseInfo(null);
    setActiveTab('dashboard');
  };

  const renderActiveComponent = () => {
    switch (activeTab) {
      case 'dashboard':
        return <Dashboard systemHealth={systemHealth} licenseInfo={licenseInfo} />;
      case 'vps':
        return <VPSManager licenseInfo={licenseInfo} />;
      case 'gateway':
        return <GatewayManager licenseInfo={licenseInfo} />;
      case 'network':
        return <NetworkMonitor />;
      case 'license':
        return <LicenseManager licenseInfo={licenseInfo} setLicenseInfo={setLicenseInfo} />;
      default:
        return <Dashboard systemHealth={systemHealth} licenseInfo={licenseInfo} />;
    }
  };

  // Show login screen if not authenticated
  if (!authenticated) {
    return <EmailLogin onLogin={handleLogin} />;
  }

  // Show dashboard if authenticated
  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <div className="header-left">
            <Shield className="header-logo" size={32} />
            <h1>Backend Management Dashboard</h1>
          </div>
          <div className="header-right">
            {licenseInfo && (
              <div className="license-indicator">
                <Key size={16} />
                <span>{licenseInfo.plan} ({licenseInfo.gatewaysUsed}/{licenseInfo.gatewaysLimit} Gateways)</span>
              </div>
            )}
            <div className={`health-indicator ${systemHealth?.status === 'OK' ? 'healthy' : 'unhealthy'}`}>
              <div className="health-dot"></div>
              <span>{systemHealth?.status || 'Checking...'}</span>
            </div>
            <div className="user-info">
              <span className="user-email">{user?.email}</span>
              <button 
                className="btn-icon logout-btn" 
                onClick={handleLogout}
                title="Logout"
              >
                <LogOut size={16} />
              </button>
            </div>
          </div>
        </div>
      </header>

      <nav className="app-nav">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              className={`nav-tab ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              <Icon size={18} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </nav>

      <main className="app-main">
        {renderActiveComponent()}
      </main>
    </div>
  );
}

export default App
