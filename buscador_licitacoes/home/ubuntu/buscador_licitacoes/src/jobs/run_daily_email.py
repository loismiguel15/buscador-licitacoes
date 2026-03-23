from src.main import app
from src.jobs.daily_email import run

if __name__ == "__main__":
    with app.app_context():
        run()