#!/bin/bash
# SWEGENT-BENCH 环境安装脚本
# 用于在新服务器上自动安装和配置环境

# 不设置 set -e，因为我们需要处理用户输入和可选安装

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

print_info "SWEGENT-BENCH 环境安装脚本"
print_info "当前目录: $SCRIPT_DIR"
echo ""

# ============================================================================
# 步骤 1: 检查并创建 .env 文件
# ============================================================================
print_info "步骤 1: 配置环境变量文件"

if [ ! -f ".env.example" ]; then
    print_error ".env.example 文件不存在，正在创建..."
    cat > .env.example << 'EOF'
FORGE_API_KEY="your-forge-api-key-here"
FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
MODEL="OpenAI/gpt-4.1"
AI_TEMPERATURE=0.7


GITHUB_TOKEN=ghp_your_token_here

ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co
ANTHROPIC_AUTH_TOKEN="your-forge-api-key-here"
ANTHROPIC_MODEL="tensorblock/gpt-4.1"
ANTHROPIC_SMALL_FAST_MODEL="tensorblock/gpt-4.1"
EOF
    print_success "已创建 .env.example 文件"
fi

if [ -f ".env" ]; then
    print_warning ".env 文件已存在"
    read -p "是否覆盖现有 .env 文件? (y/N): " overwrite
    if [[ ! "$overwrite" =~ ^[Yy]$ ]]; then
        print_info "跳过 .env 文件创建"
    else
        cp .env.example .env
        print_success "已复制 .env.example 到 .env"
    fi
else
    cp .env.example .env
    print_success "已复制 .env.example 到 .env"
fi

# 询问用户输入 FORGE_API_KEY
echo ""
print_info "请输入您的 Forge API Key"
read -p "FORGE_API_KEY: " forge_key

if [ -z "$forge_key" ]; then
    print_warning "未输入 FORGE_API_KEY，将使用默认值"
    forge_key="your-forge-api-key-here"
fi

# 询问用户输入 GITHUB_TOKEN（可选）
echo ""
print_info "请输入您的 GitHub Token (可选，按 Enter 跳过)"
read -p "GITHUB_TOKEN: " github_token

if [ -z "$github_token" ]; then
    print_info "跳过 GITHUB_TOKEN 设置"
    github_token="ghp_your_token_here"
fi

# 写入 .env 文件
# 更新 FORGE_API_KEY（支持带引号和不带引号）
sed -i "s|FORGE_API_KEY=.*|FORGE_API_KEY=\"$forge_key\"|" .env
# 更新 ANTHROPIC_AUTH_TOKEN（应该和 FORGE_API_KEY 一样）
sed -i "s|ANTHROPIC_AUTH_TOKEN=.*|ANTHROPIC_AUTH_TOKEN=\"$forge_key\"|" .env
# 更新 GITHUB_TOKEN
sed -i "s|GITHUB_TOKEN=.*|GITHUB_TOKEN=$github_token|" .env
print_success "已更新 .env 文件"

echo ""

# ============================================================================
# 步骤 2: 检查并安装 Python
# ============================================================================
print_info "步骤 2: 检查 Python 环境"

check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        print_success "Python 已安装: $PYTHON_VERSION"
        return 0
    else
        return 1
    fi
}

if ! check_python; then
    print_warning "Python3 未安装，正在安装..."
    
    # 检测系统类型
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
    else
        print_error "无法检测操作系统类型"
        exit 1
    fi
    
    case $OS in
        ubuntu|debian)
            print_info "检测到 Ubuntu/Debian 系统"
            sudo apt update
            sudo apt install -y python3 python3-pip python3-venv
            ;;
        centos|rhel|fedora)
            print_info "检测到 CentOS/RHEL/Fedora 系统"
            if command -v dnf &> /dev/null; then
                sudo dnf install -y python3 python3-pip
            elif command -v yum &> /dev/null; then
                sudo yum install -y python3 python3-pip
            fi
            ;;
        *)
            print_error "不支持的操作系统: $OS"
            print_info "请手动安装 Python3"
            exit 1
            ;;
    esac
    
    if check_python; then
        print_success "Python3 安装完成"
    else
        print_error "Python3 安装失败"
        exit 1
    fi
fi

# 检查 Python 版本（需要 >= 3.6）
PYTHON_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
PYTHON_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 6 ]); then
    print_error "Python 版本过低，需要 Python 3.6 或更高版本"
    exit 1
