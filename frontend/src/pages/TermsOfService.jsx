// Public Terms of Service page (no auth). Linked from the login screen.
//
// ⚠️ DRAFT — pending review by legal counsel before launch. Entity name and
// effective date are filled in; still TODO: the [REGISTERED ADDRESS] placeholder,
// and a lawyer's review (especially liability and governing law).
import { Link } from 'react-router-dom'
import Logo from '../components/Logo.jsx'

const wrap = { maxWidth: 820, margin: '0 auto', padding: '40px 24px 80px', color: 'var(--cream)', lineHeight: 1.7 }
const h2 = { color: 'var(--terra-light)', marginTop: 36, marginBottom: 8, fontSize: '1.25rem' }
const muted = { color: 'var(--cream-dim)', fontSize: '0.9rem' }

export default function TermsOfService() {
  return (
    <div style={{ minHeight: '100vh', background: 'var(--midnight)' }}>
      <div style={wrap}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
          <Logo />
          <Link to="/login" style={{ color: 'var(--terra-light)', textDecoration: 'none', fontSize: '0.9rem' }}>← Back</Link>
        </div>

        <h1 style={{ fontSize: '1.8rem', marginBottom: 4 }}>Terms of Service</h1>
        <p style={muted}>Effective date: 2 June 2026 · Last updated: 2 June 2026</p>

        <p style={{ background: 'rgba(200,120,80,0.12)', border: '1px solid var(--terra)', borderRadius: 8, padding: '12px 16px', marginTop: 16, fontSize: '0.9rem' }}>
          <strong>Draft notice:</strong> This document is a working draft pending review by legal counsel. It is not yet a binding agreement.
        </p>

        <h2 style={h2}>1. Acceptance</h2>
        <p>
          These Terms govern your use of the Ritha web and mobile applications (the “Service”), operated by
          <strong> Ritha GmbH</strong>, [REGISTERED ADDRESS]. By creating an account or using the Service, you
          agree to these Terms and to our <Link to="/privacy" style={{ color: 'var(--terra-light)' }}>Privacy Policy</Link>.
        </p>

        <h2 style={h2}>2. Your account</h2>
        <p>
          You must provide accurate information, keep your credentials secure, and are responsible for activity under
          your account. You must be at least 16 years old to use the Service.
        </p>

        <h2 style={h2}>3. Acceptable use</h2>
        <p>You agree not to misuse the Service, including: violating laws; infringing others’ rights; uploading content
          you don’t have rights to; attempting to disrupt, reverse-engineer, or gain unauthorised access; or harassing
          other users via social/messaging features.</p>

        <h2 style={h2}>4. Your content</h2>
        <p>
          You retain ownership of the photos and content you upload. You grant us a limited licence to host and process
          that content solely to operate and improve the Service for you (e.g. to generate recommendations). You are
          responsible for the content you upload.
        </p>

        <h2 style={h2}>5. AI recommendations — no warranty</h2>
        <p>
          Ritha’s outfit, packing, cultural, and weather guidance is generated algorithmically and with AI, and is
          provided for convenience only. It may be inaccurate or incomplete. It is <strong>not</strong> professional
          advice. You are responsible for your own decisions; always verify weather, cultural, and travel information
          from authoritative sources.
        </p>

        <h2 style={h2}>6. Third-party services</h2>
        <p>
          The Service integrates third parties (e.g. Google/Microsoft/Apple calendars, weather and AI providers). Your
          use of those is subject to their terms, and we are not responsible for them.
        </p>

        <h2 style={h2}>7. Limitation of liability</h2>
        <p>
          To the maximum extent permitted by law, the Service is provided “as is” without warranties, and
          Ritha GmbH is not liable for indirect, incidental, or consequential damages, or for any reliance on
          AI-generated recommendations.
        </p>

        <h2 style={h2}>8. Termination</h2>
        <p>
          You may stop using the Service and delete your account at any time. We may suspend or terminate access for
          breach of these Terms or to protect the Service.
        </p>

        <h2 style={h2}>9. Governing law &amp; changes</h2>
        <p>
          These Terms are governed by the laws of Switzerland, without regard to conflict-of-law rules. We may update
          these Terms; we will post changes here and update the date. Continued use after changes constitutes acceptance.
        </p>

        <h2 style={h2}>10. Contact</h2>
        <p>
          Questions about these Terms? Contact <strong>Ritha GmbH</strong> at
          <a href="mailto:legal@getritha.com" style={{ color: 'var(--terra-light)' }}> legal@getritha.com</a>.
        </p>
      </div>
    </div>
  )
}
