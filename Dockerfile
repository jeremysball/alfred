# syntax=docker/dockerfile:1

# STAGE 1: Homebrew Builder
FROM archlinux:multilib-devel-20260208.0.488728 AS builder

# Install base tools for Homebrew installation
RUN pacman -Syu -y --noconfirm
RUN pacman -S -y --noconfirm curl git sudo base-devel

# Create a temporary user for Homebrew
RUN useradd -m -s /bin/bash linuxbrew
RUN echo "linuxbrew ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

USER linuxbrew
RUN CI=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"


# STAGE 2: Release Image
FROM archlinux:multilib-devel-20260208.0.488728 AS release

# Set environment variables
ENV NODE_ENV=development
ENV NPM_CONFIG_LOGLEVEL=warn

# Create node user
RUN useradd -m -s /bin/bash node

# Update system
RUN pacman -Syu -y --noconfirm

# Install core packages
RUN pacman -S -y --noconfirm \
    python3 \
    uv \
    git \
    neovim \
    sudo \
    jq \
    unzip \
    bun \
    corepack \
    chromium \
    cronie \
    curl \
    wget \
    ca-certificates \
    procps \
    base-devel \
    direnv \
    ripgrep \
    fd \
    fzf \
    tmux \
    glib2 \
    nss \
    at-spi2-core \
    cups \
    libdrm \
    dbus \
    libxkbcommon \
    xorg-xrandr \
    mesa \
    alsa-lib \
    pango \
    cairo

# Clean up pacman cache
RUN rm -rf /var/cache/pacman/pkg/*

# Enable corepack for pnpm/yarn
RUN corepack enable

# Create symlinks for convenience
RUN ln -sf /usr/bin/nvim /usr/local/bin/vim

# Install modern Neovim (v0.11+) from official release
RUN curl -LO https://github.com/neovim/neovim/releases/latest/download/nvim-linux-x86_64.tar.gz
RUN rm -rf /opt/nvim
RUN tar -C /opt -xzf nvim-linux-x86_64.tar.gz
RUN ln -sf /opt/nvim-linux-x86_64/bin/nvim /usr/local/bin/nvim
RUN rm nvim-linux-x86_64.tar.gz

# Install Node.js 22 via pacman
RUN pacman -S -y --noconfirm nodejs npm
RUN rm -rf /var/cache/pacman/pkg/*

# Install GitHub CLI (gh)
RUN curl -fsSL https://github.com/cli/cli/releases/download/v2.67.0/gh_2.67.0_linux_amd64.tar.gz | tar -xz
RUN mv gh_2.67.0_linux_amd64/bin/gh /usr/local/bin/gh
RUN rm -rf gh_2.67.0_linux_amd64

# Install pi-coding-agent globally
RUN npm install -g @mariozechner/pi-coding-agent

# Install Playwright MCP Server and browsers
RUN npm install -g @playwright/mcp@latest
RUN npx playwright install chromium firefox webkit

# Create .pi directory structure and workspace
RUN mkdir -p /home/node/.pi/agent
RUN mkdir -p /workspace
RUN chown -R node:node /home/node/.pi
RUN chown -R node:node /workspace

# Copy homebrew from builder
COPY --from=builder /home/linuxbrew/.linuxbrew /home/linuxbrew/.linuxbrew
ENV PATH="/home/linuxbrew/.linuxbrew/bin:/home/linuxbrew/.linuxbrew/sbin:${PATH}"

# Install LazyVim for node user
USER node
RUN mkdir -p /home/node/.config
RUN mkdir -p /home/node/.local/share
RUN mkdir -p /home/node/.local/state

# Backup existing configs if present
RUN mv /home/node/.config/nvim /home/node/.config/nvim.bak.$(date +%s) 2>/dev/null || true
RUN mv /home/node/.local/share/nvim /home/node/.local/share/nvim.bak.$(date +%s) 2>/dev/null || true
RUN mv /home/node/.local/state/nvim /home/node/.local/state/nvim.bak.$(date +%s) 2>/dev/null || true

# Clone LazyVim starter
RUN git clone https://github.com/LazyVim/starter /home/node/.config/nvim
RUN rm -rf /home/node/.config/nvim/.git

# Verify installations
RUN pi --version
RUN nvim --version

# Set working directory
WORKDIR /workspace

# Add Tini for proper init handling
USER root
ENV TINI_VERSION=v0.19.0
ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini /tini
RUN chmod +x /tini

# Install Alfred (as root for system-wide installation)
USER root
WORKDIR /app
RUN chown node:node /app
RUN chmod -R 770 /app
USER node
RUN uv venv
COPY pyproject.toml uv.lock .
COPY alfred ./alfred
COPY docs ./docs
RUN bash -c "source /app/.venv/bin/activate && uv pip install -e ."

# Create symlink to docs for easy access
RUN ln -sf /app/docs /home/node/docs

ENTRYPOINT ["/tini", "-s", "--", "bash", "-c", "source /app/.venv/bin/activate && alfred"]
