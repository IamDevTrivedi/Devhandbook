FROM texlive/texlive:latest

ENV DEBIAN_FRONTEND=noninteractive

# ---- System packages: pandoc, curl, fonts, chromium (for mermaid rendering) ----
RUN apt-get update && apt-get install -y --no-install-recommends \
        pandoc \
        curl \
        ca-certificates \
        gnupg \
        chromium \
        fonts-dejavu \
        fonts-noto \
        fonts-noto-cjk \
        lmodern \
    && rm -rf /var/lib/apt/lists/*

# ---- Node.js (needed for mermaid-cli / mermaid-filter) ----
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# ---- Use the system Chromium instead of letting puppeteer fetch its own ----
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

# ---- Mermaid renderer + the pandoc filter that swaps ```mermaid blocks for images ----
RUN npm install -g @mermaid-js/mermaid-cli@11.16.0 mermaid-filter

# Puppeteer/Chromium needs --no-sandbox when running as root inside a container
COPY puppeteer-config.json /opt/puppeteer-config.json
ENV MERMAID_FILTER_PUPPETEER_CONFIG=/opt/puppeteer-config.json
ENV MERMAID_FILTER_FORMAT=pdf

# ---- Build a LaTeX template from pandoc's own current default template, then
#      force a page break right after the table of contents. Doing it this way
#      (instead of hand-writing a template) keeps it correct for whatever
#      pandoc version apt installs. ----
RUN pandoc -D latex > /opt/template.tex \
    && sed -i 's/\\tableofcontents/\\tableofcontents\n\\newpage/' /opt/template.tex

COPY convert.sh /usr/local/bin/convert.sh
RUN chmod +x /usr/local/bin/convert.sh

WORKDIR /data
ENTRYPOINT ["/usr/local/bin/convert.sh"]
