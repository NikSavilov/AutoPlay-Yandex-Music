## AutoPlay-Yandex-Music

Bored? Turn on music when you're at home.  

AutoPlay-Yandex-Music scans the network to find your phone (by MAC).
When device is detected, it turns the music from Yandex Recommendations on. When you leave it stops.

## Installation

```
apt-get install python3.7 git python3-pip
git clone https://github.com/NikSavilov/AutoPlay-Yandex-Music.git
cd AutoPlay-Yandex-Music
python3.7 -m pip install -r requirements.txt
cp settings.py.example settings.py
vim settings.py
```

You should specify:
- MAC
- Login, Password on Yandex

Also alarm clock available. Define time in settings.

Then run:

```
python3.7 ./main.py
```

