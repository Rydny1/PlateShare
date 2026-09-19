# PlateShare

PlateShare is a small FastAPI backend for a school cafeteria WhatsApp bot.

## 1. Run locally

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload
```

Set values in `.env` before testing WhatsApp. Never commit `.env` or real tokens.

Check the app at <http://localhost:8000/health>. The expected response is:

```json
{"status":"ok"}
```

Environment variables belong in a local `.env` file or in the hosting provider's environment settings. Never commit real tokens, passwords, or database URLs.

## 2. Deploy to Render

Create or use a Render Web Service connected to this GitHub repository.

Build command:

```text
pip install -r requirements.txt
```

Start command:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

Add these environment variables in the Render Web Service settings:

```text
DATABASE_URL=<Render Internal Database URL>
WHATSAPP_PHONE_NUMBER_ID=<Meta phone number ID>
WHATSAPP_ACCESS_TOKEN=<Meta access token>
WHATSAPP_VERIFY_TOKEN=<a private value you choose>
WHATSAPP_GRAPH_API_VERSION=v26.0
APP_ENV=production
```

Use the Render Postgres Internal Database URL, not the external URL. Render may provide a `postgres://` URL; the application converts it automatically for SQLAlchemy.

After the first successful deploy, confirm:

```text
https://YOUR-RENDER-SERVICE.onrender.com/health
```

The response should be `{"status":"ok"}`. Database tables are created automatically at startup.

## 3. Configure the Meta webhook

In the Meta Developer dashboard, open the WhatsApp product for your app and find its Configuration or Webhooks section. Configure:

Callback URL:

```text
https://YOUR-RENDER-SERVICE.onrender.com/webhook
```

Verify token: the exact value used for `WHATSAPP_VERIFY_TOKEN` in Render.

Complete verification, then subscribe to the WhatsApp `messages` field. Meta must be able to reach the public HTTPS Render URL; `localhost` will not work for Meta callbacks.

## 4. Test the bot

Use a WhatsApp number allowed by the Meta test phone configuration. Send these commands in order:

```text
/register Bob Smith
/staff John Smith
/new Pizza - 10 slices
/offers
```

The staff number creates the offer. Registered student numbers receive an interactive `CLAIM` button. Clicking it creates one claim and decreases the remaining quantity atomically.

The dashboard is available at:

```text
https://YOUR-RENDER-SERVICE.onrender.com/dashboard
```

## 5. Messaging limitation

WhatsApp generally allows free-form replies during the customer-service window after a user messages the business. Proactive notifications outside that window may require an approved WhatsApp message template. For the hackathon, have test students message the Meta test number first and test within the allowed test-number/customer-service window.

## 6. Twilio WhatsApp Sandbox

The app also supports Twilio as a separate WhatsApp transport. Configure the Twilio Sandbox incoming-message webhook as:

```text
https://YOUR-RENDER-SERVICE.onrender.com/twilio/webhook
```

Add these variables to the Render Web Service:

```text
TWILIO_ACCOUNT_SID=<Twilio Account SID>
TWILIO_AUTH_TOKEN=<Twilio Auth Token>
TWILIO_WHATSAPP_NUMBER=whatsapp:<Twilio Sandbox number>
TWILIO_OFFER_CONTENT_SID=<Twilio Content Template SID with a URL button>
APP_BASE_URL=https://YOUR-RENDER-SERVICE.onrender.com
```

Join the Sandbox from each test phone using Twilio's join code. Then send normal WhatsApp text commands. The same commands and database behavior are used as the Meta route:

```text
/register Bob Smith
/staff John Smith
/new Pizza - 10 slices
/offers
claim:1
```

Twilio notifications include a clickable claim URL and also keep the text fallback `claim:1`. The link opens `/claim/1` and performs the same atomic claim operation. Set `APP_BASE_URL` to the public Render URL. The Meta webhook remains available at `/webhook`.

To use a native WhatsApp CTA URL button, create a Twilio Content Template with variables for description, remaining quantity, and the claim URL button. Copy its `HX...` Content SID into `TWILIO_OFFER_CONTENT_SID` on Render. The application sends variables as `1=description`, `2=remaining`, and `3=claim URL`. If this variable is empty, the application uses the plain-text clickable-link fallback.

For a Twilio trial demo, broadcasts to unverified student numbers can fail with Twilio error `572002`. A staff member can use this test-only command instead:

```text
/demo Pizza - 1 slice
```

It creates the offer and sends the announcement only back to the staff member who issued the command. The message includes `claim:ID`, which can be sent back to claim the offer. `/new` remains the normal broadcast command.

For testing role changes, use:

```text
/logout
```

This removes the test phone's registration and its claims so the same phone can then use `/register` or `/staff`.