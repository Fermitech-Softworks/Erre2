# 🇮🇹 Erre2: Raccoglitore (di) Riassunti
Erre2 è un webserver scritto in python che si pone come obiettivo quello di creare una piattaforma gradevole da usare
per l'universitario medio sulla quale è possibile caricare e aggiornare riassunti, piuttosto che ritrovarseli sparpagliati nel gruppo universitario. 
Con Erre2, inoltre, è possibile ricevere notifiche mediante Telegram di aggiornamenti e nuovi arrivi sulla piattaforma, per essere sempre aggiornati e pronti agli esami.

# 🇬🇧 Erre2: a simple Summary Binder
Erre2 is a webserver written in python that aims to become a comfortable platform to be used by the average university student to gather summaries in a more methodic and organized way than scattered in a Whatsapp group. Erre2 also supports telegram integration: provide your university group chat-id, and Erre2 will tell everyone if a new summary gets uploaded or updated.  
If you need a full website translation, please open an issue. I will be more than happy to provide one.

-----

## Installation

1. Clone this repository using `git`:
   ```
   git clone git@github.com:Fermitech-Softworks/Erre2.git
   ```
   
2. Create a new `venv`:
   ``` 
   python -m venv venv
   ```
   
3. `activate` the venv you just created:
   ```bash
   source venv/bin/activate
   ```
  
4. Install the requirements using `pip`:
   ```
   pip install -r requirements.txt
   ```
   
### For development

5. Use `export` to set the required environment variables:
   ```bash
   export COOKIE_SECRET_KEY='qwerty'  # A random string of characters
   export TELEGRAM_BOT_TOKEN='1234567890:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'  # The token for the Telegram notifier bot, get one at https://t.me/BotFather
   export TARGET_CHAT_ID='-100XXXXXXXXXX'  # The Telegram chat id where the notifications should be sent, remember that the id of supergroups is prefixed by -100
   export URL='http://127.0.0.1'  # The url at which Erre2 will be served
   ```
   
6. Run the `flask` development server:
   ```
   python server.py
   ```
   
### For production

_Assuming you are using a Linux distribution which supports systemd and has apache2 installed._

5. Create the file `/etc/systemd/system/web-erre2.service` with the following contents:
   ```ini
   [Unit]
   Name=web-erre2
   Description=Erre2 Gunicorn Server
   Wants=network-online.target
   After=network-online.target nss-lookup.target
   
   [Service]
   Type=exec
   User=erre2
   WorkingDirectory=/opt/erre2  # Replace with the directory where you cloned the repository
   ExecStart=/opt/erre2/venv/bin/gunicorn -b 127.0.0.1:30002 server:app  # Replace with the directory where you cloned the repository
   
   [Install]
   WantedBy=multi-user.target
   ```
   
6. Create the file `/etc/systemd/system/web-erre2.service.d/override.conf` with the following contents:
   ```ini
   [Service]
   Environment="COOKIE_SECRET_KEY=qwerty"  # A random string of characters
   Environment="BASE_URL=https://erre2.fermitech.info"  # The url at which Erre2 will be served
   Environment="TELEGRAM_BOT_TOKEN=1234567890:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"  # The token for the Telegram notifier bot, get one at https://t.me/BotFather
   Environment="TARGET_CHAT_ID=-100XXXXXXXXXX"  # The url at which Erre2 will be served
   ```
   
7. Reload all `systemd` daemon files:
   ```
   systemctl daemon-reload
   ```
   
8. `start` (and optionally `enable` to run at boot) the `web-erre2` systemd service:
   ```
   systemctl start web-erre2
   systemctl enable web-erre2
   ```
   
9. Configure a reverse proxy (`apache2`, `nginx`, ...) to proxy requests to and from `127.0.0.1:30002`.
