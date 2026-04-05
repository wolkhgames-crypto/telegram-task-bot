from setuptools import setup, find_packages

setup(
    name="telegram-task-bot",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "aiogram==3.4.1",
        "psycopg2-binary==2.9.9",
        "APScheduler==3.10.4",
        "python-dotenv==1.0.0",
        "dateparser==1.2.0",
        "pytz==2024.1",
        "timezonefinder==6.2.0",
    ],
    author="Your Name",
    description="Telegram bot for task management",
    python_requires=">=3.8",
)