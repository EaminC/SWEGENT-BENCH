# Dockerfile Dependency Analysis and Update Tool

This tool can automatically analyze dependencies in Dockerfile and use AI to update them to appropriate versions.

## Features

1. **Read Dockerfile** - Read the specified Dockerfile
2. **AI Extract Dependencies** - Use AI to extract all dependency packages from Dockerfile (supports Python, Go, Rust, Java, C++)
3. **Dependency Analysis** - Analyze each dependency using compat tool (dependency tree, available versions, etc.)
4. **AI Update Dockerfile** - Use AI to intelligently update dependency versions in Dockerfile based on analysis results
5. **Write New File** - Write updated content to a new Dockerfile

## Usage

### Basic Usage

```bash
python main.py <input_dockerfile> [output_dockerfile]
```

### Examples

```bash
# Specify both input and output files
python main.py Dockerfile Dockerfile.new

# Only specify input file, output file will be automatically named Dockerfile.updated
python main.py Dockerfile
```

## Supported Dependency Formats

The tool supports dependencies for the following 5 languages:

- **Python**: `package==version` (e.g., `pandas==1.1.1`)
- **Go**: `module_path@version` (e.g., `k8s.io/kubernetes@v1.27.1`)
- **Rust**: `crate==version` (e.g., `tokio==1.28.0`)
- **Java**: `groupId:artifactId:version` (e.g., `org.apache.hadoop:hadoop-common:3.3.6`)
- **C++**: `package==version` (e.g., `fmt==10.0.0`)

## Workflow

1. Read Dockerfile content
2. Call AI to extract all dependencies (returns JSON format)
3. Analyze each dependency using compat tool:
   - Get dependency tree
   - Get available version list
4. Provide analysis results to AI to update dependency versions in Dockerfile
5. Write updated Dockerfile to new file

## Notes

- Need to configure `FORGE_API_KEY` in `.env` file to use AI features
- If AI returns dependencies with unsupported languages, they will be automatically filtered out
- If analysis of a dependency fails, it will continue processing other dependencies
- The tool will prefer newer but stable versions for updates

## Dependencies

- `openai` - OpenAI API client
- `python-dotenv` - Environment variable management
- `requests` - HTTP requests (used by compat tool)

## Error Handling

- If Dockerfile doesn't exist, will display error and exit
- If AI call fails, will display error message
- If analysis of a dependency fails, will log error but continue processing other dependencies
