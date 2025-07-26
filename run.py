# run.py
from dotenv import load_dotenv
from app import create_app

load_dotenv()
app = create_app()

if __name__ == '__main__':
    # This is for local development only.
    # Gunicorn will be used in production.
    app.run(debug=True, host='0.0.0.0', port=5000)