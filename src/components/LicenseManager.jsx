import { useState, useEffect } from 'react';
import { Key, Check, X, AlertTriangle, Crown, Zap, Building, ExternalLink } from 'lucide-react';

function LicenseManager({ licenseInfo, setLicenseInfo }) {
  const [licenseKey, setLicenseKey] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Mock license validation - später durch echte FastSpring API ersetzen
  const validateLicense = async (key) => {
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      // Simuliere API Call
      await new Promise(resolve => setTimeout(resolve, 1500));

      // Mock validation logic
      const mockLicenses = {
        'STARTER-123-456': {
          valid: true,
          plan: 'Starter',
          gatewaysLimit: 1,
          gatewaysUsed: 0,
          status: 'active',
          expires: '2024-12-31',
          features: ['Basic Gateway Management', 'Port Forwarding', 'DNS Management']
        },
        'PRO-789-012': {
          valid: true,
          plan: 'Professional',
          gatewaysLimit: 5,
          gatewaysUsed: 2,
          status: 'active',
          expires: '2024-12-31',
          features: ['Advanced Gateway Management', 'Port Forwarding', 'DNS Management', 'Network Monitoring', 'Analytics']
        },
        'ENT-345-678': {
          valid: true,
          plan: 'Enterprise',
          gatewaysLimit: 999,
          gatewaysUsed: 12,
          status: 'active',
          expires: '2024-12-31',
          features: ['Unlimited Gateways', 'All Features', 'Priority Support', 'Custom Integrations', 'SLA']
        }
      };

      const license = mockLicenses[key];
      
      if (license && license.valid) {
        setLicenseInfo(license);
        localStorage.setItem('licenseKey', key);
        localStorage.setItem('licenseInfo', JSON.stringify(license));
        setSuccess('License activated successfully!');
      } else {
        throw new Error('Invalid license key');
      }
    } catch (error) {
      setError('Invalid license key. Please check your key and try again.');
    } finally {
      setLoading(false);
    }
  };

  const removeLicense = () => {
    setLicenseInfo(null);
    localStorage.removeItem('licenseKey');
    localStorage.removeItem('licenseInfo');
    setLicenseKey('');
    setSuccess('License removed successfully');
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (licenseKey.trim()) {
      validateLicense(licenseKey.trim());
    }
  };

  // Load license from localStorage on mount
  useEffect(() => {
    const savedKey = localStorage.getItem('licenseKey');
    const savedInfo = localStorage.getItem('licenseInfo');
    
    if (savedKey && savedInfo) {
      try {
        const info = JSON.parse(savedInfo);
        setLicenseInfo(info);
        setLicenseKey(savedKey);
      } catch (error) {
        localStorage.removeItem('licenseKey');
        localStorage.removeItem('licenseInfo');
      }
    }
  }, [setLicenseInfo]);

  const getPlanIcon = (plan) => {
    switch (plan) {
      case 'Starter': return <Zap className="plan-icon starter" size={20} />;
      case 'Professional': return <Crown className="plan-icon pro" size={20} />;
      case 'Enterprise': return <Building className="plan-icon enterprise" size={20} />;
      default: return <Key size={20} />;
    }
  };

  const getPlanColor = (plan) => {
    switch (plan) {
      case 'Starter': return 'starter';
      case 'Professional': return 'pro';
      case 'Enterprise': return 'enterprise';
      default: return '';
    }
  };

  return (
    <div className="license-manager">
      <div className="license-header">
        <h2>License Management</h2>
        <p>Manage your software license and view usage information</p>
      </div>

      {!licenseInfo ? (
        <div className="license-activation">
          <div className="activation-card">
            <div className="activation-header">
              <Key size={32} />
              <h3>Activate Your License</h3>
              <p>Enter your license key to unlock all features</p>
            </div>

            <form onSubmit={handleSubmit} className="activation-form">
              <div className="form-group">
                <label htmlFor="licenseKey">License Key</label>
                <input
                  type="text"
                  id="licenseKey"
                  value={licenseKey}
                  onChange={(e) => setLicenseKey(e.target.value)}
                  placeholder="Enter your license key (e.g., STARTER-123-456)"
                  required
                  disabled={loading}
                />
              </div>

              {error && (
                <div className="error-message">
                  <X size={16} />
                  <span>{error}</span>
                </div>
              )}

              {success && (
                <div className="success-message">
                  <Check size={16} />
                  <span>{success}</span>
                </div>
              )}

              <button 
                type="submit" 
                className="btn btn-primary activation-btn"
                disabled={loading || !licenseKey.trim()}
              >
                {loading ? 'Validating...' : 'Activate License'}
              </button>
            </form>

            <div className="demo-keys">
              <h4>Demo License Keys for Testing:</h4>
              <div className="demo-key-list">
                <div className="demo-key" onClick={() => setLicenseKey('STARTER-123-456')}>
                  <strong>STARTER-123-456</strong> - Starter Plan (1 Gateway)
                </div>
                <div className="demo-key" onClick={() => setLicenseKey('PRO-789-012')}>
                  <strong>PRO-789-012</strong> - Professional Plan (5 Gateways)
                </div>
                <div className="demo-key" onClick={() => setLicenseKey('ENT-345-678')}>
                  <strong>ENT-345-678</strong> - Enterprise Plan (Unlimited)
                </div>
              </div>
            </div>

            <div className="purchase-info">
              <p>Don't have a license yet?</p>
              <a href="#" className="btn btn-secondary">
                <ExternalLink size={16} />
                Purchase License
              </a>
            </div>
          </div>
        </div>
      ) : (
        <div className="license-info">
          <div className="license-card">
            <div className="license-card-header">
              <div className="plan-info">
                {getPlanIcon(licenseInfo.plan)}
                <div>
                  <h3>{licenseInfo.plan} Plan</h3>
                  <p className={`plan-status ${licenseInfo.status}`}>
                    {licenseInfo.status === 'active' ? 'Active' : 'Inactive'}
                  </p>
                </div>
              </div>
              <button 
                className="btn btn-secondary"
                onClick={removeLicense}
              >
                Remove License
              </button>
            </div>

            <div className="license-details">
              <div className="detail-grid">
                <div className="detail-item">
                  <span className="detail-label">License Key:</span>
                  <span className="detail-value">{licenseKey}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Expires:</span>
                  <span className="detail-value">{new Date(licenseInfo.expires).toLocaleDateString()}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Gateway Usage:</span>
                  <span className="detail-value">
                    {licenseInfo.gatewaysUsed} / {licenseInfo.gatewaysLimit === 999 ? '∞' : licenseInfo.gatewaysLimit}
                  </span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Status:</span>
                  <span className={`detail-value status ${licenseInfo.status}`}>
                    {licenseInfo.status === 'active' ? (
                      <><Check size={16} /> Active</>
                    ) : (
                      <><X size={16} /> Inactive</>
                    )}
                  </span>
                </div>
              </div>
            </div>

            <div className="gateway-usage">
              <h4>Gateway Usage</h4>
              <div className="usage-bar">
                <div 
                  className={`usage-fill ${getPlanColor(licenseInfo.plan)}`}
                  style={{ 
                    width: `${licenseInfo.gatewaysLimit === 999 ? 
                      Math.min((licenseInfo.gatewaysUsed / 20) * 100, 100) : 
                      (licenseInfo.gatewaysUsed / licenseInfo.gatewaysLimit) * 100}%` 
                  }}
                ></div>
              </div>
              <p className="usage-text">
                {licenseInfo.gatewaysUsed} of {licenseInfo.gatewaysLimit === 999 ? 'unlimited' : licenseInfo.gatewaysLimit} gateways used
              </p>
              
              {licenseInfo.gatewaysUsed >= licenseInfo.gatewaysLimit && licenseInfo.gatewaysLimit !== 999 && (
                <div className="warning-message">
                  <AlertTriangle size={16} />
                  <span>Gateway limit reached. Upgrade your plan to add more gateways.</span>
                </div>
              )}
            </div>

            <div className="features-list">
              <h4>Included Features</h4>
              <div className="features-grid">
                {licenseInfo.features.map((feature, index) => (
                  <div key={index} className="feature-item">
                    <Check size={16} />
                    <span>{feature}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="upgrade-section">
            <h4>Need More Gateways?</h4>
            <p>Upgrade your plan to unlock more gateways and advanced features.</p>
            <a href="#" className="btn btn-primary">
              <Crown size={16} />
              Upgrade Plan
            </a>
          </div>
        </div>
      )}
    </div>
  );
}

export default LicenseManager;