fi

echo ""

# ============================================================================
# 步骤 3: 检查并安装 pip
# ============================================================================
print_info "步骤 3: 检查 pip"

check_pip() {
    if command -v pip3 &> /dev/null || python3 -m pip --version &> /dev/null; then
        PIP_VERSION=$(python3 -m pip --version 2>&1 | head -n1)
        print_success "pip 已安装: $PIP_VERSION"
        return 0
    else
        return 1
    fi
}

if ! check_pip; then
    print_warning "pip 未安装，正在安装..."
    
    case $OS in
        ubuntu|debian)
            sudo apt install -y python3-pip
            ;;
        centos|rhel|fedora)
            if command -v dnf &> /dev/null; then
                sudo dnf install -y python3-pip
            elif command -v yum &> /dev/null; then
                sudo yum install -y python3-pip
            fi
            ;;
    esac
    
    # 如果系统包管理器安装失败，尝试使用 get-pip.py
    if ! check_pip; then
        print_info "尝试使用 get-pip.py 安装 pip..."
        curl -sS https://bootstrap.pypa.io/get-pip.py | python3
    fi
    
    if check_pip; then
        print_success "pip 安装完成"
    else
        print_error "pip 安装失败"
        exit 1
    fi
fi

# 升级 pip
print_info "升级 pip 到最新版本..."
python3 -m pip install --upgrade pip setuptools wheel --user 2>/dev/null || true
print_success "pip 已升级"

echo ""

# ============================================================================
# 步骤 4: 检查并安装 Docker
# ============================================================================
print_info "步骤 4: 检查 Docker"

check_docker() {
    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker --version 2>&1)
        # 检查是否有权限使用 Docker
        if docker ps &> /dev/null; then
            print_success "Docker 已安装且可访问: $DOCKER_VERSION"
            return 0
        else
            print_warning "Docker 已安装但可能没有权限: $DOCKER_VERSION"
            return 1
        fi
    else
        return 1
    fi
}

DOCKER_NEEDS_INSTALL=false
DOCKER_NEEDS_PERMISSION=false

if ! check_docker; then
    if ! command -v docker &> /dev/null; then
        DOCKER_NEEDS_INSTALL=true
        print_warning "Docker 未安装"
        read -p "是否安装 Docker? (y/N): " install_docker
        
        if [[ "$install_docker" =~ ^[Yy]$ ]]; then
            print_info "正在安装 Docker..."
            
            # 检测系统类型
            if [ -f /etc/os-release ]; then
                . /etc/os-release
                OS=$ID
            fi
            
            case $OS in
                ubuntu|debian)
                    print_info "在 Ubuntu/Debian 上安装 Docker..."
                    # 卸载旧版本
                    sudo apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true
                    
                    # 安装依赖
                    sudo apt-get update
                    sudo apt-get install -y \
                        ca-certificates \
                        curl \
                        gnupg \
                        lsb-release
                    
                    # 添加 Docker 官方 GPG key
                    sudo mkdir -p /etc/apt/keyrings
                    curl -fsSL https://download.docker.com/linux/$OS/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
                    
                    # 设置仓库
                    echo \
                      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$OS \
                      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
                    
                    # 安装 Docker
                    sudo apt-get update
                    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
                    ;;
                centos|rhel)
                    print_info "在 CentOS/RHEL 上安装 Docker..."
                    sudo yum install -y yum-utils
                    sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
                    sudo yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
                    sudo systemctl start docker
                    sudo systemctl enable docker
                    ;;
                fedora)
                    print_info "在 Fedora 上安装 Docker..."
                    sudo dnf install -y dnf-plugins-core
                    sudo dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
                    sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
                    sudo systemctl start docker
                    sudo systemctl enable docker
                    ;;
                *)
                    print_error "不支持的操作系统: $OS"
                    print_info "请手动安装 Docker: https://docs.docker.com/get-docker/"
                    DOCKER_NEEDS_INSTALL=false
                    ;;
            esac
            
            if command -v docker &> /dev/null; then
                print_success "Docker 安装完成"
                DOCKER_NEEDS_PERMISSION=true
            else
                print_error "Docker 安装失败，请手动安装"
            fi
        else
            print_info "跳过 Docker 安装"
        fi
    else
        DOCKER_NEEDS_PERMISSION=true
    fi
