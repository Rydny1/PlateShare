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