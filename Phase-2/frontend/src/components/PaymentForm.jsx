/**
 * PaymentForm
 * ===========
 * Shown after a booking is created (pending_payment).
 * Wraps the Stripe PaymentElement — handles card entry and submission.
 *
 * Props:
 *   clientSecret   – Stripe PaymentIntent client secret
 *   total          – display amount (number)
 *   ticketCode     – shown after success
 *   expiresAt      – ISO datetime string; countdown shown to user
 *   onSuccess()    – called when payment is confirmed by Stripe
 *   onCancel()     – called when user clicks "Cancel"
 */

import { useState, useEffect } from 'react';
import { loadStripe } from '@stripe/stripe-js';
import { Elements, PaymentElement, useStripe, useElements } from '@stripe/react-stripe-js';
import { api } from '../api.js';

// ── Stripe promise (fetched once from backend) ────────────────────────────────
let _stripePromise = null;
async function getStripePromise() {
  if (_stripePromise) return _stripePromise;
  const { publishable_key } = await api.stripeConfig();
  _stripePromise = loadStripe(publishable_key);
  return _stripePromise;
}

// ── Inner form (must be inside <Elements>) ────────────────────────────────────
function CheckoutForm({ total, ticketCode, expiresAt, onSuccess, onCancel }) {
  const stripe   = useStripe();
  const elements = useElements();
  const [error, setBusy] = useState('');
  const [busy,  setB   ] = useState(false);
  const [secondsLeft, setSecondsLeft] = useState(null);

  // Countdown timer
  useEffect(() => {
    if (!expiresAt) return;
    const end = new Date(expiresAt).getTime();
    function tick() {
      const diff = Math.max(0, Math.floor((end - Date.now()) / 1000));
      setSecondsLeft(diff);
      if (diff === 0) onCancel();  // auto-cancel when expired
    }
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [expiresAt, onCancel]);

  const mmss = secondsLeft != null
    ? `${String(Math.floor(secondsLeft / 60)).padStart(2, '0')}:${String(secondsLeft % 60).padStart(2, '0')}`
    : null;

  async function handleSubmit(e) {
    e.preventDefault();
    if (!stripe || !elements) return;
    setB(true); setBusy('');

    const { error: stripeError, paymentIntent } = await stripe.confirmPayment({
      elements,
      redirect: 'if_required',
    });

    if (stripeError) {
      setBusy(stripeError.message);
      setB(false);
    } else if (paymentIntent?.status === 'succeeded') {
      onSuccess({ ticketCode, total });
    } else {
      setBusy('Payment could not be completed. Please try again.');
      setB(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} style={{ maxWidth: 480 }}>
      <h2 style={{ marginBottom: 4 }}>Complete your payment</h2>
      <p className="muted" style={{ marginBottom: 16 }}>
        Ticket: <strong>{ticketCode}</strong> · Total:{' '}
        <strong>${Number(total).toFixed(2)}</strong>
        {mmss && (
          <span style={{ marginLeft: 12, color: secondsLeft < 60 ? '#e55' : undefined }}>
            ⏱ {mmss} remaining
          </span>
        )}
      </p>

      <PaymentElement />

      {error && <p className="error" style={{ marginTop: 12 }}>{error}</p>}

      <div style={{ display: 'flex', gap: 12, marginTop: 20 }}>
        <button type="submit" disabled={busy || !stripe} style={{ flex: 1 }}>
          {busy ? 'Processing…' : `Pay $${Number(total).toFixed(2)}`}
        </button>
        <button type="button" onClick={onCancel}
                style={{ background: 'transparent', color: '#888' }}>
          Cancel
        </button>
      </div>

      <p className="muted" style={{ marginTop: 12, fontSize: 12 }}>
        🔒 Payments are secured by Stripe. We never store your card details.
      </p>
    </form>
  );
}

// ── Public wrapper — loads Stripe asynchronously ──────────────────────────────
export default function PaymentForm(props) {
  const [stripePromise, setStripe] = useState(null);
  const [loadError,     setError ] = useState('');

  useEffect(() => {
    getStripePromise()
      .then(setStripe)
      .catch(() => setError('Could not load payment system. Please refresh the page.'));
  }, []);

  if (loadError) return <p className="error">{loadError}</p>;
  if (!stripePromise) return <p className="muted">Loading payment form…</p>;

  return (
    <Elements stripe={stripePromise} options={{ clientSecret: props.clientSecret }}>
      <CheckoutForm {...props} />
    </Elements>
  );
}
