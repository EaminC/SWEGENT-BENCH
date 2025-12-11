import sys
import importlib.util
from pathlib import Path


def load_tool_module():
    """动态加载 tools/docker-build-init/main.py 模块。"""
    script_path = Path(__file__).parent.parent / "tools" / "docker-build-init" / "main.py"
    spec = importlib.util.spec_from_file_location("docker_build_init", script_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载模块: {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[arg-type]
    return module


def main():
    module = load_tool_module()
    result_path = module.run_docker_build_flow(Path.cwd())
    print(f"env.dockerfile 已生成: {result_path}")


if __name__ == "__main__":
    main()

