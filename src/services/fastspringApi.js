// FastSpring API Service für serverlose License-Validierung
const FASTSPRING_CONFIG = {
  apiUrl: 'https://api.fastspring.com',
  // Diese Credentials würden normalerweise über Environment-Variablen gesetzt
  username: import.meta.env.VITE_FASTSPRING_USERNAME || 'demo_username',
  password: import.meta.env.VITE_FASTSPRING_PASSWORD || 'demo_password',
  storefront: import.meta.env.VITE_FASTSPRING_STOREFRONT || 'demo.onfastspring.com'
};

class FastSpringApiService {
  constructor() {
    this.credentials = btoa(`${FASTSPRING_CONFIG.username}:${FASTSPRING_CONFIG.password}`);
  }

  async makeRequest(endpoint, options = {}) {
    const url = `${FASTSPRING_CONFIG.apiUrl}${endpoint}`;
    
    const response = await fetch(url, {
      headers: {
        'Authorization': `Basic ${this.credentials}`,
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    });

    if (!response.ok) {
      throw new Error(`FastSpring API error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  // License-Validierung über Email
  async validateCustomerLicense(email) {
    try {
      // Alle aktiven Subscriptions für Email abrufen
      const subscriptions = await this.makeRequest(`/subscriptions?account=${encodeURIComponent(email)}&status=active`);
      
      if (subscriptions.subscriptions && subscriptions.subscriptions.length > 0) {
        const subscription = subscriptions.subscriptions[0];
        
        return {
          valid: true,
          subscription: {
            id: subscription.id,
            status: subscription.state,
            quantity: subscription.quantity || 1,
            product: subscription.product,
            nextBillingDate: subscription.next,
            plan: this.getPlanFromProduct(subscription.product)
          }
        };
      }

      return { valid: false, error: 'No active subscription found' };
    } catch (error) {
      console.error('License validation error:', error);
      return { valid: false, error: error.message };
    }
  }

  // Plan-Information aus Produkt extrahieren
  getPlanFromProduct(product) {
    if (!product) return 'Unknown';
    
    // Basierend auf Produkt-ID oder Name
    if (product.includes('starter') || product.includes('basic')) {
      return 'Starter';
    } else if (product.includes('professional') || product.includes('pro')) {
      return 'Professional';
    } else if (product.includes('enterprise')) {
      return 'Enterprise';
    }
    
    return 'Custom';
  }

  // Customer Account Management Link generieren
  async getCustomerPortalLink(email, targetTab = '#/subscriptions') {
    try {
      const response = await this.makeRequest('/accounts', {
        method: 'POST',
        body: JSON.stringify({
          contact: { email: email },
          target: targetTab
        })
      });

      return response.accounts[0]?.url || null;
    } catch (error) {
      console.error('Error generating customer portal link:', error);
      return null;
    }
  }

  // Subscription-Details abrufen
  async getSubscriptionDetails(subscriptionId) {
    try {
      const subscription = await this.makeRequest(`/subscriptions/${subscriptionId}`);
      return subscription;
    } catch (error) {
      console.error('Error fetching subscription details:', error);
      return null;
    }
  }

  // Account-Informationen abrufen
  async getAccountInfo(email) {
    try {
      const accounts = await this.makeRequest(`/accounts?email=${encodeURIComponent(email)}`);
      return accounts.accounts?.[0] || null;
    } catch (error) {
      console.error('Error fetching account info:', error);
      return null;
    }
  }
}

// Mock-Implementation für Entwicklung
class MockFastSpringApiService {
  async validateCustomerLicense(email) {
    // Simuliere Netzwerk-Delay
    await new Promise(resolve => setTimeout(resolve, 500));

    // Demo-Lizenzen
    const demoLicenses = {
      'demo@starter.com': {
        valid: true,
        subscription: {
          id: 'sub_starter_123',
          status: 'active',
          quantity: 1,
          product: 'gateway-starter',
          nextBillingDate: '2024-07-20',
          plan: 'Starter'
        }
      },
      'demo@pro.com': {
        valid: true,
        subscription: {
          id: 'sub_pro_456',
          status: 'active',
          quantity: 5,
          product: 'gateway-professional',
          nextBillingDate: '2024-07-20',
          plan: 'Professional'
        }
      },
      'demo@enterprise.com': {
        valid: true,
        subscription: {
          id: 'sub_ent_789',
          status: 'active',
          quantity: 50,
          product: 'gateway-enterprise',
          nextBillingDate: '2024-07-20',
          plan: 'Enterprise'
        }
      }
    };

    return demoLicenses[email] || { valid: false, error: 'No license found' };
  }

  async getCustomerPortalLink(email, targetTab = '#/subscriptions') {
    await new Promise(resolve => setTimeout(resolve, 300));
    return `https://demo.onfastspring.com/account/manage${targetTab}?email=${encodeURIComponent(email)}`;
  }

  async getSubscriptionDetails(subscriptionId) {
    await new Promise(resolve => setTimeout(resolve, 200));
    return {
      id: subscriptionId,
      state: 'active',
      quantity: 5,
      product: 'gateway-professional'
    };
  }

  async getAccountInfo(email) {
    await new Promise(resolve => setTimeout(resolve, 200));
    return {
      id: 'acc_' + email.replace('@', '_').replace('.', '_'),
      contact: { email }
    };
  }
}

// Service-Instance basierend auf Umgebung
const USE_MOCK = import.meta.env.VITE_USE_FASTSPRING_MOCK !== 'false';
export const fastspringApi = USE_MOCK ? new MockFastSpringApiService() : new FastSpringApiService();

export default fastspringApi;