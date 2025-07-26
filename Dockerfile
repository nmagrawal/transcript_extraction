# Start from the official Playwright image (amd64) which gives us a good base
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

# Set working directory
WORKDIR /app

# --- ROOT-LEVEL OPERATIONS ---
# Run all system-level installations as the default ROOT user.
# Install wget and dependencies, then install Google Chrome
# Install wget and Chrome Beta
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    ca-certificates \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libgdk-pixbuf2.0-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    && wget https://dl.google.com/linux/direct/google-chrome-beta_current_amd64.deb \
    && apt install -y ./google-chrome-beta_current_amd64.deb \
    && rm -f google-chrome-beta_current_amd64.deb \
    && apt-get clean && rm -rf /var/lib/apt/lists/*



# 3. Create the non-root user that the app will eventually run as
RUN useradd --create-home --shell /bin/bash appuser

# --- SWITCH TO NON-ROOT USER ---
# Now that all root-level tasks are done, we drop privileges for security.
USER appuser

# Set environment variables for the user. PATH is for Gunicorn.
ENV PATH="/home/appuser/.local/bin:${PATH}"

# Create screenshots directory

# Copy and install Python dependencies as the non-root user
COPY --chown=appuser:appuser requirements.txt .
RUN python -m pip install --no-cache-dir --user -r requirements.txt

# Copy the rest of the application code
COPY --chown=appuser:appuser . .

# Expose the port Gunicorn will listen on
EXPOSE 8080

# The final command to run the application.
# It uses xvfb-run to create a virtual display for Chrome.
# It uses the shell form to allow for ${PORT} variable substitution.
CMD /bin/sh -c "xvfb-run --server-args='-screen 0 1280x720x24' gunicorn --workers 4 --timeout 180 --bind 0.0.0.0:${PORT:-8080} run:app"