# EZRealtor.app 🏠

**Multi-tenant SaaS platform for real estate agents with AI-powered lead capture and processing**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-ezrealtor.app-blue)](https://ezrealtor.app)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=flat&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Stripe](https://img.shields.io/badge/Stripe-626CD9?style=flat&logo=Stripe&logoColor=white)](https://stripe.com)

## 🚀 Features

### 🤖 AI-Powered Lead Processing
- **Intelligent Lead Capture**: AI analyzes and processes incoming leads
- **Automated Follow-up**: Smart email sequences and SMS campaigns
- **Lead Scoring**: AI-driven lead qualification and prioritization
- **Multi-channel Integration**: Phone, email, and web form capture

### 🎨 Agent Customization System
- **15+ Branding Options**: Colors, logos, fonts, and styling
- **Custom Domains**: Subdomain routing (agent.ezrealtor.app)
- **Personalized Templates**: Branded lead capture pages
- **Professional Profiles**: Agent photos, bios, and contact info

### 💳 Complete Billing Integration
- **Stripe Payments**: Secure subscription billing
- **Multiple Plans**: Trial, Booster ($97), Pro ($297)
- **Webhook Processing**: Real-time subscription updates
- **Customer Portal**: Self-service billing management

### 🏢 Multi-Tenant Architecture
- **Isolated Data**: Complete tenant separation
- **Subdomain Routing**: Custom agent subdomains
- **Scalable Design**: Handles unlimited agents
- **SSL Security**: Let's Encrypt certificates

## 🛠️ Technology Stack

### Backend
- **FastAPI**: Modern Python web framework
- **PostgreSQL**: Robust relational database
- **SQLAlchemy 2.0**: Advanced ORM with async support
- **Alembic**: Database migration management

### AI & Integrations
- **OpenAI GPT**: Advanced text processing and generation
- **Twilio**: SMS and voice communications
- **Brevo**: Email marketing automation
- **Google OAuth**: Secure authentication
- **Foursquare**: Location services
- **USPS**: Address validation
- **MapTiler**: Mapping and geocoding

### Infrastructure
- **Nginx**: Reverse proxy and load balancing
- **Ubuntu 22.04**: Production server environment
- **SSL/TLS**: Let's Encrypt certificate automation
- **Systemd**: Service management and monitoring

### Frontend
- **Bootstrap 5**: Responsive UI framework
- **FontAwesome**: Professional iconography
- **Jinja2**: Server-side templating
- **JavaScript**: Interactive client-side features

## 📋 Installation

### Prerequisites
- Python 3.9+
- PostgreSQL 14+
- Node.js (for asset building)
- SSL certificate (Let's Encrypt)

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/pgwilde8/ezrealtorapp.git
   cd ezrealtorapp
   ```

2. **Set up virtual environment**
   ```bash
   cd ezadmin
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and database credentials
   ```

4. **Initialize database**
   ```bash
   ./setup_db.sh
   alembic upgrade head
   ```

5. **Start the application**
   ```bash
   ./start_server.sh
   ```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the `ezadmin` directory:

```env
# Database
DATABASE_URL=postgresql://username:password@localhost/ezrealtor

# Stripe
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# OpenAI
OPENAI_API_KEY=sk-...

# Twilio
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+1...

# Brevo (Email)
BREVO_API_KEY=xkeysib-...

# Google OAuth
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...

# Other APIs
FOURSQUARE_API_KEY=...
USPS_API_KEY=...
MAPTILER_API_KEY=...
```

### Stripe Price IDs

Update billing configuration with your Stripe price IDs:

```python
# In app/api/billing.py
STRIPE_PRICES = {
    "trial": "price_free",
    "booster": "price_1SHlyqRzRv6CTjxRuoNxsMt6",  # $97/month
    "pro": "price_1SHlz5RzRv6CTjxRhQXXXXXX"      # $297/month
}
```

## 🚀 Deployment

### Production Setup

1. **Configure Nginx**
   ```bash
   sudo cp nginx/ezrealtor.conf /etc/nginx/sites-available/
   sudo ln -s /etc/nginx/sites-available/ezrealtor.conf /etc/nginx/sites-enabled/
   sudo nginx -t && sudo systemctl reload nginx
   ```

2. **Set up SSL with Let's Encrypt**
   ```bash
   sudo certbot --nginx -d ezrealtor.app -d *.ezrealtor.app
   ```

3. **Install systemd service**
   ```bash
   sudo cp systemd/ezrealtor.service /etc/systemd/system/
   sudo systemctl enable ezrealtor
   sudo systemctl start ezrealtor
   ```

4. **Configure firewall**
   ```bash
   sudo ufw allow 'Nginx Full'
   sudo ufw allow 8011:8013/tcp
   ```

## 📊 Database Schema

### Core Models

- **Agent**: User profiles with customization settings
- **Lead**: Captured prospect information
- **CapturePages**: Landing page configurations
- **Domain**: Custom domain management
- **Usage**: Billing and usage tracking
- **Notifications**: System alerts and messages

### Customization Fields

- Colors (primary, secondary, accent)
- Typography (fonts, sizes)
- Logos and branding assets
- Contact information
- Social media links
- Custom messaging

## 🔧 API Endpoints

### Public APIs
- `POST /api/leads/capture` - Lead capture webhook
- `GET /api/agents/{subdomain}` - Agent profile lookup
- `POST /api/stripe/webhook` - Stripe event processing

### Agent APIs
- `GET /api/agents/me` - Current agent profile
- `PUT /api/agents/customize` - Update customization
- `GET /api/leads` - List agent leads
- `POST /api/billing/checkout` - Create checkout session

### Admin APIs
- `GET /api/admin/dashboard` - System metrics
- `GET /api/admin/tenants` - Tenant management
- `POST /api/admin/plans` - Plan configuration

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app

# Load test
locust -f tests/load_test.py
```

## 📈 Monitoring

- **Health Checks**: `/health` endpoint
- **Metrics**: Prometheus-compatible metrics
- **Logging**: Structured JSON logs
- **Alerts**: Email notifications for critical events

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [docs.ezrealtor.app](https://docs.ezrealtor.app)
- **Email**: support@ezrealtor.app
- **Issues**: [GitHub Issues](https://github.com/pgwilde8/ezrealtorapp/issues)

## 🔄 Changelog

### v1.0.0 (2024-10-13)
- Initial release
- AI-powered lead capture
- Agent customization system
- Stripe billing integration
- Multi-tenant architecture
- SSL-secured domain

---

**Built with ❤️ by the EZRealtor team**