fi

# 处理 Docker 权限问题
DOCKER_PERMISSION_FIXED=false
if [ "$DOCKER_NEEDS_PERMISSION" = true ] || (command -v docker &> /dev/null && ! docker ps &> /dev/null 2>&1); then
    if command -v docker &> /dev/null; then
        print_info "配置 Docker 用户权限..."
        
        # 检查用户是否已在 docker 组中
        CURRENT_GROUPS=$(groups)
        if echo "$CURRENT_GROUPS" | grep -q docker; then
            print_info "用户已在 docker 组中"
            # 尝试测试 Docker 访问
            if docker ps &> /dev/null 2>&1; then
                print_success "Docker 权限正常"
                DOCKER_PERMISSION_FIXED=true
            else
                print_warning "Docker 权限可能未在当前 shell 中生效"
                print_info "当前 shell 可能还没有 docker 组权限"
                echo ""
                print_info "要使用 Docker，您需要："
                echo "  1. 运行: newgrp docker  (会启动新的 shell)"
                echo "  2. 或者重新登录/重启终端"
                echo ""
                print_warning "注意: 如果选择运行 'newgrp docker'，脚本会在新 shell 中继续"
                print_warning "      但建议先完成安装，然后手动运行 'newgrp docker'"
                read -p "是否现在运行 'newgrp docker'? (y/N): " run_newgrp
                if [[ "$run_newgrp" =~ ^[Yy]$ ]]; then
                    print_info "运行 newgrp docker..."
                    print_warning "注意: newgrp 会启动新的子 shell"
                    print_info "在新 shell 中，请运行: cd $SCRIPT_DIR && ./setup.sh"
                    print_info "或者继续当前安装，稍后手动运行 'newgrp docker'"
                    echo ""
                    # 运行 newgrp，但不在其中执行脚本（因为会中断）
                    newgrp docker << 'DOCKER_GROUP_EOF'
echo ""
echo "=========================================="
echo "已切换到 docker 组"
echo "当前 shell 现在可以访问 Docker"
echo "=========================================="
echo ""
echo "要完成安装，请运行:"
echo "  cd $SCRIPT_DIR"
echo "  # 然后继续使用 Docker"
echo ""
DOCKER_GROUP_EOF
                    # 提示用户
                    print_info "已运行 newgrp docker"
                    print_warning "如果要在新 shell 中继续，请在新 shell 中运行剩余的安装步骤"
                    print_info "或者继续当前安装，稍后使用 Docker"
                else
                    print_info "跳过 newgrp，请稍后手动运行 'newgrp docker' 或重新登录"
                fi
            fi
        else
            print_info "将用户添加到 docker 组..."
            sudo usermod -aG docker $USER
            print_success "用户已添加到 docker 组"
            echo ""
            print_warning "需要运行 'newgrp docker' 或重新登录才能使用 Docker"
            print_info "选项 1: 现在运行 'newgrp docker' (会启动新 shell)"
            print_info "选项 2: 稍后重新登录或重启终端"
            read -p "是否现在运行 'newgrp docker'? (y/N): " run_newgrp
            if [[ "$run_newgrp" =~ ^[Yy]$ ]]; then
                print_info "运行 newgrp docker..."
                print_warning "注意: newgrp 会启动新的子 shell"
                print_info "在新 shell 中，请运行: cd $SCRIPT_DIR && ./setup.sh"
                print_info "或者继续当前安装，稍后手动运行 'newgrp docker'"
                echo ""
                # 运行 newgrp
                newgrp docker << 'DOCKER_GROUP_EOF'
echo ""
echo "=========================================="
echo "已切换到 docker 组"
echo "当前 shell 现在可以访问 Docker"
echo "=========================================="
echo ""
echo "要完成安装，请运行:"
echo "  cd $SCRIPT_DIR"
echo "  # 然后继续使用 Docker"
echo ""
DOCKER_GROUP_EOF
                print_info "已运行 newgrp docker"
                print_warning "如果要在新 shell 中继续，请在新 shell 中运行剩余的安装步骤"
            else
                print_info "跳过 newgrp，请稍后重新登录以使用 Docker"
            fi
        fi
    fi
fi

echo ""

# ============================================================================
# 步骤 5: 检查并安装 Conda (可选)
# ============================================================================
print_info "步骤 5: 检查 Conda (可选)"

