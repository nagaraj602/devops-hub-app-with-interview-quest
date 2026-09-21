#!/usr/bin/env bash
# ==============================================================================
#  🚀 DevOps Knowledge Portal & Interview Hub - Universal Deployment Script
#  Compatible with: Git Bash (Windows), Ubuntu / Debian (Linux / GCP VM), macOS
#  Port: 8926 | Ubuntu Multi-Stage Dockerfile | Docker Desktop K8s | GCP Compose
# ==============================================================================

set -eo pipefail

# Text styling
BOLD="\033[1m"
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
CYAN="\033[1;36m"
RED="\033[1;31m"
RESET="\033[0m"

# Default configuration
DEFAULT_IMAGE_NAME="nagarajkamath602/devops-hub-app-with-interview-quest"
DEFAULT_TAG="latest"
DEFAULT_VERSION="1.0.9"
PORT="8926"
K8S_MANIFEST="k8s/all-in-one.yaml"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"

# Detect OS
OS="Unknown"
if [[ "$OSTYPE" == "msys"* || "$OSTYPE" == "cygwin"* || "$OSTYPE" == "win32"* ]]; then
    OS="Windows (Git Bash / Docker Desktop)"
elif [[ "$OSTYPE" == "linux"* ]]; then
    OS="Linux ($(grep -oP '(?<=^ID=).+' /etc/os-release 2>/dev/null | tr -d '"' || echo 'Generic'))"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macOS"
fi

print_header() {
    clear 2>/dev/null || true
    echo -e "${CYAN}========================================================================${RESET}"
    echo -e "${BOLD}     🚀 DevOps Knowledge Portal & Interview Hub Deployer${RESET}"
    echo -e "${CYAN}========================================================================${RESET}"
    echo -e " Environment : ${GREEN}$OS${RESET}"
    echo -e " Directory   : ${YELLOW}$APP_DIR${RESET}"
    echo -e " Image Target: ${YELLOW}$DEFAULT_IMAGE_NAME:$DEFAULT_TAG${RESET}"
    echo -e " Target Port : ${GREEN}$PORT${RESET} (Ubuntu Base)"
    echo -e "${CYAN}========================================================================${RESET}\n"
}

# ------------------------------------------------------------------------------
# Helper: Push image with Docker Hub account authorization verification
# ------------------------------------------------------------------------------
push_with_auth_check() {
    local img="$1"
    local repo_user="${img%%/*}"

    echo -e "\n${CYAN}==> Attempting to push image: ${YELLOW}$img${RESET}..."
    
    set +e
    push_output=$(docker push "$img" 2>&1)
    push_exit=$?
    set -e

    if [ $push_exit -eq 0 ]; then
        echo -e "${GREEN}✔ Image successfully pushed: $img${RESET}"
        return 0
    fi

    # Push failed - check for permission/authentication errors
    echo -e "\n${RED}✘ Failed to push image to Docker Hub!${RESET}"
    echo -e "${YELLOW}Docker Output:${RESET}"
    echo "$push_output" | sed 's/^/  /'

    if echo "$push_output" | grep -Ei "denied|unauthorized|authentication required|requested access" > /dev/null; then
        echo -e "\n${YELLOW}------------------------------------------------------------------------${RESET}"
        echo -e "${BOLD}${RED}⚠️  AUTHENTICATION / PERMISSION ISSUE DETECTED${RESET}"
        echo -e "You are pushing to repository owned by: ${CYAN}$repo_user${RESET}"
        echo -e "You may currently be logged into a ${RED}different Docker Hub account${RESET}."
        echo -e "${YELLOW}------------------------------------------------------------------------${RESET}"
        
        read -p "Would you like to log in to Docker Hub as '$repo_user' now? (Y/n): " do_login
        do_login=${do_login:-Y}
        if [[ "$do_login" =~ ^[Yy]$ ]]; then
            echo -e "\n${CYAN}Running 'docker login' for user '${repo_user}'...${RESET}"
            docker login -u "$repo_user"
            
            echo -e "\n${CYAN}Retrying push to ${YELLOW}$img${CYAN}...${RESET}"
            if docker push "$img"; then
                echo -e "${GREEN}✔ Image successfully pushed on retry: $img${RESET}"
                return 0
            else
                echo -e "${RED}✘ Push failed again. Please verify your repository permissions.${RESET}"
                return 1
            fi
        else
            echo -e "${YELLOW}Skipping re-login. The image was built locally but not pushed.${RESET}"
            return 1
        fi
    else
        echo -e "${RED}Unknown push error occurred. Please check network connectivity.${RESET}"
        return 1
    fi
}

