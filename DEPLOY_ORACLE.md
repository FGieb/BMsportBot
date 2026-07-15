# Deploy BMsportBot on Oracle Cloud (Free Forever)

This guide gets the bot running 24/7 on Oracle Cloud's Always Free tier.
Total time: ~30 minutes. Cost: €0.

---

## Step 1: Create an Oracle Cloud account

1. Go to **https://cloud.oracle.com/registrations/signup/create**
2. Fill in your details and verify your email
3. Choose your home region — pick one close to you (e.g. **EU Amsterdam**)
4. Add a credit/debit card — **they don't charge it**, it's only for identity verification
5. Complete signup — you'll get $300 trial credits + Always Free services

---

## Step 2: Create a free VM

1. Once logged in, go to the **Oracle Cloud Console**: https://cloud.oracle.com
2. Click **"Create a VM instance"** (on the main dashboard)
   - If you don't see it, go to: Menu (☰) → Compute → Instances → Create Instance
3. Configure the instance:
   - **Name**: `sportbot` (or whatever you like)
   - **Image**: Click **Edit** → select **Canonical Ubuntu 22.04** (or 24.04)
   - **Shape**: Click **Change Shape** → **Ampere** (ARM) → **VM.Standard.A1.Flex**
     - Set **OCPUs to 1** and **Memory to 6 GB** (this is within the free tier)
   - **Networking**: Leave defaults (a public subnet will be created)
   - **SSH Key**: Click **Generate a key pair** → **Save Private Key** 
     - ⚠️ **Save this .key file!** You need it to connect. Put it somewhere safe.
4. Click **Create**
5. Wait ~2 minutes for the instance to be "Running"
6. Copy the **Public IP address** shown on the instance page

---

## Step 3: Connect to your VM

### On Mac/Linux:
```bash
# Make the key file secure (required)
chmod 400 ~/Downloads/ssh-key-*.key

# Connect (replace with your IP)
ssh -i ~/Downloads/ssh-key-*.key ubuntu@YOUR_PUBLIC_IP
```

### On Windows:
- Use **PuTTY** or **Windows Terminal**:
```
ssh -i C:\Users\YOU\Downloads\ssh-key-*.key ubuntu@YOUR_PUBLIC_IP
```

If it asks "Are you sure you want to continue connecting?", type `yes`.

---

## Step 4: Install Python and the bot

Once connected to the VM, run these commands one by one:

```bash
# Update the system
sudo apt update && sudo apt upgrade -y

# Install Python and pip
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
# Create the env file
nano sportbot.env
```

Paste in your keys (replace with your actual values):

```
OPENWEATHER_API_KEY=your_key_here
WEATHERAPI_API_KEY=your_key_here
GROQ_API_KEY=your_key_here
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_IDS=martha:123456789,britt:987654321
```

Save and exit: press `Ctrl+X`, then `Y`, then `Enter`.

---

## Step 6: Test the bot

```bash
# Quick test — does it start without errors?
python scripts/send_notification.py &

# Wait 10 seconds, then check it's running
sleep 10
jobs

# If it says "Running", the bot works! Stop it for now:
kill %1
```

Try typing `/help` in the Telegram bot chat. If it responds, you're good.

---

## Step 7: Make it run forever (systemd)

This makes the bot start automatically, restart on crashes, and survive reboots.

```bash
# Create a systemd service
sudo nano /etc/systemd/system/sportbot.service
```

Paste this (edit the username if needed):

```ini
[Unit]
Description=BM Sport Weather Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/BMsportBot
EnvironmentFile=/home/ubuntu/BMsportBot/sportbot.env
ExecStart=/home/ubuntu/BMsportBot/venv/bin/python scripts/send_notification.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Save and exit (`Ctrl+X`, `Y`, `Enter`), then:

```bash
# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable sportbot
sudo systemctl start sportbot

# Check it's running
sudo systemctl status sportbot
```

You should see "active (running)" in green. 🎉

---

## Useful commands

```bash
# Check bot status
sudo systemctl status sportbot

# View recent logs
sudo journalctl -u sportbot -n 50

# Follow logs live
sudo journalctl -u sportbot -f

# Restart the bot (e.g. after updating code)
cd ~/BMsportBot && git pull
sudo systemctl restart sportbot

# Stop the bot
sudo systemctl stop sportbot
```

---

## Updating the bot

When you push changes to GitHub:

```bash
ssh -i ~/Downloads/ssh-key-*.key ubuntu@YOUR_PUBLIC_IP
cd ~/BMsportBot
git pull
sudo systemctl restart sportbot
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| Can't SSH in | Check the IP address, check your .key file path, make sure the VM is "Running" |
| Bot starts but Telegram doesn't respond | Check `TELEGRAM_BOT_TOKEN` in `sportbot.env` |
| LLM comments show "coffee break" | Check `GROQ_API_KEY` is set correctly |
| Bot crashes and restarts | Check logs: `sudo journalctl -u sportbot -n 100` |
| "Shape not available" during VM creation | Try a different availability domain, or try again later (free tier has capacity limits) |

---

That's it! The bot runs 24/7, survives reboots, and costs nothing.