check_conda() {
    if command -v conda &> /dev/null; then
        CONDA_VERSION=$(conda --version 2>&1)
        print_success "Conda 已安装: $CONDA_VERSION"
        return 0
    else
        return 1
    fi
}

if ! check_conda; then
    print_warning "Conda 未安装"
    read -p "是否安装 Miniconda? (y/N): " install_conda
    
    if [[ "$install_conda" =~ ^[Yy]$ ]]; then
        print_info "正在安装 Miniconda..."
        
        # 检测架构
        ARCH=$(uname -m)
        if [ "$ARCH" = "x86_64" ]; then
            CONDA_ARCH="x86_64"
        elif [ "$ARCH" = "aarch64" ]; then
            CONDA_ARCH="aarch64"
        else
            print_error "不支持的架构: $ARCH"
            exit 1
        fi
        
        # 下载并安装 Miniconda
        CONDA_INSTALLER="Miniconda3-latest-Linux-${CONDA_ARCH}.sh"
        CONDA_URL="https://repo.anaconda.com/miniconda/${CONDA_INSTALLER}"
        
        print_info "下载 Miniconda: $CONDA_URL"
        wget -q "$CONDA_URL" -O /tmp/$CONDA_INSTALLER || {
            print_error "下载失败，请手动安装 Conda"
            exit 1
        }
        
        print_info "安装 Miniconda..."
        bash /tmp/$CONDA_INSTALLER -b -p "$HOME/miniconda3"
        rm /tmp/$CONDA_INSTALLER
        
        # 初始化 Conda
        "$HOME/miniconda3/bin/conda" init bash
        print_success "Miniconda 安装完成"
        
        # 尝试在当前 shell 中初始化 conda
        print_info "初始化 Conda 到当前 shell..."
        eval "$($HOME/miniconda3/bin/conda shell.bash hook)" 2>/dev/null || true
        
        print_warning "请运行 'source ~/.bashrc' 或重新打开终端以使用 Conda"
    else
        print_info "跳过 Conda 安装"
    fi
else
    print_info "Conda 已存在，跳过安装"
    
    # 尝试在当前 shell 中初始化 conda（如果还没有）
    if ! command -v conda &> /dev/null; then
        if [ -f "$HOME/miniconda3/bin/conda" ]; then
            print_info "在当前 shell 中初始化 Conda..."
            eval "$($HOME/miniconda3/bin/conda shell.bash hook)" 2>/dev/null || true
            if command -v conda &> /dev/null; then
                print_success "Conda 已在当前 shell 中初始化"
            fi
        elif [ -f "$HOME/anaconda3/bin/conda" ]; then
            print_info "在当前 shell 中初始化 Conda..."
            eval "$($HOME/anaconda3/bin/conda shell.bash hook)" 2>/dev/null || true
            if command -v conda &> /dev/null; then
                print_success "Conda 已在当前 shell 中初始化"
            fi
        fi
    fi
fi

echo ""

# ============================================================================
# 步骤 6: 安装 Python 依赖
# ============================================================================
print_info "步骤 6: 安装 Python 依赖包"

if [ ! -f "requirements.txt" ]; then
    print_error "requirements.txt 文件不存在"
    exit 1
fi

print_info "安装依赖包（这可能需要几分钟）..."
python3 -m pip install --user -r requirements.txt

if [ $? -eq 0 ]; then
    print_success "依赖包安装完成"
else
    print_error "依赖包安装失败"
    exit 1
fi

echo ""

# ============================================================================
# 步骤 7: 配置 PATH
# ============================================================================
print_info "步骤 7: 配置 PATH 环境变量"

# 检查 ~/.local/bin 是否在 PATH 中
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    print_info "添加 ~/.local/bin 到 PATH..."
    
    # 检查是否已在 .bashrc 中
    if ! grep -q '\.local/bin' ~/.bashrc 2>/dev/null; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
        print_success "已添加 ~/.local/bin 到 ~/.bashrc"
    else
        print_info "~/.local/bin 已在 ~/.bashrc 中"
    fi
    
    # 导出到当前会话
    export PATH="$HOME/.local/bin:$PATH"
    print_success "PATH 已更新（当前会话）"
else
    print_info "~/.local/bin 已在 PATH 中"
fi

echo ""

# ============================================================================
# 步骤 8: 检查并安装 Claude CLI
# ============================================================================
print_info "步骤 8: 检查 Claude CLI"