# ------------------------------------------------------------------------------
# 1. Docker Compose Deployment (Local or GCP VM)
# ------------------------------------------------------------------------------
deploy_docker_compose() {
    echo -e "\n${CYAN}------------------------------------------------------------${RESET}"
    echo -e "${BOLD}  [1] Docker Compose Deployment (Port $PORT)${RESET}"
    echo -e "${CYAN}------------------------------------------------------------${RESET}"

    echo "Choose build / pull mode:"
    echo "  1) Build Docker image locally (Recommended for fresh updates)"
    echo "  2) Pull prebuilt image from Docker Hub (Fastest for GCP/Remote servers)"
    read -p "Select [1 or 2] (Default: 1): " compose_mode
    compose_mode=${compose_mode:-1}

    if [ "$compose_mode" == "1" ]; then
        echo -e "\n${CYAN}==> Building Ubuntu Multi-stage Docker image locally...${RESET}"
        docker compose build
        
        read -p "Do you want to push this newly built image to Docker Hub? (y/N): " do_push
        if [[ "$do_push" =~ ^[Yy]$ ]]; then
            push_with_auth_check "$DEFAULT_IMAGE_NAME:$DEFAULT_TAG"
        fi
    else
        echo -e "\n${CYAN}==> Pulling latest image from Docker Hub...${RESET}"
        docker compose pull devops-hub || {
            echo -e "${YELLOW}Warning: Pull failed, attempting local build fallback...${RESET}"
            docker compose build
        }
    fi

    echo -e "\n${CYAN}==> Stopping any previous container...${RESET}"
    docker compose down --remove-orphans || true

    echo -e "\n${CYAN}==> Starting devops-hub with Docker Compose on port $PORT...${RESET}"
    docker compose up -d

    echo -e "\n${GREEN}✔ Container started! Current status:${RESET}"
    docker compose ps

    echo -e "\n${CYAN}==> Verifying health status at http://localhost:$PORT/api/health (waiting 5s)...${RESET}"
    sleep 5
    if command -v curl &>/dev/null; then
        if curl -s -f "http://localhost:$PORT/api/health" > /dev/null; then
            echo -e "${GREEN}✔ Health Check Passed! (http://localhost:$PORT/api/health)${RESET}"
        else
            echo -e "${YELLOW}ℹ Container is initializing. Run 'docker compose logs -f' to monitor.${RESET}"
        fi
    fi

    echo -e "\n${GREEN}========================================================================${RESET}"
    echo -e " DevOps Hub is now accessible at:"
    echo -e "   • Web Portal        : ${CYAN}http://localhost:$PORT${RESET} (or http://<SERVER_IP>:$PORT)"
    echo -e "   • Question Bank     : ${CYAN}http://localhost:$PORT/question-bank${RESET}"
    echo -e "   • Project Page      : ${CYAN}http://localhost:$PORT/project${RESET}"
    echo -e "   • Training Materials: ${CYAN}http://localhost:$PORT/training-materials${RESET}"
    echo -e "   • Command Cheatsheet: ${CYAN}http://localhost:$PORT/command-cheatsheet${RESET}"
    echo -e "   • Sync All & Logs   : ${CYAN}http://localhost:$PORT/sync-all${RESET}"
    echo -e "${GREEN}========================================================================${RESET}"
}

