# Contributing to Ritha

Thank you for considering contributing to Ritha! We welcome contributions from everyone.

## 🤝 How to Contribute

### 1. Fork the Repository
Click the "Fork" button at the top right of this repository to create your own copy.

### 2. Clone Your Fork
```bash
git clone https://github.com/YOUR_USERNAME/ritha.git
cd ritha
```

### 3. Create a Feature Branch
```bash
git checkout -b feature/amazing-feature
```

### 4. Make Your Changes
- Follow the existing code style and conventions
- Write clear, descriptive commit messages
- Add tests for new features
- Update documentation as needed

#### If your change touches the public API
The `backend/openapi.yaml` schema feeds typed clients on web (TypeScript) and
mobile (Dart). After changing any DRF serializer or view, regenerate everything
with one command from `backend/`:

```bash
make codegen
```

This runs three steps:
1. `manage.py spectacular --file openapi.yaml` — refreshes the schema
2. `npm run gen:api` in `frontend/` — writes `src/api/generated/schema.d.ts`
3. `tool/gen_api.sh` in `mobile_flutter/` — writes Dart models to `lib/api/generated/`

**Commit all three** outputs together. CI does not regenerate; reviewers should
see the API surface diff in the PR.

To type-check the frontend against the new schema: `cd frontend && npm run check:api`.

### 5. Test Your Changes
```bash
# Run backend tests
cd backend
python -m pytest

# Run web frontend tests (Playwright)
cd ../frontend
npm test

# Run mobile tests
cd ../mobile_flutter
flutter test
```

### 6. Commit and Push
```bash
git add .
git commit -m "Add amazing feature"
git push origin feature/amazing-feature
```

### 7. Create a Pull Request
- Go to your fork on GitHub
- Click "New Pull Request"
- Fill out the PR template
- Submit for review

## 📋 Pull Request Guidelines

### PR Template
```markdown
## Summary
Brief description of the changes

## Test plan
[ ] I have tested these changes locally
[ ] I have run the test suite
[ ] I have updated documentation

## Screenshots (if applicable)
[Add screenshots showing the changes]

## Additional Notes
[Any additional information for reviewers]
```

### Review Process
- All PRs require at least one review before merging
- We may request changes before approval
- Please be patient and responsive to feedback

## 🐛 Reporting Issues

### Bug Reports
When reporting bugs, please include:
- Steps to reproduce the issue
- Expected behavior vs. actual behavior
- Your operating system and browser
- Any error messages or logs
- Screenshots if applicable

### Feature Requests
For new features, please:
- Check if the feature already exists
- Provide a clear description of the feature
- Explain why this feature would be valuable
- Include any relevant mockups or examples

## 🏗️ Development Guidelines

### Code Style
- Follow PEP 8 for Python code
- Use TypeScript for frontend development
- Maintain consistent naming conventions
- Write clear, descriptive variable names

### Testing
- Write unit tests for new features
- Ensure tests are fast and reliable
- Use meaningful test names
- Test edge cases and error conditions

### Documentation
- Update README.md for major changes
- Add inline comments for complex logic
- Document new API endpoints
- Keep examples up to date

## 🎯 Project Structure

### Backend (`/backend`)
- `api/` - REST API endpoints
- `agents/` - AI agent implementations
- `models/` - Database models
- `services/` - Business logic services
- `utils/` - Utility functions

### Frontend (`/frontend`)
- React 18 + Vite web app

### Mobile (`/mobile_flutter`)
- Flutter 3 / Dart 3 mobile app

### Testing
- `/backend/tests` — pytest suites for the Django backend
- `/frontend/tests` — Playwright end-to-end tests for the web app
- `/mobile_flutter/test` — Dart widget/unit tests

## 🔧 Setting Up for Development

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- Docker (optional)

### Setup Instructions
1. Fork and clone the repository
2. Install dependencies:
   ```bash
   # Backend
   cd backend
   pip install -r requirements.txt

   # Web frontend
   cd ../frontend
   npm install

   # Mobile app
   cd ../mobile_flutter
   flutter pub get
   ```
3. Set up environment variables (see `.env.example`)
4. Run database migrations
5. Start development servers

## 🤖 AI Development Guidelines

### Agent Development
- Follow the existing agent patterns in `backend/agents/services.py`
- Call Mistral via `backend/ritha/services/mistral_client.py`
- Implement proper error handling and stub fallbacks for missing API keys
- Add logging for debugging

### Model Integration
- Use environment variables for API keys
- Implement caching where appropriate
- Handle rate limiting gracefully
- Provide fallback mechanisms

## 🛡️ Security Guidelines

### Data Privacy
- Never commit API keys or secrets
- Use environment variables for sensitive data
- Follow Swiss data protection regulations
- Implement proper authentication

### Code Security
- Validate all user inputs
- Use parameterized queries to prevent SQL injection
- Implement proper authorization checks
- Keep dependencies up to date

## 📞 Getting Help

- **Discussions**: Use GitHub Discussions for questions
- **Issues**: Report bugs and feature requests
- **Email**: dev@getritha.com
- **Slack**: Join our developer community

## 🙏 Code of Conduct

We are committed to providing a welcoming and inclusive environment for all contributors. Please be respectful in all interactions and follow our code of conduct.

## 📄 License

By contributing to this project, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing to Ritha!** 🎉