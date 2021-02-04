# thorunimore

![](resources/bot_image.png)

A moderator bot for the Unimore Informatica group

## Installation

1. Create a new venv and enter it:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
   
2. Download through PyPI:
   ```bash
   pip install thorunimore
   ```
   
3. Install the packages required to connect to the desired SQL database:
   
   - For PostgreSQL:
     ```bash
     pip install psycopg2-binary
     ```

## Running

### Development

1. Set the following env variables:

   - [The URI of the SQL database you want to use](https://docs.sqlalchemy.org/en/13/core/engines.html)
     ```bash
     SQLALCHEMY_DATABASE_URI=postgresql://steffo@/thor_dev
     ```
   
   - [A Google OAuth 2.0 client id and client secret](https://console.developers.google.com/apis/credentials)
     ```bash
     GOOGLE_CLIENT_ID=000000000000-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.apps.googleusercontent.com
     GOOGLE_CLIENT_SECRET=aaaaaaaaaaaaaaaaaaaaaaaa
     ```
   
   - A random string of characters used to sign Telegram data
     ```bash
     SECRET_KEY=Questo è proprio un bel test.
     ```
   
   - [api_id and api_hash for a Telegram application](https://my.telegram.org/apps)
     ```bash
     TELEGRAM_API_ID=1234567
     TELEGRAM_API_HASH=abcdefabcdefabcdefabcdefabcdefab
     ```

   - [The username and token of the Telegram bot](https://t.me/BotFather)
     ```bash
     TELEGRAM_BOT_USERNAME=thorunimorebot
     TELEGRAM_BOT_TOKEN=1111111111:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
     ```

   - The desired logging level and format
     ```bash
     LOG_LEVEL=DEBUG
     LOG_FORMAT={asctime}\t| {name}\t| {message}
     ```
   
   - The url at which web is hosted
     ```bash
     BASE_URL=http://lo.steffo.eu:30008
     ```
     
   - The url to join the Telegram group
     ```bash
     GROUP_URL=https://t.me/joinchat/AAAAAAAAAAAAAAAAAAAAAA
     ```

2. Run both the following processes:
   ```bash
   python -m thorunimore.telegram &
   python -m thorunimore.web &
   ```

### Production

1. Install `gunicorn` in the previously created venv:
   ```
   pip install gunicorn
   ```

2. Create the `bot-thorunimore` systemd unit by creating the `/etc/systemd/system/bot-thorunimore.service` file:
   ```ini
   [Unit]
   Name=bot-thorunimore
   Description=A moderator bot for the Unimore Informatica group
   Requires=network-online.target postgresql.service
   After=network-online.target nss-lookup.target
   
   [Service]
   Type=exec
   User=thorunimore
   WorkingDirectory=/opt/thorunimore
   ExecStart=/opt/thorunimore/venv/bin/python -OO -m thorunimore.telegram
   Environment=PYTHONUNBUFFERED=1
   
   [Install]
   WantedBy=multi-user.target
   ```

3. Create the `web-thorunimore` systemd unit by creating the `/etc/systemd/system/web-thorunimore.service` file:
   ```ini
   [Unit]
   Name=web-thorunimore
   Description=Thorunimore Gunicorn Server
   Wants=network-online.target postgresql.service
   After=network-online.target nss-lookup.target
   
   [Service]
   Type=exec
   User=thorunimore
   WorkingDirectory=/opt/thorunimore
   ExecStart=/opt/thorunimore/venv/bin/gunicorn -b 127.0.0.1:30008 thorunimore.web.__main__:reverse_proxy_app
   
   [Install]
   WantedBy=multi-user.target
   ```
   
4. Create the `/etc/systemd/system/bot-thorunimore.d/override.conf` and 
   `/etc/systemd/system/web-thorunimore.d/override.conf` files:
   ```ini
   [Service]
   Environment="SQLALCHEMY_DATABASE_URI=postgresql://thorunimore@/thor_prod"
   Environment="GOOGLE_CLIENT_ID=000000000000-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.apps.googleusercontent.com"
   Environment="GOOGLE_CLIENT_SECRET=aaaaaaaaaaaaaaaaaaaaaaaa"
   Environment="SECRET_KEY=Questo è proprio un bel server."
   Environment="TELEGRAM_API_ID=1234567"
   Environment="TELEGRAM_API_HASH=abcdefabcdefabcdefabcdefabcdefab"
   Environment="TELEGRAM_BOT_USERNAME=thorunimorebot"
   Environment="TELEGRAM_BOT_TOKEN=1111111111:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
   Environment="LOG_LEVEL=DEBUG"
   Environment="LOG_FORMAT={asctime}\t| {name}\t| {message}"
   Environment="BASE_URL=https://thor.steffo.eu"
   Environment="GROUP_URL=https://t.me/joinchat/AAAAAAAAAAAAAAAAAAAAAA"
   ```
   
5. Start (and optionally enable) both services:
   ```bash
   systemctl start "*-thorunimore"
   systemctl enable "*-thorunimore"
   ```

6. Reverse-proxy the web service:
   ```
   <VirtualHost *:80>
   
   ServerName "thor.steffo.eu"
   Redirect permanent "/" "https://thor.steffo.eu/"
   
   </VirtualHost>
   
   <VirtualHost *:443>
   
   ServerName "thor.steffo.eu"
   
   ProxyPass "/" "http://127.0.0.1:30008/"
   ProxyPassReverse "/" "http://127.0.0.1:30008/"
   RequestHeader set "X-Forwarded-Proto" expr=%{REQUEST_SCHEME}
   
   SSLEngine on
   SSLCertificateFile "/root/.acme.sh/*.steffo.eu/fullchain.cer"
   SSLCertificateKeyFile "/root/.acme.sh/*.steffo.eu/*.steffo.eu.key"
   
   </VirtualHost>
   ```
   ```bash
   a2ensite rp-thorunimore
   ```
