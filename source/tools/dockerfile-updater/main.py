#!/usr/bin/env python3
"""
Dockerfile Dependency Analysis and Update Tool

Features:
1. Read Dockerfile
2. Use AI to extract all dependencies (JSON format)
3. Analyze each dependency using compat tool
4. Use AI to update dependency versions in Dockerfile based on analysis results
5. Write updated Dockerfile to new file
"""

import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any

# Add tools directory to path for imports
tools_dir = Path(__file__).parent.parent
sys.path.insert(0, str(tools_dir))

# Import API and compat tools
from api.main import chat
from compat.package_version import analyze_package

# Supported languages list
SUPPORTED_LANGUAGES = ["python", "go", "rust", "java", "cpp"]


def read_dockerfile(dockerfile_path: str) -> str:
    """Read Dockerfile content"""
    path = Path(dockerfile_path)
    if not path.exists():
        raise FileNotFoundError(f"Dockerfile not found: {dockerfile_path}")
    return path.read_text(encoding="utf-8")


def extract_dependencies_with_ai(dockerfile_content: str) -> List[Dict[str, str]]:
    """
    Use AI to extract all dependencies directly installed in Dockerfile
    
    Returns format: [{"language": "python", "package": "pandas==1.1.1"}, ...]
    """
    prompt = f"""Please analyze the following Dockerfile content and extract all dependency packages that are DIRECTLY INSTALLED in the Dockerfile.

IMPORTANT: Only extract packages that are explicitly installed via commands like:
- RUN pip install ...
- RUN apt-get install ...
- RUN go get ...
- RUN cargo install ...
- RUN npm install ...
- RUN mvn install ...
- FROM base_image:version (extract version from base image)

DO NOT extract dependencies from:
- pyproject.toml
- package.json
- go.mod
- Cargo.toml
- pom.xml
- requirements.txt (unless it's installed via RUN pip install -r requirements.txt)
- Any other dependency files

Requirements:
1. Return only JSON format, no other text or explanations
2. JSON format is an array, each element contains:
   - "language": language name (one of: python, go, rust, java, cpp)
   - "package": package name and version, format as follows:
     * Python: "package==version" (e.g., "pandas==1.1.1" or "python==3.12" from base image)
     * Go: "module_path@version" (e.g., "k8s.io/kubernetes@v1.27.1")
     * Rust: "crate==version" (e.g., "tokio==1.28.0")
     * Java: "groupId:artifactId:version" (e.g., "org.apache.hadoop:hadoop-common:3.3.6")
     * C++: "package==version" (e.g., "fmt==10.0.0")
3. Extract version from base image if applicable (e.g., "python:3.12-slim" -> "python==3.12")
4. Extract packages from RUN commands that install dependencies
5. If version cannot be determined, version part can be omitted
6. Only extract dependencies for these 5 languages, skip others

Dockerfile content:
```
{dockerfile_content}
```

Return only JSON array, example format:
[
  {{"language": "python", "package": "python==3.12"}},
  {{"language": "python", "package": "pandas==1.1.1"}},
  {{"language": "go", "package": "k8s.io/kubernetes@v1.27.1"}}
]
"""

    messages = [
        {
            "role": "system",
            "content": "You are a professional dependency analysis tool. Return only JSON format array, no other text."
        },
        {
            "role": "user",
            "content": prompt
        }
    ]

    try:
        response = chat(messages, model="OpenAI/gpt-4o", temperature=0.3, max_tokens=2000)
        
        # Clean response, extract JSON part
        response = response.strip()
        
        # If response contains code block markers, extract content
        if "```json" in response or "```" in response:
            # Extract content from code block
            lines = response.split("\n")
            json_lines = []
            in_code_block = False
            for line in lines:
                if line.strip().startswith("```"):
                    in_code_block = not in_code_block
                    continue
                if in_code_block:
                    json_lines.append(line)
            if json_lines:
                response = "\n".join(json_lines)
        
        # Try to find start and end of JSON array
        start = response.find("[")
        end = response.rfind("]") + 1
        if start != -1 and end > start:
            response = response[start:end]
        
        # Parse JSON
        dependencies = json.loads(response)
        
        # Ensure it's a list
        if not isinstance(dependencies, list):
            dependencies = [dependencies]
        
        # Validate and filter: only keep supported languages
        valid_dependencies = []
        for dep in dependencies:
            if isinstance(dep, dict) and "language" in dep and "package" in dep:
                lang = dep["language"].lower()
                if lang in SUPPORTED_LANGUAGES:
                    valid_dependencies.append({
                        "language": lang,
                        "package": dep["package"]
                    })
        
        return valid_dependencies
        
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse AI response JSON: {e}")
        print(f"AI response content: {response[:500]}")
        return []
    except Exception as e:
        print(f"❌ Failed to call AI to extract dependencies: {e}")
        import traceback
        traceback.print_exc()
        return []


