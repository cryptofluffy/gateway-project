#!/bin/bash

# Gateway Pro Dashboard - VPS Installation Script
# Usage: curl -fsSL https://raw.githubusercontent.com/yourusername/gateway-dashboard/main/install-vps.sh | bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
DOMAIN=""
EMAIL=""
INSTALL_DIR="/opt/gateway-dashboard"
FASTSPRING_USERNAME=""
FASTSPRING_PASSWORD=""
FASTSPRING_STOREFRONT=""

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Function to show help
show_help() {
    echo "Gateway Pro Dashboard - VPS Installation Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --domain=DOMAIN              Your domain (required)"
    echo "  --email=EMAIL                Email for Let's Encrypt (required)"
    echo "  --fastspring-user=USER       FastSpring API Username"
    echo "  --fastspring-pass=PASS       FastSpring API Password"
    echo "  --fastspring-store=STORE     FastSpring Storefront"
    echo "  -h, --help                   Show this help message"
    echo ""
    echo "Example:"
    echo "  curl -fsSL https://install.gatewaypi.com/install-vps.sh | bash -s -- \\"
    echo "    --domain=\"dashboard.your-domain.com\" \\"
    echo "    --email=\"admin@your-domain.com\" \\"
    echo "    --fastspring-user=\"your_api_user\" \\"
    echo "    --fastspring-pass=\"your_api_pass\" \\"
    echo "    --fastspring-store=\"yourstore.onfastspring.com\""
}

# Function to parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --domain=*)
                DOMAIN="${1#*=}"
                shift
                ;;
            --email=*)
                EMAIL="${1#*=}"
                shift
                ;;
            --fastspring-user=*)
                FASTSPRING_USERNAME="${1#*=}"
                shift
                ;;
            --fastspring-pass=*)
                FASTSPRING_PASSWORD="${1#*=}"
                shift
                ;;
            --fastspring-store=*)
                FASTSPRING_STOREFRONT="${1#*=}"
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                ;;
        esac
    done
}

# Function to check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root (use sudo)"
    fi
}

# Function to detect OS
detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$ID
        OS_VERSION=$VERSION_ID
    else
        print_error "Cannot detect operating system"
    fi
    
    print_status "Detected OS: $OS $OS_VERSION"
}

# Function to install dependencies
install_dependencies() {
    print_status "Installing dependencies..."
    
    case $OS in
        ubuntu|debian)
            apt-get update
            apt-get install -y curl wget git nginx certbot python3-certbot-nginx docker.io docker-compose ufw
            ;;
        centos|rhel|fedora)
            if command -v dnf &> /dev/null; then
                dnf install -y curl wget git nginx certbot python3-certbot-nginx docker docker-compose firewalld
            else
                yum install -y curl wget git nginx certbot python3-certbot-nginx docker docker-compose firewalld
            fi
            ;;
        *)
            print_error "Unsupported operating system: $OS"
            ;;
    esac
    
    # Start Docker
    systemctl enable docker
    systemctl start docker
    
    print_success "Dependencies installed"
}

# Function to setup firewall
setup_firewall() {
    print_status "Setting up firewall..."
    
    case $OS in
        ubuntu|debian)
            ufw --force enable
            ufw allow ssh
            ufw allow 80/tcp
            ufw allow 443/tcp
            ufw allow 51820/udp  # WireGuard
            ;;
        centos|rhel|fedora)
            systemctl enable firewalld
            systemctl start firewalld
            firewall-cmd --permanent --add-service=ssh
            firewall-cmd --permanent --add-service=http
            firewall-cmd --permanent --add-service=https
            firewall-cmd --permanent --add-port=51820/udp
            firewall-cmd --reload
            ;;
    esac
    
    print_success "Firewall configured"
}

# Function to clone repository
clone_repository() {
    print_status "Cloning Gateway Dashboard repository..."
    
    # Remove existing directory if present
    if [[ -d "$INSTALL_DIR" ]]; then
        rm -rf "$INSTALL_DIR"
    fi
    
    # Clone repository
    git clone https://github.com/yourusername/gateway-dashboard.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    
    print_success "Repository cloned"
}

# Function to setup environment
setup_environment() {
    print_status "Setting up environment configuration..."
    
    # Copy environment template
    cp .env.example .env
    
    # Set production values
    sed -i "s/NODE_ENV=development/NODE_ENV=production/" .env
    sed -i "s/VITE_USE_FASTSPRING_MOCK=true/VITE_USE_FASTSPRING_MOCK=false/" .env
    sed -i "s/your-vps-domain.com/$DOMAIN/" .env
    sed -i "s/your.vps.ip.address/$(curl -s ifconfig.me)/" .env
    
    # Set FastSpring credentials if provided
    if [[ -n "$FASTSPRING_USERNAME" ]]; then
        sed -i "s/your_fastspring_username/$FASTSPRING_USERNAME/" .env
    fi
    
    if [[ -n "$FASTSPRING_PASSWORD" ]]; then
        sed -i "s/your_fastspring_password/$FASTSPRING_PASSWORD/" .env
    fi
    
    if [[ -n "$FASTSPRING_STOREFRONT" ]]; then
        sed -i "s/yourstore.onfastspring.com/$FASTSPRING_STOREFRONT/" .env
    fi
    
    print_success "Environment configured"
}

