// Mock API service for testing dashboard functionality
let mockData = {
  gateways: [
    {
      id: 'gw_001',
      name: 'Office Gateway',
      location: 'Berlin Office',
      description: 'Main office network gateway',
      connected: true,
      ip: '192.168.1.1',
      lastSeen: new Date().toISOString(),
      createdAt: new Date(Date.now() - 86400000).toISOString()
    },
    {
      id: 'gw_002', 
      name: 'Home Network',
      location: 'Home',
      description: 'Personal home gateway',
      connected: false,
      ip: '192.168.2.1',
      lastSeen: new Date(Date.now() - 3600000).toISOString(),
      createdAt: new Date(Date.now() - 172800000).toISOString()
    }
  ],
  routes: [
    {
      path: '/api/users/*',
      targets: [{ url: 'http://localhost:3001', healthy: true, weight: 1 }],
      methods: ['GET', 'POST', 'PUT', 'DELETE'],
      loadBalancing: 'round-robin',
      enabled: true
    },
    {
      path: '/api/orders/*',
      targets: [{ url: 'http://localhost:3002', healthy: true, weight: 1 }],
      methods: ['GET', 'POST'],
      loadBalancing: 'least-connections',
      enabled: true
    }
  ],
  dnsRecords: [
    {
      hostname: 'api.local',
      ip: '192.168.1.100',
      description: 'Internal API server',
      ttl: 300
    },
    {
      hostname: 'db.local',
      ip: '192.168.1.101',
      description: 'Database server',
      ttl: 600
    }
  ],
  dnsStats: {
    totalQueries: 15420,
    cacheHits: 12336,
    cacheMiss: 3084,
    successRate: '96.2%',
    avgResponseTime: '12ms'
  },
  portForwards: [
    {
      id: 'pf_001',
      name: 'Web Server',
      publicPort: 80,
      privateIp: '192.168.1.100',
      privatePort: 8080,
      protocol: 'TCP',
      enabled: true,
      gatewayId: 'gw_001'
    },
    {
      id: 'pf_002',
      name: 'SSH Access',
      publicPort: 2222,
      privateIp: '192.168.1.10',
      privatePort: 22,
      protocol: 'TCP',
      enabled: true,
      gatewayId: 'gw_001'
    }
  ],
  vpsStatus: {
    uptime: '15 days, 8 hours',
    cpu: 45.2,
    memory: 67.8,
    disk: 34.1,
    network: {
      inbound: '125.4 MB/s',
      outbound: '89.7 MB/s'
    },
    activeConnections: 1247
  },
  networkInterfaces: [
    {
      name: 'eth0',
      ip: '192.168.1.100',
      netmask: '255.255.255.0',
      gateway: '192.168.1.1',
      status: 'up',
      speed: '1000 Mbps'
    },
    {
      name: 'wg0',
      ip: '10.0.0.1',
      netmask: '255.255.255.0',
      gateway: null,
      status: 'up',
      speed: 'N/A'
    }
  ]
};

// Simulate network delay
const delay = (ms = 500) => new Promise(resolve => setTimeout(resolve, ms));