def analyze_dependencies(dependencies: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    Analyze each dependency using compat tool
    
    Returns list containing analysis results
    """
    analysis_results = []
    
    for dep in dependencies:
        lang = dep["language"]
        pkg = dep["package"]
        
        print(f"🔍 Analyzing dependency: {lang} - {pkg}")
        
        try:
            result = analyze_package(lang, pkg, limit_version=20)
            analysis_results.append({
                "original": dep,
                "analysis": result
            })
        except Exception as e:
            print(f"⚠️ Error analyzing {pkg}: {e}")
            analysis_results.append({
                "original": dep,
                "analysis": {
                    "language": lang,
                    "package": pkg,
                    "tree": None,
                    "versions": None,
                    "error": str(e)
                }
            })
    
    return analysis_results


def format_analysis_for_ai(analysis_results: List[Dict[str, Any]]) -> str:
    """Format analysis results as AI-readable string"""
    formatted = []
    
    for item in analysis_results:
        original = item["original"]
        analysis = item["analysis"]
        
        formatted.append(f"\nDependency: {original['language']} - {original['package']}")
        
        if analysis.get("error"):
            formatted.append(f"  Error: {analysis['error']}")
        else:
            if analysis.get("tree"):
                formatted.append(f"  Dependency Tree: {analysis['tree']}")
            if analysis.get("versions"):
                versions = analysis['versions']
                if isinstance(versions, str):
                    versions_list = [v.strip() for v in versions.split(',')]
                    formatted.append(f"  Available Versions: {', '.join(versions_list[:10])} (total {len(versions_list)})")
                else:
                    formatted.append(f"  Available Versions: {versions}")
        
        formatted.append("")
    
    return "\n".join(formatted)


def update_dockerfile_with_ai(original_dockerfile: str, analysis_results: List[Dict[str, Any]]) -> str:
    """
    Use AI to update dependency versions in Dockerfile based on analysis results
    
    Returns updated Dockerfile content
    """
    analysis_text = format_analysis_for_ai(analysis_results)
    
    prompt = f"""Please update the dependency versions in the Dockerfile based on the following dependency analysis results.

Requirements:
1. Return only the complete updated Dockerfile content, no other text or explanations
2. Update dependencies to appropriate versions based on available versions in analysis results
3. Keep other parts of Dockerfile unchanged
4. If a dependency has no available version information, keep it as is
5. Prefer newer but stable versions

Original Dockerfile:
```
{original_dockerfile}
```

Dependency Analysis Results:
{analysis_text}

Return only the updated Dockerfile content, no prefix or suffix explanations.
"""

    messages = [
        {
            "role": "system",
            "content": "You are a professional Dockerfile optimization tool. Return only the updated Dockerfile content, no other text."
        },
        {
            "role": "user",
            "content": prompt
        }
    ]

    try:
        response = chat(messages, model="OpenAI/gpt-4o", temperature=0.3, max_tokens=4000)
        
        # Clean response, extract Dockerfile content
        response = response.strip()
        
        # If response contains code block markers, extract content
        if "```" in response:
            lines = response.split("\n")
            # Find first ``` and last ```
            start_idx = None
            end_idx = None
            for i, line in enumerate(lines):
                if line.strip().startswith("```"):
                    if start_idx is None:
                        start_idx = i + 1
                    else:
                        end_idx = i
                        break
            
            if start_idx is not None and end_idx is not None:
                response = "\n".join(lines[start_idx:end_idx])
            elif start_idx is not None:
                # Only starting ```, extract all content after it
                response = "\n".join(lines[start_idx:])
        
        return response
        
    except Exception as e:
        print(f"❌ Failed to call AI to update Dockerfile: {e}")
        return original_dockerfile


def write_dockerfile(content: str, output_path: str):
    """Write content to Dockerfile"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"✅ Written new Dockerfile: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Dockerfile Dependency Analysis and Update Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s Dockerfile Dockerfile.new
  %(prog)s Dockerfile  # If output file not specified, will create Dockerfile.updated
        """
    )
    
    parser.add_argument(
        "input_dockerfile",
        help="Input Dockerfile path"
    )
    
    parser.add_argument(
        "output_dockerfile",
        nargs="?",
        default=None,
        help="Output Dockerfile path (optional, default: <input_filename>.updated)"
    )
    
    args = parser.parse_args()
    
    # Determine output file path
    if args.output_dockerfile is None:
        input_path = Path(args.input_dockerfile)
        args.output_dockerfile = str(input_path.parent / f"{input_path.stem}.updated{input_path.suffix}")
    
    try:
        # 1. Read Dockerfile
        print(f"📖 Reading Dockerfile: {args.input_dockerfile}")
        dockerfile_content = read_dockerfile(args.input_dockerfile)
        
        # 2. Use AI to extract dependencies (only from Dockerfile, not from dependency files)
        print("\n🤖 Using AI to extract dependencies from Dockerfile...")
        dependencies = extract_dependencies_with_ai(dockerfile_content)
        
        if not dependencies:
            print("⚠️ No dependencies found, skipping update")
            return
        
        print(f"✅ Found {len(dependencies)} dependencies:")
        for dep in dependencies:
            print(f"   - {dep['language']}: {dep['package']}")
        
        # 3. Analyze each dependency
        print("\n🔍 Analyzing dependencies...")
        analysis_results = analyze_dependencies(dependencies)
        
        # 4. Use AI to update Dockerfile
        print("\n🤖 Using AI to update Dockerfile...")
        updated_dockerfile = update_dockerfile_with_ai(dockerfile_content, analysis_results)
        
        # 5. Write new Dockerfile
        print(f"\n💾 Writing new Dockerfile...")
        write_dockerfile(updated_dockerfile, args.output_dockerfile)
        
        print("\n✅ Done!")
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

