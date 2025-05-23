# koshinko-utils

A collection of utilities for the Koshinko project.

## Features

- **Data Processing:**  
    Scripts and tools for transforming, cleaning, and analyzing data.

- **Automation:**  
    Utilities for automating repetitive tasks and workflows.

- **API Clients:**  
    Ready-to-use clients for interacting with Koshinko-related APIs.

- **CLI Tools:**  
    Command-line tools for quick access to common operations.

- **Testing Utilities:**  
    Helpers and fixtures to streamline testing.

## Getting Started

1. Clone the repository:
     ```sh
     git clone https://github.com/yourusername/koshinko-utils.git
     cd koshinko-utils
     ```

2. Install dependencies:
     ```sh
     pip install -r requirements.txt
     ```

3. Explore the utilities in the `scripts/` and `utils/` directories.

# Security Notes

**Important:** The authentication files contain sensitive information:
- `service-account.json`
- `credentials.json` 
- `token.json`

These files should:
- Never be committed to version control
- Be stored securely
- Have restricted access permissions

To set up authentication:
1. Copy the template files:
   ```sh
   cp service-account.template.json service-account.json
   cp credentials.template.json credentials.json
   ```
2. Fill in your actual credentials from Google Cloud Console
3. Set restrictive permissions:
   ```sh
   chmod 600 service-account.json credentials.json
   ```
   
## Usage

- Run a script:
    ```sh
    python scripts/example_script.py
    ```

- Use a CLI tool:
    ```sh
    python -m utils.cli_tool --help
    ```

## Contributing

Contributions are welcome! Please open issues or submit pull requests.

## License

See [LICENSE](LICENSE) for details.