# ------------------------------------------------------------------------------
# 2. Docker Desktop Kubernetes Deployment (Windows / Mac)
# ------------------------------------------------------------------------------
deploy_docker_desktop_k8s() {
    echo -e "\n${CYAN}------------------------------------------------------------${RESET}"
    echo -e "${BOLD}  [2] Docker Desktop Kubernetes Deployment (Port $PORT)${RESET}"
    echo -e "${CYAN}------------------------------------------------------------${RESET}"

    if ! command -v kubectl &>/dev/null; then
        echo -e "${RED}✘ 'kubectl' command not found. Please ensure Kubernetes is enabled in Docker Desktop.${RESET}"
        return 1
    fi

    current_ctx=$(kubectl config current-context 2>/dev/null || echo "none")
    echo -e "Current kubectl context: ${YELLOW}$current_ctx${RESET}"

    read -p "Do you want to rebuild and push the Docker image before deploying? (Y/n): " do_rebuild
    do_rebuild=${do_rebuild:-Y}
    if [[ "$do_rebuild" =~ ^[Yy]$ ]]; then
        echo -e "\n${CYAN}==> Building Ubuntu Multi-stage Docker image (tags: ${YELLOW}$DEFAULT_TAG, $DEFAULT_VERSION${CYAN})...${RESET}"
        docker build -t "$DEFAULT_IMAGE_NAME:$DEFAULT_TAG" -t "$DEFAULT_IMAGE_NAME:$DEFAULT_VERSION" .
        
        read -p "Push image to Docker Hub? (y/N): " do_push_k8s
        if [[ "$do_push_k8s" =~ ^[Yy]$ ]]; then
            push_with_auth_check "$DEFAULT_IMAGE_NAME:$DEFAULT_TAG"
            push_with_auth_check "$DEFAULT_IMAGE_NAME:$DEFAULT_VERSION"
        fi
    fi

    echo -e "\n${CYAN}==> Applying Kubernetes manifests from $K8S_MANIFEST...${RESET}"
    kubectl apply -f "$K8S_MANIFEST"

    echo -e "\n${CYAN}==> Restarting deployment rollout to load latest image...${RESET}"
    kubectl rollout restart deployment/devops-hub-deployment -n devops-hub || true

    echo -e "\n${CYAN}==> Waiting for deployment rollout...${RESET}"
    kubectl rollout status deployment/devops-hub-deployment -n devops-hub --timeout=120s || true

    echo -e "\n${GREEN}✔ Kubernetes Resources Status:${RESET}"
    kubectl get pods,svc -n devops-hub

    echo -e "\n${GREEN}========================================================================${RESET}"
    echo -e " Docker Desktop routes LoadBalancer directly to localhost!"
    echo -e " Access the portal at:"
    echo -e "   • Web Portal        : ${CYAN}http://localhost:$PORT${RESET}"
    echo -e "   • NodePort          : ${CYAN}http://localhost:30926${RESET}"
    echo -e "   • Question Bank     : ${CYAN}http://localhost:$PORT/question-bank${RESET}"
    echo -e "   • Project Page      : ${CYAN}http://localhost:$PORT/project${RESET}"
    echo -e "   • Training Materials: ${CYAN}http://localhost:$PORT/training-materials${RESET}"
    echo -e "   • Command Cheatsheet: ${CYAN}http://localhost:$PORT/command-cheatsheet${RESET}"
    echo -e "   • Sync All & Logs   : ${CYAN}http://localhost:$PORT/sync-all${RESET}"
    echo -e "${GREEN}========================================================================${RESET}"
}

