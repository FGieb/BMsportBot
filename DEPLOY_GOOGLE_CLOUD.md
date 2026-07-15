# Deploy BMsportBot on Google Cloud (Free Forever)

Google Cloud gives you 1 free `e2-micro` VM per month — forever, not a trial.
That's more than enough for this bot. Cost: €0.

Total time: ~30 minutes.

---

## Step 1: Create a Google Cloud account

1. Go to **https://cloud.google.com/free**
2. Click **"Get started for free"**
3. Sign in with your Google account
4. Add a credit/debit card — **you won't be charged**, it's for verification
5. You'll get $300 trial credit (expires in 90 days) but you don't need it — the free VM is separate and permanent

---

## Step 2: Create a free VM

1. Go to **https://console.cloud.google.com/compute/instances**
   - If it asks you to enable the Compute Engine API, click **Enable** and wait a minute
2. Click **"Create Instance"**
3. Configure:
   - **Name**: `sportbot`
   - **Region**: pick one close to you, e.g. `europe-west4 (Netherlands)`
     - ⚠️ The free tier VM is only free in certain regions: `us-west1`, `us-central1`, `us-east1`. Pick **us-east1** to be safe (latency doesn't matter for a Telegram bot)
   - **Machine configuration**:
     - Series: **E2**
     - Machine type: **e2-micro** (this is the free one)
   - **Boot disk**: Click **Change**
     - Operating system: **Ubuntu**
     - Version: **Ubuntu 22.04 LTS**
     - Size: **30 GB** (free tier allows up to 30 GB)
     - Click **Select**
   - **Firewall**: leave unchecked (the bot only makes outbound connections)
4. Click **Create**
5. Wait ~1 minute for it to start

---

## Step 3: Connect to your VM

The easiest way — no SSH keys needed:

1. On the VM instances page, find your `sportbot` instance
2. Click the **"SSH"** button on the right side of the row
3. A browser terminal window opens — you're in!

(Alternatively, you can use `gcloud compute ssh sportbot` from your own terminal if you install the gcloud CLI.)

---

## Step 4: Install Python and the bot

In the SSH terminal, run these commands:

```bash
# Update the system
sudo apt update && sudo apt upgrade -y

# Install Python and git
sudo apt install -y python3 python3-pip python3-venv git

# Clone the bot
git clone https://github.com/FGieb/BMsportBot.git
cd BMsportBot

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Step 5: Add your API keys

```bash
nano sportbot.env
```

Paste your keys:

```
OPENWEATHER_API_KEY=your_key_here
WEATHERAPI_API_KEY=your_key_here
GROQ_API_KEY=your_key_here
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_IDS=martha:123456789,britt:987654321
```

Save: `Ctrl+X`, then `Y`, then `Enter`.

---

## Step 6: Quick test

```bash
python scripts/send_notification.py &
sleep 10
```

Go to Telegram and type `/help` to the bot. If it responds, it works!

Stop the test:
```bash
kill %1
```

---

## Step 7: Make it run forever

```bash
sudo nano /etc/systemd/system/sportbot.service
```

Paste this:

```ini
[Unit]
Description=BM Sport Weather Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/home/$USER/BMsportBot
EnvironmentFile=/home/$USER/BMsportBot/sportbot.env
ExecStart=/home/$USER/BMsportBot/venv/bin/python scripts/send_notification.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

⚠️ **Before saving**: replace `$USER` with your actual username. Check it with:
```bash
whoami
```
It's usually your Google account name (e.g. `francien_giebels`) or just `ubuntu`.

Save (`Ctrl+X`, `Y`, `Enter`), then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable sportbot
sudo systemctl start sportbot

# Check it's running
sudo systemctl status sportbot
```

You should see **"active (running)"** in green. Done! 🎉

---

## ⚠️ Important: Don't get charged

To make sure you stay on the free tier:

1. Go to **https://console.cloud.google.com/billing**
2. Set up a **budget alert** at $1 — you'll get an email if anything would cost money
3. Your `e2-micro` in `us-east1` with 30 GB disk = **$0/month**

If you're ever worried, you can check current costs at:
**Console → Billing → Reports**

---

## Useful commands

```bash
# Check bot status
sudo systemctl status sportbot

# View logs
sudo journalctl -u sportbot -n 50

# Follow logs live
sudo journalctl -u sportbot -f

# Restart after code update
cd ~/BMsportBot && git pull
sudo systemctl restart sportbot
```

---

## Updating the bot

When you push changes to GitHub:

1. Click **SSH** on the VM instances page
2. Run:
```bash
cd ~/BMsportBot
git pull
sudo systemctl restart sportbot
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| "e2-micro not available" | Make sure region is `us-east1`, `us-central1`, or `us-west1` |
| Bot doesn't respond on Telegram | Check logs: `sudo journalctl -u sportbot -n 50` |
| "coffee break" fallback message | `GROQ_API_KEY` is wrong or missing in `sportbot.env` |
| VM stops randomly | Check billing — make sure you're on the free tier config |
| SSH button doesn't work | Try a different browser, or disable ad blockers |

---

That's it. Free forever, runs 24/7, survives reboots.