# Function to setup SSL certificates
setup_ssl() {
    print_status "Setting up SSL certificates with Let's Encrypt..."
    
    # Stop nginx if running
    systemctl stop nginx || true
    
    # Create SSL directory
    mkdir -p ssl
    
    # Get SSL certificate
    certbot certonly --standalone \
        --non-interactive \
        --agree-tos \
        --email "$EMAIL" \
        -d "$DOMAIN"
    
    # Copy certificates
    cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem ./ssl/
    cp /etc/letsencrypt/live/$DOMAIN/privkey.pem ./ssl/
    
    print_success "SSL certificates configured"
}

# Function to configure nginx
configure_nginx() {
    print_status "Configuring nginx..."
    
    # Update nginx configuration with actual domain
    sed -i "s/your-domain.com/$DOMAIN/g" nginx.conf
    
    # Copy nginx configuration
    cp nginx.conf /etc/nginx/sites-available/gateway-dashboard
    
    # Remove default site and enable our site
    rm -f /etc/nginx/sites-enabled/default
    ln -sf /etc/nginx/sites-available/gateway-dashboard /etc/nginx/sites-enabled/
    
    # Test nginx configuration
    nginx -t
    
    print_success "nginx configured"
}

# Function to deploy application
deploy_application() {
    print_status "Deploying application with Docker Compose..."
    
    # Build and start containers
    docker-compose up -d --build
    
    # Wait for containers to start
    sleep 10
    
    # Check container status
    docker-compose ps
    
    print_success "Application deployed"
}

# Function to setup auto-renewal for SSL
setup_ssl_renewal() {
    print_status "Setting up SSL certificate auto-renewal..."
    
    # Create renewal script
    cat << 'EOF' > /etc/cron.daily/renew-ssl
#!/bin/bash
certbot renew --quiet --post-hook "docker-compose -f /opt/gateway-dashboard/docker-compose.yml restart nginx"
EOF
    
    chmod +x /etc/cron.daily/renew-ssl
    
    print_success "SSL auto-renewal configured"
}

# Function to show installation summary
show_summary() {
    echo ""
    echo "======================================="
    echo "Gateway Pro Dashboard Installation Complete!"
    echo "======================================="
    echo ""
    echo "Dashboard Details:"
    echo "  URL: https://$DOMAIN"
    echo "  Installation Directory: $INSTALL_DIR"
    echo "  SSL Certificate: Let's Encrypt"
    echo ""
    echo "Service Status:"
    echo "  nginx: $(systemctl is-active nginx)"
    echo "  Docker: $(systemctl is-active docker)"
    echo ""
    echo "Container Status:"
    docker-compose -f "$INSTALL_DIR/docker-compose.yml" ps
    echo ""
    echo "Next Steps:"
    echo "  1. Visit https://$DOMAIN to access the dashboard"
    echo "  2. Configure FastSpring credentials in $INSTALL_DIR/.env"
    echo "  3. Restart containers: cd $INSTALL_DIR && docker-compose restart"
    echo ""
    echo "FastSpring Setup:"
    if [[ -z "$FASTSPRING_USERNAME" ]]; then
        echo "  - Add VITE_FASTSPRING_USERNAME to .env"
        echo "  - Add VITE_FASTSPRING_PASSWORD to .env"
        echo "  - Add VITE_FASTSPRING_STOREFRONT to .env"
    else
        echo "  ✓ FastSpring credentials configured"
    fi
    echo ""
    echo "Commands:"
    echo "  View logs: cd $INSTALL_DIR && docker-compose logs -f"
    echo "  Restart: cd $INSTALL_DIR && docker-compose restart"
    echo "  Update: cd $INSTALL_DIR && git pull && docker-compose up -d --build"
    echo ""
    echo "Support:"
    echo "  Documentation: https://github.com/yourusername/gateway-dashboard"
    echo "  Issues: https://github.com/yourusername/gateway-dashboard/issues"
    echo ""
}

# Main execution
main() {
    print_status "Starting Gateway Pro Dashboard Installation..."
    
    # Parse arguments
    parse_args "$@"
    
    # Validate required parameters
    if [[ -z "$DOMAIN" ]]; then
        print_error "Domain is required. Use --domain=your-domain.com"
    fi
    
    if [[ -z "$EMAIL" ]]; then
        print_error "Email is required. Use --email=admin@your-domain.com"
    fi
    
    # Check if running as root
    check_root
    
    # Detect OS and install dependencies
    detect_os
    install_dependencies
    
    # Setup firewall
    setup_firewall
    
    # Clone repository
    clone_repository
    
    # Setup environment
    setup_environment
    
    # Setup SSL certificates
    setup_ssl
    
    # Configure nginx
    configure_nginx
    
    # Deploy application
    deploy_application
    
    # Setup SSL auto-renewal
    setup_ssl_renewal
    
    # Start nginx
    systemctl enable nginx
    systemctl start nginx
    
    # Show summary
    show_summary
}

# Run main function with all arguments
main "$@"