#python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload --timeout-keep-alive 3600