# ------------------------------------------------------------------------------
# 3. Kubeadm / Production Kubernetes Cluster Deployment
# ------------------------------------------------------------------------------
deploy_kubeadm() {
    echo -e "\n${CYAN}------------------------------------------------------------${RESET}"
    echo -e "${BOLD}  [3] Kubeadm / Production Kubernetes Deployment${RESET}"
    echo -e "${CYAN}------------------------------------------------------------${RESET}"

    if ! command -v kubectl &>/dev/null; then
        echo -e "${RED}✘ 'kubectl' command not found. Ensure KUBECONFIG is exported.${RESET}"
        return 1
    fi

    echo -e "${CYAN}==> Checking Cluster Info...${RESET}"
    kubectl cluster-info || {
        echo -e "${RED}✘ Cannot connect to Kubernetes API server. Check your ~/.kube/config.${RESET}"
        return 1
    }

    echo -e "\n${CYAN}==> Applying Kubernetes manifests ($K8S_MANIFEST)...${RESET}"
    kubectl apply -f "$K8S_MANIFEST"

    echo -e "\n${CYAN}==> Monitoring deployment rollout in 'devops-hub' namespace...${RESET}"
    kubectl rollout status deployment/devops-hub-deployment -n devops-hub --timeout=120s

    echo -e "\n${GREEN}✔ Deployed Pods & Services:${RESET}"
    kubectl get pods,svc -n devops-hub -o wide

    echo -e "\n${YELLOW}📌 Accessing on Kubeadm Cluster:${RESET}"
    echo "  1) NodePort Access: The service exposes NodePort 30926."
    echo -e "     Access at: ${CYAN}http://<ANY_WORKER_NODE_IP>:30926${RESET}"
    echo "  2) Port-Forward (Quick check):"
    echo -e "     ${YELLOW}kubectl port-forward -n devops-hub svc/devops-hub-service $PORT:$PORT${RESET}"
}

# ------------------------------------------------------------------------------
# 4. Standalone Docker Run
# ------------------------------------------------------------------------------
deploy_docker_run() {
    echo -e "\n${CYAN}------------------------------------------------------------${RESET}"
    echo -e "${BOLD}  [4] Standalone Docker Run Container (Port $PORT)${RESET}"
    echo -e "${CYAN}------------------------------------------------------------${RESET}"

    CONTAINER_NAME="devops-hub"
    read -p "Enter container name (Default: devops-hub): " input_cname
    CONTAINER_NAME=${input_cname:-devops-hub}

    read -p "Enter image to run (Default: $DEFAULT_IMAGE_NAME:$DEFAULT_TAG): " input_img
    IMAGE_TO_RUN=${input_img:-"$DEFAULT_IMAGE_NAME:$DEFAULT_TAG"}

    echo -e "\n${CYAN}==> Checking image $IMAGE_TO_RUN...${RESET}"
    docker pull "$IMAGE_TO_RUN" || true

    if docker ps -a --format '{{.Names}}' | grep -Eq "^${CONTAINER_NAME}\$"; then
        echo -e "${YELLOW}Stopping and removing existing '$CONTAINER_NAME' container...${RESET}"
        docker stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
        docker rm "$CONTAINER_NAME" >/dev/null 2>&1 || true
    fi

    echo -e "\n${CYAN}==> Running container '$CONTAINER_NAME' on port $PORT...${RESET}"
    docker run -d \
        --name "$CONTAINER_NAME" \
        -p "$PORT:$PORT" \
        -e PORT="$PORT" \
        -e HOST="0.0.0.0" \
        --restart unless-stopped \
        "$IMAGE_TO_RUN"

    echo -e "\n${GREEN}✔ Container started on http://localhost:$PORT!${RESET}"
    docker ps --filter "name=$CONTAINER_NAME"
}

