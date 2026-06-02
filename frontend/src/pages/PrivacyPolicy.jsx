// Public Privacy Policy page (no auth). Linked from the login screen and used
// as the privacy URL for Google/Microsoft OAuth verification.
//
// ⚠️ DRAFT — pending review by legal counsel before launch. Replace the
// [LEGAL ENTITY NAME] / [REGISTERED ADDRESS] placeholders and the effective
// date, and confirm wording with a lawyer for GDPR / Swiss FADP compliance.
import { Link } from 'react-router-dom'
import Logo from '../components/Logo.jsx'

const wrap = { maxWidth: 820, margin: '0 auto', padding: '40px 24px 80px', color: 'var(--cream)', lineHeight: 1.7 }
const h2 = { color: 'var(--terra-light)', marginTop: 36, marginBottom: 8, fontSize: '1.25rem' }
const muted = { color: 'var(--cream-dim)', fontSize: '0.9rem' }

export default function PrivacyPolicy() {
  return (
    <div style={{ minHeight: '100vh', background: 'var(--midnight)' }}>
      <div style={wrap}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
          <Logo />
          <Link to="/login" style={{ color: 'var(--terra-light)', textDecoration: 'none', fontSize: '0.9rem' }}>← Back</Link>
        </div>

        <h1 style={{ fontSize: '1.8rem', marginBottom: 4 }}>Privacy Policy</h1>
        <p style={muted}>Effective date: __________ · Last updated: __________</p>

        <p style={{ background: 'rgba(200,120,80,0.12)', border: '1px solid var(--terra)', borderRadius: 8, padding: '12px 16px', marginTop: 16, fontSize: '0.9rem' }}>
          <strong>Draft notice:</strong> This document is a working draft pending review by legal counsel. It is not yet a binding policy.
        </p>

        <p style={{ marginTop: 20 }}>
          This Privacy Policy explains how <strong>[LEGAL ENTITY NAME]</strong> (“Ritha”, “we”, “us”), based at
          [REGISTERED ADDRESS], collects, uses, and protects your personal data when you use the Ritha web and
          mobile applications (the “Service”). We act as the data controller. We comply with the EU General Data
          Protection Regulation (GDPR) and the Swiss Federal Act on Data Protection (FADP).
        </p>

        <h2 style={h2}>1. Data we collect</h2>
        <ul>
          <li><strong>Account data:</strong> email address, name, password (hashed), timezone.</li>
          <li><strong>Wardrobe data:</strong> clothing item photos you upload and their metadata (category, colour, material, brand, season).</li>
          <li><strong>Calendar data:</strong> with your explicit consent, calendar events from Google Calendar, Microsoft/Outlook, or Apple (CalDAV) — event titles, times, and locations — used to infer occasion and formality.</li>
          <li><strong>Travel &amp; location data:</strong> destinations and trip dates you enter (geocoded to coordinates to fetch weather). We do not track your device location in the background.</li>
          <li><strong>Social data:</strong> profile handle/bio, connections, and messages, if you use those features.</li>
          <li><strong>Sustainability &amp; usage data:</strong> outfit acceptance/feedback, wear logs, and sustainability actions.</li>
          <li><strong>Technical data:</strong> push-notification (FCM) tokens, and standard logs (IP, device/browser) for security and reliability.</li>
        </ul>

        <h2 style={h2}>2. How we use your data &amp; legal bases</h2>
        <ul>
          <li><strong>To provide the Service</strong> (outfit recommendations, packing lists, cultural guidance) — performance of our contract with you.</li>
          <li><strong>To personalise recommendations</strong> from your feedback — our legitimate interest / your consent.</li>
          <li><strong>To send transactional email and notifications</strong> — performance of contract; marketing only with consent.</li>
          <li><strong>To secure the Service and prevent abuse</strong> — legitimate interest and legal obligation.</li>
        </ul>

        <h2 style={h2}>3. Google Calendar data — Limited Use</h2>
        <p>
          When you connect Google Calendar, we request the minimum scopes <code>calendar.readonly</code> (to read your
          upcoming events and infer occasion/formality for outfit suggestions) and <code>userinfo.email</code> (to
          identify the connected account). Ritha’s use of information received from Google APIs adheres to the
          <a href="https://developers.google.com/terms/api-services-user-data-policy" style={{ color: 'var(--terra-light)' }}> Google API Services User Data Policy</a>,
          including the Limited Use requirements. Specifically, we <strong>do not</strong> sell this data, use it for
          advertising, allow humans to read it (except for security/abuse or with your consent or as required by law),
          or use it to train generalized AI/ML models. Calendar data is used solely to provide the user-facing
          features described above. The same principles apply to Microsoft and Apple calendar data.
        </p>

        <h2 style={h2}>4. Third-party processors</h2>
        <p>We share data only with service providers who process it on our behalf under contract:</p>
        <ul>
          <li><strong>Mistral AI</strong> — analyses wardrobe photos, receipts, and text to generate styling/cultural guidance.</li>
          <li><strong>Open-Meteo</strong> — weather and geocoding (destination text only; no personal identifiers).</li>
          <li><strong>Google, Microsoft, Apple</strong> — calendar integrations you connect.</li>
          <li><strong>Firebase Cloud Messaging</strong> — delivers push notifications.</li>
          <li><strong>Our email/SMTP provider</strong> — sends verification and account emails.</li>
          <li><strong>Our hosting provider</strong> — runs the Service infrastructure.</li>
        </ul>

        <h2 style={h2}>5. Retention</h2>
        <p>
          We keep your data while your account is active. You can delete individual items at any time, and deleting
          your account permanently removes your personal data, subject to limited retention required by law or for
          security. Disconnecting a calendar stops further syncing and removes the stored access tokens.
        </p>

        <h2 style={h2}>6. Your rights</h2>
        <p>
          Subject to GDPR/FADP, you may access, correct, export, restrict, or delete your data, and object to certain
          processing. The Service provides in-app <strong>account deletion</strong> and <strong>data export</strong>.
          To exercise other rights, contact us at <a href="mailto:privacy@getritha.com" style={{ color: 'var(--terra-light)' }}>privacy@getritha.com</a>.
          You may also lodge a complaint with your local supervisory authority (or the Swiss FDPIC).
        </p>

        <h2 style={h2}>7. International transfers</h2>
        <p>
          Some processors may process data outside your country. Where required, transfers are protected by adequacy
          decisions or Standard Contractual Clauses.
        </p>

        <h2 style={h2}>8. Children</h2>
        <p>The Service is not directed at children under 16, and we do not knowingly collect their data.</p>

        <h2 style={h2}>9. Changes &amp; contact</h2>
        <p>
          We will post any changes here and update the “Last updated” date. Questions? Contact
          <strong> [LEGAL ENTITY NAME]</strong> at <a href="mailto:privacy@getritha.com" style={{ color: 'var(--terra-light)' }}>privacy@getritha.com</a>.
        </p>

        <p style={{ ...muted, marginTop: 32 }}>
          See also our <Link to="/terms" style={{ color: 'var(--terra-light)' }}>Terms of Service</Link>.
        </p>
      </div>
    </div>
  )
}
