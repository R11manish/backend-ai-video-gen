FROM public.ecr.aws/lambda/python:3.9

# Install system dependencies
RUN yum update -y && yum install -y \
    tar \
    xz \
    wget \
    libpng \
    libjpeg

# Install ffmpeg using static build
RUN mkdir -p /opt/ffmpeg && \
    cd /opt/ffmpeg && \
    wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz && \
    tar xf ffmpeg-release-amd64-static.tar.xz && \
    rm ffmpeg-release-amd64-static.tar.xz && \
    mv ffmpeg-*-amd64-static/* . && \
    rm -rf ffmpeg-*-amd64-static && \
    ln -s /opt/ffmpeg/ffmpeg /usr/local/bin/ffmpeg && \
    ln -s /opt/ffmpeg/ffprobe /usr/local/bin/ffprobe

# Copy function code
COPY *.py ${LAMBDA_TASK_ROOT}/

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Add ffmpeg to PATH for subprocess calls
ENV PATH="/opt/ffmpeg:${PATH}"

# Set the CMD to your handler
CMD [ "lambda_function.lambda_handler" ]