# ------------------------------------------------------------------------------
# 5. GCP Ubuntu Full Automated Setup (Install Docker + Deploy + Cloudflare)
# ------------------------------------------------------------------------------
deploy_gcp_ubuntu_full() {
    echo -e "\n${CYAN}------------------------------------------------------------${RESET}"
    echo -e "${BOLD}  [5] GCP Ubuntu Full Setup (Docker + App on Port $PORT + Cloudflare Tunnel)${RESET}"
    echo -e "${CYAN}------------------------------------------------------------${RESET}"

    if [[ "$OSTYPE" != "linux"* ]]; then
        echo -e "${YELLOW}Notice: This option is designed to run directly on an Ubuntu Linux server (e.g. GCP VM).${RESET}"
        read -p "Continue anyway? (y/N): " cont
        if [[ ! "$cont" =~ ^[Yy]$ ]]; then return 0; fi
    fi

    # Step 1: Install Docker if missing
    if ! command -v docker &>/dev/null; then
        echo -e "\n${CYAN}==> Docker not found. Installing Docker engine on Ubuntu...${RESET}"
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        rm -f get-docker.sh
        sudo usermod -aG docker "$USER" 2>/dev/null || true
        sudo systemctl enable --now docker
        echo -e "${GREEN}✔ Docker installed successfully!${RESET}"
    else
        echo -e "${GREEN}✔ Docker is already installed.${RESET}"
    fi

    # Step 2: Ensure Docker Compose is available
    if ! docker compose version &>/dev/null; then
        echo -e "\n${CYAN}==> Installing Docker Compose plugin...${RESET}"
        sudo apt-get update && sudo apt-get install -y docker-compose-plugin
    fi

    # Step 3: Deploy Application via Docker Compose
    echo -e "\n${CYAN}==> Deploying DevOps Hub via Docker Compose on port $PORT...${RESET}"
    docker compose pull devops-hub || true
    docker compose down --remove-orphans || true
    docker compose up -d

    echo -e "\n${GREEN}✔ Application container running on port $PORT!${RESET}"
    docker compose ps

    # Step 4: Cloudflare Tunnel Setup
    setup_cloudflare_tunnel "1"
}

# ------------------------------------------------------------------------------
# 6. Cloudflare Tunnel Installer & Runner
# ------------------------------------------------------------------------------
setup_cloudflare_tunnel() {
    local choice="$1"

    if [ -z "$choice" ]; then
        echo -e "\n${CYAN}------------------------------------------------------------${RESET}"
        echo -e "${BOLD}  [6] Cloudflare Tunnel Setup (Zero GCP Port Exposure)${RESET}"
        echo -e "${CYAN}------------------------------------------------------------${RESET}"
        echo "  1) Quick Tunnel (Free, instant https://xxxx.trycloudflare.com for port $PORT)"
        echo "  2) Cloudflare Zero Trust Named Tunnel (Permanent custom domain with Token)"
        echo "  3) Check running Cloudflare Tunnel status"
        read -p "Select [1, 2, or 3] (Default: 1): " choice
        choice=${choice:-1}
    fi

    if [ "$choice" == "3" ]; then
        if command -v systemctl &>/dev/null && systemctl list-unit-files | grep -q cloudflared; then
            sudo systemctl status cloudflared --no-pager
        else
            ps aux | grep cloudflared | grep -v grep || echo "No cloudflared process running."
        fi
        return 0
    fi

    # Install cloudflared binary if missing
    if ! command -v cloudflared &>/dev/null; then
        echo -e "\n${CYAN}==> Installing cloudflared...${RESET}"
        if [[ "$OSTYPE" == "linux"* ]]; then
            ARCH="amd64"
            if [ "$(uname -m)" == "aarch64" ]; then ARCH="arm64"; fi
            curl -fsSL "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${ARCH}.deb" -o /tmp/cloudflared.deb
            sudo dpkg -i /tmp/cloudflared.deb || sudo apt-get install -f -y
            rm -f /tmp/cloudflared.deb
        elif [[ "$OSTYPE" == "msys"* || "$OSTYPE" == "cygwin"* ]]; then
            echo -e "${YELLOW}On Windows, install cloudflared via winget: 'winget install --id Cloudflare.cloudflared'${RESET}"
            return 0
        fi
        echo -e "${GREEN}✔ cloudflared installed!${RESET}"
    fi

    if [ "$choice" == "1" ]; then
        echo -e "\n${GREEN}==> Starting Quick Cloudflare Tunnel for http://localhost:$PORT...${RESET}"
        nohup cloudflared tunnel --url "http://localhost:$PORT" > /tmp/cloudflared.log 2>&1 &
        sleep 5
        
        TUNNEL_URL=$(grep -o 'https://[-a-zA-Z0-9.]*\.trycloudflare\.com' /tmp/cloudflared.log | tail -n 1 || echo "")
        if [ -n "$TUNNEL_URL" ]; then
            echo -e "\n${GREEN}========================================================================${RESET}"
            echo -e " 🎉 YOUR APP IS LIVE SECURELY ON CLOUDFLARE TUNNEL:"
            echo -e "    ${BOLD}${CYAN}$TUNNEL_URL${RESET}"
            echo -e "    Question Bank: ${CYAN}$TUNNEL_URL/question-bank${RESET}"
            echo -e "${GREEN}========================================================================${RESET}"
        else
            echo -e "${YELLOW}Tunnel launched! Check URL by running:${RESET}"
            echo "  cat /tmp/cloudflared.log | grep trycloudflare.com"
        fi
    fi
}

