
FROM python:3.12 as base

# Setup env
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONFAULTHANDLER 1


#FROM base AS python-deps



# Install python dependencies in /.venv
COPY Pipfile .
COPY Pipfile.lock .
RUN PIPENV_VENV_IN_PROJECT=1 pipenv install --deploy


#FROM base AS runtime

# Copy virtual env from python-deps stage
#COPY /.venv /.venv
ENV PATH="/.venv/bin:$PATH"

RUN pip install pipenv
RUN apt-get update && apt-get install -y --no-install-recommends gcc ca-certificates imagemagick ffmpeg
RUN which ffmpeg

# Create and switch to a new user
RUN useradd --create-home appuser
WORKDIR /home/appuser
USER appuser
# Install pipenv and compilation dependencies



# Install application into container
COPY . .

# Run the application
ENTRYPOINT ["./run.sh" ]
