# RobRun

## Instalare (pe fiecare dispozitiv)
```
python -m venv .venv
# macOS:   source .venv/bin/activate
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
```
macOS: da terminalului permisiunile Screen Recording + Accessibility (+ Input Monitoring pentru record_route).

## Folosire
1. `python calibrate.py grab icon_ready`      (masa cu iarba gata, decupezi iconita)
2. `python calibrate.py grab prompt_harvest`  (langa masa, decupezi "СБОР УРОЖАЯ"; salveaza si PROMPT_REGION in .env)
3. `python calibrate.py test`                 (verifici scorurile live)
4. `python record_route.py`                   (mergi cu WASD pe ruta; opresti cu STOP_HOTKEY)
5. `python main.py`

Pe alt dispozitiv/rezolutie refa pasii 1, 2 si 4: template-urile depind de rezolutia ecranului.
Valorile (hold, asteptari, camera, praguri) sunt in `.env`.