# ------------------------------------------------------------------------------
# 7. Build & Push Image Only
# ------------------------------------------------------------------------------
build_and_push_image() {
    echo -e "\n${CYAN}------------------------------------------------------------${RESET}"
    echo -e "${BOLD}  [7] Build & Push Ubuntu Multi-Stage Docker Image${RESET}"
    echo -e "${CYAN}------------------------------------------------------------${RESET}"

    read -p "Enter version tag to build (Default: latest): " user_tag
    user_tag=${user_tag:-latest}

    TAGS=("-t" "$DEFAULT_IMAGE_NAME:$user_tag")
    if [ "$user_tag" != "latest" ]; then
        TAGS+=("-t" "$DEFAULT_IMAGE_NAME:latest")
    fi

    echo -e "\n${CYAN}==> Building Ubuntu Multi-stage image for tag '${user_tag}'...${RESET}"
    docker build "${TAGS[@]}" .

    echo -e "\n${GREEN}✔ Build finished successfully!${RESET}"

    # Push tag
    push_with_auth_check "$DEFAULT_IMAGE_NAME:$user_tag"
    if [ "$user_tag" != "latest" ]; then
        push_with_auth_check "$DEFAULT_IMAGE_NAME:latest"
    fi
}

# ------------------------------------------------------------------------------
# Main Menu Loop
# ------------------------------------------------------------------------------
while true; do
    print_header
    echo "Choose an action:"
    echo "  1) [Docker Compose] Deploy / update app on port $PORT using Docker Compose"
    echo "  2) [Docker Desktop K8s] Build, push & deploy to Docker Desktop Kubernetes (Port $PORT)"
    echo "  3) [Kubeadm Cluster] Deploy to production / multi-node Kubernetes cluster"
    echo "  4) [Docker Run] Run standalone container on port $PORT"
    echo "  5) [GCP Ubuntu Server Setup] Automated Setup (Install Docker + Deploy on Port $PORT + Tunnel)"
    echo "  6) [Cloudflare Tunnel] Setup zero-port secure HTTPS tunnel for port $PORT"
    echo "  7) [Build & Push Only] Build Ubuntu multi-stage image & push to Docker Hub"
    echo "  q) Quit"
    echo ""
    read -p "Select an option [1-7, q]: " choice

    case "$choice" in
        1) deploy_docker_compose ;;
        2) deploy_docker_desktop_k8s ;;
        3) deploy_kubeadm ;;
        4) deploy_docker_run ;;
        5) deploy_gcp_ubuntu_full ;;
        6) setup_cloudflare_tunnel "" ;;
        7) build_and_push_image ;;
        q|Q) echo -e "\n${CYAN}Exiting. Happy DevOps coding!${RESET}\n"; exit 0 ;;
        *) echo -e "\n${RED}Invalid option. Please choose between 1 and 7.${RESET}" ;;
    esac

    echo ""
    read -p "Press [Enter] to return to the menu..." dummy
done
