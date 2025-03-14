FROM python:3.11-slim

WORKDIR /app

# Build context is the project root (/home/claus/git/spotify-manager)
# Ensure a .dockerignore exists at the project root to exclude unnecessary files.

# Install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Files are copied relative to the project root
COPY . .

# Expose the port the app runs on
EXPOSE 5000

# Run the app using Gunicorn as the WSGI server
CMD [ "gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "wsgi:app" ]