Source URL: https://ohmyposh.dev/docs/advanced/mcp-server

[Skip to main content](https://ohmyposh.dev/docs/advanced/mcp-server#__docusaurus_skipToContent_fallback)

If you're enjoying Oh My Posh, consider becoming a [sponsor](https://github.com/sponsors/JanDeDobbeleer)
 to keep the project going strong 💪

On this page

What is the Oh My Posh MCP Server?[​](https://ohmyposh.dev/docs/advanced/mcp-server#what-is-the-oh-my-posh-mcp-server "Direct link to What is the Oh My Posh MCP Server?")

---------------------------------------------------------------------------------------------------------------------------------------------------------------------------

The Oh My Posh MCP (Model Context Protocol) Server is a validation service that allows you to validate your oh-my-posh theme configurations against the official JSON schema. It supports JSON, YAML, and TOML formats and provides detailed error reporting to help you create valid configurations.

Features[​](https://ohmyposh.dev/docs/advanced/mcp-server#features "Direct link to Features")

----------------------------------------------------------------------------------------------

*   **Multi-format Support**: Validates JSON, YAML, and TOML configurations
*   **Detailed Error Reporting**: Get precise validation errors with JSON paths
*   **Format Auto-detection**: Automatically detects the format of your configuration
*   **Warnings & Recommendations**: Receive best practice suggestions and deprecation warnings
*   **Standards-based**: Uses the official oh-my-posh JSON schema
*   **Remote Access**: No installation required - access via HTTPS

Usage[​](https://ohmyposh.dev/docs/advanced/mcp-server#usage "Direct link to Usage")

-------------------------------------------------------------------------------------

### With MCP Clients[​](https://ohmyposh.dev/docs/advanced/mcp-server#with-mcp-clients "Direct link to With MCP Clients")

Configure your MCP-compatible client (like Claude Desktop, Cline, or other AI assistants) to use the validator:

    {  "mcpServers": {    "oh-my-posh-validator": {      "url": "https://ohmyposh.dev/api/mcp",      "transport": "http"    }  }}

Then ask your AI assistant to validate your oh-my-posh configuration.

### Direct HTTP API[​](https://ohmyposh.dev/docs/advanced/mcp-server#direct-http-api "Direct link to Direct HTTP API")

You can also use the validator directly via HTTP requests.

#### Get Server Information[​](https://ohmyposh.dev/docs/advanced/mcp-server#get-server-information "Direct link to Get Server Information")

    curl https://ohmyposh.dev/api/mcp

#### List Available Tools[​](https://ohmyposh.dev/docs/advanced/mcp-server#list-available-tools "Direct link to List Available Tools")

    curl -X POST https://ohmyposh.dev/api/mcp \  -H "Content-Type: application/json" \  -d '{    "jsonrpc": "2.0",    "method": "tools/list",    "id": 1  }'

#### Validate a Configuration[​](https://ohmyposh.dev/docs/advanced/mcp-server#validate-a-configuration "Direct link to Validate a Configuration")

    curl -X POST https://ohmyposh.dev/api/mcp \  -H "Content-Type: application/json" \  -d '{    "jsonrpc": "2.0",    "method": "tools/call",    "params": {      "name": "validate_config",      "arguments": {        "content": "{\"$schema\":\"https://raw.githubusercontent.com/JanDeDobbeleer/oh-my-posh/main/themes/schema.json\",\"version\":4,\"blocks\":[]}",        "format": "json"      }    },    "id": 1  }'

Tool Parameters[​](https://ohmyposh.dev/docs/advanced/mcp-server#tool-parameters "Direct link to Tool Parameters")

-------------------------------------------------------------------------------------------------------------------

### validate\_config[​](https://ohmyposh.dev/docs/advanced/mcp-server#validate_config "Direct link to validate_config")

**Parameters:**

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| content | string | Yes | The configuration content as a string (JSON, YAML, or TOML) |
| format | string | No  | The format: `json`, `yaml`, `toml`, or `auto` (default: `auto`) |

**Returns:**

    {  "valid": true,  "errors": [],  "warnings": [    {      "path": "$schema",      "message": "Consider adding \"$schema\" property for better editor support.",      "type": "recommendation"    }  ],  "detectedFormat": "json",  "parsedConfig": { ... }}

Response Fields[​](https://ohmyposh.dev/docs/advanced/mcp-server#response-fields "Direct link to Response Fields")

-------------------------------------------------------------------------------------------------------------------

| Field | Type | Description |
| --- | --- | --- |
| valid | boolean | Whether the configuration is valid |
| errors | array | List of validation errors (empty if valid) |
| warnings | array | List of warnings and recommendations |
| detectedFormat | string | The detected or specified format |
| parsedConfig | object | The parsed configuration object |

Error Format[​](https://ohmyposh.dev/docs/advanced/mcp-server#error-format "Direct link to Error Format")

----------------------------------------------------------------------------------------------------------

Each error in the `errors` array contains:

| Field | Type | Description |
| --- | --- | --- |
| path | string | JSON path to the problematic property |
| message | string | Human-readable error message |
| keyword | string | The validation keyword that failed |
| params | object | Additional parameters about the error |
| data | any | The actual data that failed validation |

Examples[​](https://ohmyposh.dev/docs/advanced/mcp-server#examples "Direct link to Examples")

----------------------------------------------------------------------------------------------

### Valid Configuration[​](https://ohmyposh.dev/docs/advanced/mcp-server#valid-configuration "Direct link to Valid Configuration")

    {  "$schema": "https://raw.githubusercontent.com/JanDeDobbeleer/oh-my-posh/main/themes/schema.json",  "version": 4,  "blocks": [    {      "type": "prompt",      "alignment": "left",      "segments": [        {          "type": "path",          "style": "powerline",          "background": "blue",          "foreground": "white"        }      ]    }  ]}

### Invalid Configuration Example[​](https://ohmyposh.dev/docs/advanced/mcp-server#invalid-configuration-example "Direct link to Invalid Configuration Example")

    {  "blocks": [    {      "type": "invalid-type"    }  ]}

**Validation Result:**

    {  "valid": false,  "errors": [    {      "path": "/blocks/0/type",      "message": "Value must be one of: prompt, rprompt, line",      "keyword": "enum"    }  ]}

Integration Examples[​](https://ohmyposh.dev/docs/advanced/mcp-server#integration-examples "Direct link to Integration Examples")

----------------------------------------------------------------------------------------------------------------------------------

### Claude Desktop[​](https://ohmyposh.dev/docs/advanced/mcp-server#claude-desktop "Direct link to Claude Desktop")

Add to your Claude Desktop configuration (`~/Library/Application Support/Claude/config.json` on macOS):

    {  "mcpServers": {    "oh-my-posh-validator": {      "url": "https://ohmyposh.dev/api/mcp",      "transport": "http"    }  }}

Then ask Claude: "Can you validate this oh-my-posh configuration for me?" and paste your config.

### Cline (VS Code Extension)[​](https://ohmyposh.dev/docs/advanced/mcp-server#cline-vs-code-extension "Direct link to Cline (VS Code Extension)")

Configure Cline to use the MCP server, and it will automatically validate configurations when you're working on oh-my-posh themes.

Supported Formats[​](https://ohmyposh.dev/docs/advanced/mcp-server#supported-formats "Direct link to Supported Formats")

-------------------------------------------------------------------------------------------------------------------------

### JSON[​](https://ohmyposh.dev/docs/advanced/mcp-server#json "Direct link to JSON")

    {  "$schema": "https://raw.githubusercontent.com/JanDeDobbeleer/oh-my-posh/main/themes/schema.json",  "version": 4,  "blocks": []}

### YAML[​](https://ohmyposh.dev/docs/advanced/mcp-server#yaml "Direct link to YAML")

    $schema: https://raw.githubusercontent.com/JanDeDobbeleer/oh-my-posh/main/themes/schema.jsonversion: 4blocks: []

### TOML[​](https://ohmyposh.dev/docs/advanced/mcp-server#toml "Direct link to TOML")

    version = 4blocks = []

Privacy & Security[​](https://ohmyposh.dev/docs/advanced/mcp-server#privacy--security "Direct link to Privacy & Security")

---------------------------------------------------------------------------------------------------------------------------

*   Your configuration content is **not stored** or logged
*   All validation is done in-memory and discarded after processing
*   The server only reads the official schema from the repository
*   No authentication required - fully anonymous

Source Code[​](https://ohmyposh.dev/docs/advanced/mcp-server#source-code "Direct link to Source Code")

-------------------------------------------------------------------------------------------------------

The MCP server is open source and part of the oh-my-posh repository:

*   [MCP Server Function](https://github.com/JanDeDobbeleer/oh-my-posh/blob/main/website/api/mcp)
    
*   [Validator Module](https://github.com/JanDeDobbeleer/oh-my-posh/blob/main/website/api/shared/validator.js)
    

Troubleshooting[​](https://ohmyposh.dev/docs/advanced/mcp-server#troubleshooting "Direct link to Troubleshooting")

-------------------------------------------------------------------------------------------------------------------

### Format Not Detected Correctly[​](https://ohmyposh.dev/docs/advanced/mcp-server#format-not-detected-correctly "Direct link to Format Not Detected Correctly")

If auto-detection fails, explicitly specify the format:

    {  "arguments": {    "content": "...",    "format": "yaml"  }}

### Parse Errors[​](https://ohmyposh.dev/docs/advanced/mcp-server#parse-errors "Direct link to Parse Errors")

If you get parse errors, check that your configuration is valid JSON/YAML/TOML syntax before validating the schema.

### Schema Errors[​](https://ohmyposh.dev/docs/advanced/mcp-server#schema-errors "Direct link to Schema Errors")

The validator uses the latest schema from the main branch. If you're using an older oh-my-posh version, some newer properties might not be recognized.

Contributing[​](https://ohmyposh.dev/docs/advanced/mcp-server#contributing "Direct link to Contributing")

----------------------------------------------------------------------------------------------------------

Found a bug or have a suggestion? Please [open an issue](https://github.com/JanDeDobbeleer/oh-my-posh/issues)
 on GitHub.

*   [What is the Oh My Posh MCP Server?](https://ohmyposh.dev/docs/advanced/mcp-server#what-is-the-oh-my-posh-mcp-server)
    
*   [Features](https://ohmyposh.dev/docs/advanced/mcp-server#features)
    
*   [Usage](https://ohmyposh.dev/docs/advanced/mcp-server#usage)
    *   [With MCP Clients](https://ohmyposh.dev/docs/advanced/mcp-server#with-mcp-clients)
        
    *   [Direct HTTP API](https://ohmyposh.dev/docs/advanced/mcp-server#direct-http-api)
        
*   [Tool Parameters](https://ohmyposh.dev/docs/advanced/mcp-server#tool-parameters)
    *   [validate\_config](https://ohmyposh.dev/docs/advanced/mcp-server#validate_config)
        
*   [Response Fields](https://ohmyposh.dev/docs/advanced/mcp-server#response-fields)
    
*   [Error Format](https://ohmyposh.dev/docs/advanced/mcp-server#error-format)
    
*   [Examples](https://ohmyposh.dev/docs/advanced/mcp-server#examples)
    *   [Valid Configuration](https://ohmyposh.dev/docs/advanced/mcp-server#valid-configuration)
        
    *   [Invalid Configuration Example](https://ohmyposh.dev/docs/advanced/mcp-server#invalid-configuration-example)
        
*   [Integration Examples](https://ohmyposh.dev/docs/advanced/mcp-server#integration-examples)
    *   [Claude Desktop](https://ohmyposh.dev/docs/advanced/mcp-server#claude-desktop)
        
    *   [Cline (VS Code Extension)](https://ohmyposh.dev/docs/advanced/mcp-server#cline-vs-code-extension)
        
*   [Supported Formats](https://ohmyposh.dev/docs/advanced/mcp-server#supported-formats)
    *   [JSON](https://ohmyposh.dev/docs/advanced/mcp-server#json)
        
    *   [YAML](https://ohmyposh.dev/docs/advanced/mcp-server#yaml)
        
    *   [TOML](https://ohmyposh.dev/docs/advanced/mcp-server#toml)
        
*   [Privacy & Security](https://ohmyposh.dev/docs/advanced/mcp-server#privacy--security)
    
*   [Source Code](https://ohmyposh.dev/docs/advanced/mcp-server#source-code)
    
*   [Troubleshooting](https://ohmyposh.dev/docs/advanced/mcp-server#troubleshooting)
    *   [Format Not Detected Correctly](https://ohmyposh.dev/docs/advanced/mcp-server#format-not-detected-correctly)
        
    *   [Parse Errors](https://ohmyposh.dev/docs/advanced/mcp-server#parse-errors)
        
    *   [Schema Errors](https://ohmyposh.dev/docs/advanced/mcp-server#schema-errors)
        
*   [Contributing](https://ohmyposh.dev/docs/advanced/mcp-server#contributing)