check_claude() {
    if command -v claude &> /dev/null; then
        CLAUDE_VERSION=$(claude --version 2>&1 | head -n1)
        print_success "Claude CLI 已安装: $CLAUDE_VERSION"
        return 0
    else
        return 1
    fi
}

if ! check_claude; then
    print_warning "Claude CLI 未安装"
    print_info "Claude CLI 用于生成 Dockerfile 和测试用例"
    read -p "是否安装 Claude CLI? (y/N): " install_claude
    
    if [[ "$install_claude" =~ ^[Yy]$ ]]; then
        print_info "正在安装 Claude CLI..."
        
        # 使用官方安装脚本
        if curl -fsSL https://claude.ai/install.sh | bash; then
            # 确保 PATH 包含 ~/.local/bin
            export PATH="$HOME/.local/bin:$PATH"
            
            # 验证安装
            if check_claude; then
                print_success "Claude CLI 安装完成"
            else
                print_warning "Claude CLI 安装完成，但可能需要重新加载 PATH"
                print_info "请运行: source ~/.bashrc 或重新打开终端"
            fi
        else
            print_error "Claude CLI 安装失败"
            print_info "可以稍后手动安装: curl -fsSL https://claude.ai/install.sh | bash"
        fi
    else
        print_info "跳过 Claude CLI 安装"
        print_warning "repo-build 和 test-gen 功能需要 Claude CLI"
        print_info "可以稍后手动安装: curl -fsSL https://claude.ai/install.sh | bash"
    fi
else
    print_info "Claude CLI 已存在，跳过安装"
fi

echo ""

# ============================================================================
# 步骤 9: 验证安装
# ============================================================================
print_info "步骤 9: 验证安装"

# 验证 Python 包
print_info "验证 Python 包..."
python3 -c "import openai, requests, dotenv, tqdm; print('✓ 所有依赖包正常')" 2>/dev/null && {
    print_success "Python 依赖验证通过"
} || {
    print_error "Python 依赖验证失败"
    exit 1
}

echo ""

# ============================================================================
# 完成
# ============================================================================
print_success "=========================================="
print_success "环境安装完成！"
print_success "=========================================="
echo ""
print_info "已完成的配置："
echo "  ✓ Python 环境已安装"
echo "  ✓ pip 已安装并升级"
echo "  ✓ Python 依赖包已安装"
echo "  ✓ .env 文件已配置"
if check_conda; then
    echo "  ✓ Conda 已安装"
fi
if command -v docker &> /dev/null; then
    echo "  ✓ Docker 已安装"
fi
if command -v claude &> /dev/null; then
    echo "  ✓ Claude CLI 已安装"
fi
echo ""
print_info "下一步："
echo "  1. 如果安装了 Conda，请运行: source ~/.bashrc"
echo "  2. 验证安装: python3 -c 'import openai; print(\"OK\")'"
echo "  3. 查看运行指南: cat 运行指南.md"
echo ""
print_warning "注意: 如果这是新安装的 Conda，请重新打开终端或运行 'source ~/.bashrc'"
echo ""

# 询问用户是否继续
read -p "是否现在验证所有工具? (y/N): " verify_now
if [[ "$verify_now" =~ ^[Yy]$ ]]; then
    echo ""
    print_info "验证工具..."
    
    # 检查 claude 命令
    if command -v claude &> /dev/null; then
        CLAUDE_VER=$(claude --version 2>&1 | head -n1)
        print_success "Claude CLI 已安装: $CLAUDE_VER"
    else
        print_warning "Claude CLI 未找到"
        print_info "可以运行安装脚本: curl -fsSL https://claude.ai/install.sh | bash"
    fi
    
    # 检查 docker
    if command -v docker &> /dev/null; then
        if docker ps &> /dev/null; then
            print_success "Docker 已安装且可访问"
        else
            print_warning "Docker 已安装但可能没有权限"
            print_info "如果已运行 'newgrp docker'，请在新终端中验证"
            print_info "或者运行: sudo usermod -aG docker \$USER 然后重新登录"
        fi
    else
        print_warning "Docker 未安装，test-gen 功能需要 Docker"
        print_info "可以运行此脚本并选择安装 Docker"
    fi
    
    echo ""
    print_success "验证完成！"
fi

print_info "安装脚本执行完毕！"