// Generate realistic install command
const generateInstallCommand = (gatewayId, vpsIp = '45.67.89.123') => {
  // Generate realistic WireGuard key (base64 encoded)
  const generateKey = () => {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
    let key = '';
    for (let i = 0; i < 43; i++) {
      key += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return key + '=';
  };
  
  const wireguardKey = generateKey();
  const tunnelNetwork = `10.0.${Math.floor(Math.random() * 255)}.1/24`;
  
  return `<span class="command-base">curl -fsSL https://install.gatewaypi.com/install.sh | bash -s --</span> <span class="command-continuation">\\</span>
  <span class="command-param"><span class="command-param-name">--vps-ip=</span><span class="command-param-value">"${vpsIp}"</span></span> <span class="command-continuation">\\</span>
  <span class="command-param"><span class="command-param-name">--gateway-id=</span><span class="command-param-value">"${gatewayId}"</span></span> <span class="command-continuation">\\</span>
  <span class="command-param"><span class="command-param-name">--wireguard-key=</span><span class="command-param-value">"${wireguardKey}"</span></span> <span class="command-continuation">\\</span>
  <span class="command-param"><span class="command-param-name">--tunnel-ip=</span><span class="command-param-value">"${tunnelNetwork}"</span></span>`;
};

export const mockGatewayApi = {
  async getHealth() {
    await delay(200);
    return {
      data: {
        success: true,
        data: {
          status: 'healthy',
          timestamp: new Date().toISOString(),
          services: {
            gateway: 'running',
            dns: 'running',
            routing: 'running'
          }
        }
      }
    };
  },

  async getGateways() {
    await delay(300);
    return {
      data: {
        success: true,
        data: mockData.gateways
      }
    };
  },

  async addGateway(gatewayData) {
    await delay(500);
    const newGateway = {
      id: `gw_${Date.now().toString(36)}`,
      ...gatewayData,
      connected: false,
      ip: null,
      lastSeen: null,
      createdAt: new Date().toISOString()
    };
    mockData.gateways.push(newGateway);
    return {
      data: {
        success: true,
        data: newGateway
      }
    };
  },

  async removeGateway(gatewayId) {
    await delay(300);
    mockData.gateways = mockData.gateways.filter(gw => gw.id !== gatewayId);
    return {
      data: {
        success: true,
        message: 'Gateway removed successfully'
      }
    };
  },

  async getGatewayInstallCommand(gatewayId) {
    await delay(400);
    const command = generateInstallCommand(gatewayId);
    return {
      data: {
        success: true,
        data: {
          command,
          gatewayId,
          instructions: [
            'SSH into your gateway hardware',
            'Paste and run the command above',
            'The gateway will automatically connect to this VPS',
            'Check the gateway list for connection status'
          ]
        }
      }
    };
  },

  async getRoutes() {
    await delay(250);
    return {
      data: {
        success: true,
        data: mockData.routes
      }
    };
  },

  async addRoute(routeData) {
    await delay(400);
    const newRoute = {
      ...routeData,
      id: `route_${Date.now().toString(36)}`,
      enabled: true,
      createdAt: new Date().toISOString()
    };
    mockData.routes.push(newRoute);
    return {
      data: {
        success: true,
        data: newRoute
      }
    };
  },

  async removeRoute(routeData) {
    await delay(300);
    mockData.routes = mockData.routes.filter(route => route.path !== routeData.path);
    return {
      data: {
        success: true,
        message: 'Route removed successfully'
      }
    };
  },

  async getDnsRecords() {
    await delay(200);
    return {
      data: {
        success: true,
        data: mockData.dnsRecords
      }
    };
  },

  async addDnsRecord(recordData) {
    await delay(350);
    const newRecord = {
      ...recordData,
      ttl: 300,
      createdAt: new Date().toISOString()
    };
    mockData.dnsRecords.push(newRecord);
    return {
      data: {
        success: true,
        data: newRecord
      }
    };
  },

  async removeDnsRecord(hostname) {
    await delay(250);
    mockData.dnsRecords = mockData.dnsRecords.filter(record => record.hostname !== hostname);
    return {
      data: {
        success: true,
        message: 'DNS record removed successfully'
      }
    };
  },

  async getDnsStats() {
    await delay(150);
    // Simulate changing stats
    mockData.dnsStats.totalQueries += Math.floor(Math.random() * 10);
    mockData.dnsStats.cacheHits += Math.floor(Math.random() * 8);
    return {
      data: {
        success: true,
        data: mockData.dnsStats
      }
    };
  },

  async getNetworkInterfaces() {
    await delay(200);
    return {
      data: {
        success: true,
        data: mockData.networkInterfaces
      }
    };
  },

  async getNetworkServices() {
    await delay(300);
    return {
      data: {
        success: true,
        data: [
          { name: 'SSH', port: 22, status: 'running', protocol: 'TCP' },
          { name: 'HTTP', port: 80, status: 'running', protocol: 'TCP' },
          { name: 'HTTPS', port: 443, status: 'running', protocol: 'TCP' },
          { name: 'WireGuard', port: 51820, status: 'running', protocol: 'UDP' },
          { name: 'DNS', port: 53, status: 'running', protocol: 'UDP' }
        ]
      }
    };
  },

  async performNetworkScan() {
    await delay(2000); // Simulate longer scanning time
    return {
      data: {
        success: true,
        data: {
          scanId: `scan_${Date.now()}`,
          devices: [
            { ip: '192.168.1.1', mac: '00:11:22:33:44:55', vendor: 'Router', hostname: 'gateway.local' },
            { ip: '192.168.1.10', mac: '00:11:22:33:44:66', vendor: 'Apple', hostname: 'macbook.local' },
            { ip: '192.168.1.20', mac: '00:11:22:33:44:77', vendor: 'Samsung', hostname: 'phone.local' },
            { ip: '192.168.1.100', mac: '00:11:22:33:44:88', vendor: 'Server', hostname: 'api.local' }
          ],
          timestamp: new Date().toISOString()
        }
      }
    };
  }
};

export const mockVpsApi = {
  async getStatus() {
    await delay(200);
    // Simulate changing values
    mockData.vpsStatus.cpu = 30 + Math.random() * 40;
    mockData.vpsStatus.memory = 50 + Math.random() * 30;
    return {
      data: {
        success: true,
        data: mockData.vpsStatus
      }
    };
  },

  async getPortForwards() {
    await delay(250);
    return {
      data: {
        success: true,
        data: mockData.portForwards
      }
    };
  },

  async addPortForward(forwardData) {
    await delay(400);
    const newForward = {
      id: `pf_${Date.now().toString(36)}`,
      ...forwardData,
      enabled: true,
      createdAt: new Date().toISOString()
    };
    mockData.portForwards.push(newForward);
    return {
      data: {
        success: true,
        data: newForward
      }
    };
  },

  async removePortForward(forwardId) {
    await delay(300);
    mockData.portForwards = mockData.portForwards.filter(pf => pf.id !== forwardId);
    return {
      data: {
        success: true,
        message: 'Port forward removed successfully'
      }
    };
  },

  async togglePortForward(forwardId, enabled) {
    await delay(200);
    const forward = mockData.portForwards.find(pf => pf.id === forwardId);
    if (forward) {
      forward.enabled = enabled;
    }
    return {
      data: {
        success: true,
        data: forward
      }
    };
  },

  async getPortForwardStatus(forwardId) {
    await delay(150);
    const forward = mockData.portForwards.find(pf => pf.id === forwardId);
    return {
      data: {
        success: true,
        data: {
          id: forwardId,
          status: forward?.enabled ? 'active' : 'inactive',
          connections: Math.floor(Math.random() * 100),
          traffic: {
            inbound: `${(Math.random() * 1000).toFixed(1)} KB/s`,
            outbound: `${(Math.random() * 500).toFixed(1)} KB/s`
          }
        }
      }
    };
  }
};

// Export combined mock API
export const mockApi = {
  ...mockGatewayApi,
  vps: mockVpsApi
};