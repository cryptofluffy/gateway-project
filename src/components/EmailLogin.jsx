import { useState } from 'react';
import { Mail, ArrowRight, Shield, Loader, AlertCircle, ExternalLink } from 'lucide-react';
import { fastspringApi } from '../services/fastspringApi';

function EmailLogin({ onLogin }) {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showDemo, setShowDemo] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      // License über FastSpring API validieren
      const licenseResult = await fastspringApi.validateCustomerLicense(email);
      
      if (licenseResult.valid) {
        // Erfolgreich - Benutzer einloggen
        onLogin({
          email,
          subscription: licenseResult.subscription,
          authenticated: true
        });
      } else {
        setError('No valid license found for this email address. Please check your email or purchase a license.');
      }
    } catch (err) {
      console.error('Login error:', err);
      setError('Unable to validate license. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleDemoLogin = async (demoEmail) => {
    setEmail(demoEmail);
    setLoading(true);
    setError('');

    try {
      const licenseResult = await fastspringApi.validateCustomerLicense(demoEmail);
      if (licenseResult.valid) {
        onLogin({
          email: demoEmail,
          subscription: licenseResult.subscription,
          authenticated: true
        });
      }
    } catch (err) {
      setError('Demo login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleManageSubscription = async () => {
    if (!email) {
      setError('Please enter your email address first');
      return;
    }

    try {
      const portalLink = await fastspringApi.getCustomerPortalLink(email);
      if (portalLink) {
        window.open(portalLink, '_blank');
      } else {
        setError('Unable to generate customer portal link');
      }
    } catch (err) {
      setError('Unable to access customer portal');
    }
  };

  return (
    <div className="email-login">
      <div className="login-container">
        <div className="login-header">
          <div className="login-logo">
            <Shield size={48} />
          </div>
          <h1>GatewayPro Dashboard</h1>
          <p>Enter your email to access your gateway management dashboard</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label htmlFor="email">
              <Mail size={20} />
              Email Address
            </label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your-email@example.com"
              required
              disabled={loading}
            />
          </div>

          {error && (
            <div className="error-message">
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          <div className="form-actions">
            <button
              type="submit"
              className="btn btn-primary btn-full"
              disabled={loading || !email}
            >
              {loading ? (
                <>
                  <Loader className="loading-spinner" size={16} />
                  Validating License...
                </>
              ) : (
                <>
                  Access Dashboard
                  <ArrowRight size={16} />
                </>
              )}
            </button>
          </div>
        </form>

        <div className="login-actions">
          <button 
            type="button"
            className="btn btn-secondary"
            onClick={handleManageSubscription}
            disabled={!email || loading}
          >
            <ExternalLink size={16} />
            Manage Subscription
          </button>
        </div>

        <div className="login-info">
          <h3>How it works:</h3>
          <ol>
            <li>Enter the email address you used to purchase your license</li>
            <li>We'll validate your subscription with FastSpring</li>
            <li>Access your dashboard with your current gateway limits</li>
          </ol>
        </div>

        <div className="demo-section">
          <button 
            type="button"
            className="demo-toggle"
            onClick={() => setShowDemo(!showDemo)}
          >
            Try Demo Accounts
          </button>
          
          {showDemo && (
            <div className="demo-accounts">
              <h4>Demo Accounts:</h4>
              <div className="demo-buttons">
                <button 
                  className="demo-btn"
                  onClick={() => handleDemoLogin('demo@starter.com')}
                  disabled={loading}
                >
                  Starter Plan (1 Gateway)
                </button>
                <button 
                  className="demo-btn"
                  onClick={() => handleDemoLogin('demo@pro.com')}
                  disabled={loading}
                >
                  Professional Plan (5 Gateways)
                </button>
                <button 
                  className="demo-btn"
                  onClick={() => handleDemoLogin('demo@enterprise.com')}
                  disabled={loading}
                >
                  Enterprise Plan (50 Gateways)
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="login-footer">
          <p>
            Don't have a license yet? 
            <a href="../landing-website-test/index.html" target="_blank" rel="noopener noreferrer">
              Purchase one here
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}

export default EmailLogin;