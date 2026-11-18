@echo off
set ROOT=D:\Project\dewajamv2

wt -d "%ROOT%\backend" --title Backend cmd /k "call .venv\Scripts\activate.bat && uvicorn main:app --reload" ; new-tab -d "%ROOT%\frontend" --title Frontend cmd /k "npm run dev"
