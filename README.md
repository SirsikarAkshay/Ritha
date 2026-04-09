# Arokah: AI Style Companion

🌍 **Your AI-Powered Personal Stylist — For Every Day and Every Destination**

Arokah is an intelligent style companion that knows your wardrobe, your calendar, the weather, and where you're going — whether that's the office tomorrow or Tokyo next month. Built with cutting-edge agentic AI and Swiss data privacy standards.

---

## ✨ Features

### 🧠 The Intelligence Core (Agentic Assistant)

The heart of Arokah is a unified recommendation engine that combines four signals into one smart suggestion, every morning:

```
Calendar → knows your day
Weather  → knows your conditions
Wardrobe → knows what you own
Culture  → knows where you're going
              ↓
  One smart suggestion, every morning
```

- **Calendar-Driven Outfit Engine**: Syncs with Google Calendar and Outlook to understand your full day — meetings, workouts, dinners, travel, or nothing at all — and recommends outfits accordingly
- **Smart Event Parsing**: Infers formality and context from natural calendar language (e.g. "coffee w/ Sarah" → casual-smart; "board review" → polished; "spin class" → activewear)
- **Multi-Context Day Solver**: Plans outfit transitions for complex days (e.g. *"You have a client lunch and a gym class — here's one outfit with a layer swap"*)
- **Conflict Resolver**: Detects mismatches between activity and conditions (e.g. *"You planned a hike, but there's a 90% chance of a thunderstorm — should I suggest indoor gear instead?"*)
- **Manual Event Builder**: Natural language entry for events not on your calendar (e.g. *"I'm going to a wedding on the 14th in a garden"*)
- **Luggage Weight Predictor**: Estimates total bag weight based on item materials (denim vs. silk) to avoid airline fees

### 📅 Daily Looks

Arokah isn't just for trips — it's your everyday stylist for anyone who doesn't want to spend mental energy on getting dressed.

| Event Type | What Arokah Suggests |
|---|---|
| External meeting / client | Smart, polished |
| Internal standup | Casual-smart |
| Gym / workout | Activewear |
| Social / dinner | Context-dependent |
| Nothing scheduled | Full comfort |
| Travel day | Practical + airport-friendly |

- **Morning Outfit Notification**: A "Today's Look" push notification each morning, built around your actual schedule and real weather
- **Wear-Again Intelligence**: Tracks what you've worn recently to avoid repetition
- **Style Learning**: Improves suggestions over time based on what you accept, skip, or modify

### 👗 The Wardrobe Layer

- **Receipt-to-Closet Import**: Forward shopping emails to auto-populate your digital closet (images + metadata)
- **AI Background Removal**: Snap a photo of a garment; the AI cleans it for a professional lookbook
- **The 5-4-3-2-1 Capsule Logic**: Automatically creates a mix-and-match outfit grid for the entire duration of a trip
- **Fast Onboarding**: Start with as few as 10 items to get your first smart suggestion immediately

### 🌐 The Cultural & Event Compass

- **Etiquette Radar**: Contextual warnings for specific destinations (e.g. *"Headscarf required for the Blue Mosque"* or *"Knees/shoulders must be covered for the Vatican"*)
- **Social Vibe Analysis**: Checks Instagram/TikTok tags for your hotel or restaurant to suggest the local style so you don't look like a tourist
- **Hyper-Local Event Scout**: Automatically flags special clothing requirements for festivals during your stay (e.g. *"It's Holi — pack clothes you don't mind getting stained"*)

### 🌱 Sustainability & Contribution

- **CO₂ Weight Savings Tracker**: Calculates carbon saved by keeping luggage light (less plane fuel) and switching to carry-on
- **"Wear-Again" Rewards**: Gamifies re-wearing clothes instead of buying new ones for every trip
- **Eco-Shop Integration**: When a user needs a new item, the app prioritizes sustainable and rental brands (e.g. Rent the Runway, Patagonia)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- Docker (optional, for containerized deployment)

### Installation

#### Backend Setup
```bash
# Clone the repository
git clone https://github.com/your-username/arokah.git
cd arokah

# Set up Python environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys and database settings
```

#### Frontend Setup
```bash
# Mobile App (React Native)
cd frontend/mobile
npm install

# Web App (React)
cd ../web
npm install
```

#### Database Setup
```bash
# Start PostgreSQL
# Create database and run migrations
python manage.py migrate
```

### Configuration

Create a `.env` file with the following variables:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/arokah

# AI Services
OPENAI_API_KEY=your_openai_key
GOOGLE_CALENDAR_API_KEY=your_google_calendar_key
GOOGLE_VISION_API_KEY=your_google_vision_key

# Cloud Storage
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_REGION=eu-central-1  # Swiss region

# Frontend URLs
WEB_APP_URL=http://localhost:3000
MOBILE_APP_URL=http://localhost:8081

# Security
SECRET_KEY=your_secret_key_here
JWT_SECRET=your_jwt_secret
```

### Running the Application

#### Development Mode
```bash
# Start backend API
cd backend
python app.py

# Start web frontend
cd ../frontend/web
npm start

# Start mobile app
cd ../mobile
npm start
```

#### Docker Compose (Recommended)
```bash
docker-compose up -d
```

---

## 🏗️ Architecture

### Tech Stack
- **Backend**: Python + FastAPI
- **AI Orchestration**: LangChain + CrewAI
- **Database**: PostgreSQL with encrypted storage
- **Frontend**: React Native (Mobile) + React (Web)
- **AI Models**: OpenAI API + Local Llama 3 models
- **Cloud**: Swiss-based providers (Swisscom, Leaseweb)

### Project Structure
```
arokah/
├── backend/
│   ├── api/                # REST API endpoints
│   ├── agents/             # AI agent implementations
│   ├── models/             # Database models
│   ├── services/           # Business logic services
│   └── utils/              # Utility functions
├── frontend/
│   ├── mobile/             # React Native mobile app
│   └── web/                # React web app
├── docs/
├── tests/
└── scripts/
```

---

## 🔧 API Endpoints

### Core Endpoints
- `POST /api/auth/login` — User authentication
- `GET /api/itinerary` — Get user itinerary
- `POST /api/itinerary/sync` — Sync calendar events
- `GET /api/wardrobe` — Get user wardrobe
- `POST /api/wardrobe/upload` — Upload clothing item
- `GET /api/outfits/daily` — Get today's outfit recommendation
- `GET /api/outfits/recommendations` — Get outfit recommendations for a trip
- `GET /api/cultural/etiquette` — Get cultural etiquette for destination
- `GET /api/sustainability/tracker` — Get sustainability metrics

### AI Agent Endpoints
- `POST /api/agents/daily-look` — Generate today's outfit based on calendar + weather
- `POST /api/agents/packing-list` — Generate packing list for a trip
- `POST /api/agents/outfit-planner` — Plan outfits for full trip duration
- `POST /api/agents/cultural-advisor` — Get cultural clothing advice
- `POST /api/agents/conflict-detector` — Detect schedule/weather/outfit conflicts

---

## 🎯 Development Roadmap

### Phase 1: Daily Look MVP (Months 1-3)
- [ ] Core infrastructure setup
- [ ] Google Calendar + Outlook integration
- [ ] Weather intelligence
- [ ] Event type classification engine
- [ ] Morning push notification with daily outfit
- [ ] Basic wardrobe onboarding (10-item fast start)

### Phase 2: Visual Wardrobe (Months 4-6)
- [ ] Full wardrobe digitization
- [ ] AI styling engine
- [ ] Capsule outfit recommendations
- [ ] Wear-again tracking and rewards

### Phase 3: Travel & Cultural Intelligence (Months 7-9)
- [ ] Trip mode with extended calendar horizon
- [ ] Cultural etiquette database
- [ ] Social vibe analysis
- [ ] Hyper-local event intelligence
- [ ] Luggage weight predictor

### Phase 4: Impact & Commerce (Months 10-12)
- [ ] Sustainability dashboard
- [ ] Eco-commerce integration
- [ ] Monetization features
- [ ] Full launch

---

## 🛡️ Data Privacy & Security

### Swiss Compliance
- All user data stored in Switzerland
- AES-256 encryption at rest and in transit
- OAuth 2.0 with 2FA support
- Minimal data collection
- User-controlled data deletion
- Regular security audits

### Privacy Features
- Granular user consent for all calendar and wardrobe data
- Right to erasure implementation
- Data minimization principles
- Transparent data usage policies

---
## 🤖 AI Features

### Agentic Intelligence
- **Multi-Agent System**: Specialized agents for daily looks, travel planning, cultural guidance, and conflict detection
- **Context-Aware Recommendations**: AI understands your schedule, preferences, and environment simultaneously
- **Learning System**: Improves recommendations based on what you accept, skip, or modify
- **Real-time Adaptation**: Adjusts suggestions when your calendar or weather changes

### Computer Vision
- **Background Removal**: Professional-quality garment image processing
- **Item Recognition**: Automatic clothing item identification and tagging
- **Style Analysis**: AI-powered style and formality assessment
- **Color Matching**: Intelligent color coordination across outfits

---

## 🌱 Sustainability Features

### Carbon Tracking
- **CO₂ Calculator**: Real-time carbon footprint tracking for luggage weight
- **Weight Optimization**: Packing recommendations to minimize bag weight
- **Transport Impact**: Flight vs. train carbon comparison
- **Offset Suggestions**: Carbon offset opportunities

### Ethical Shopping
- **Sustainable Brands**: Prioritized product recommendations
- **Rental Integration**: Access to clothing rental services
- **Second-hand Options**: Thrift store and consignment suggestions
- **Local Shopping**: Support for local, sustainable businesses

---

## 📱 Screenshots

[Add screenshots here showing the app interface]

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## 📞 Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/your-username/arokah/issues)
- **Email**: support@arokah.com
- **Website**: [arokah.com](https://arokah.com)

---

**Arokah** — Dress for your day. Every day. 🌍✨