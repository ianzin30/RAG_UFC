Source URL: https://ohmyposh.dev/docs/dsc

[Skip to main content](https://ohmyposh.dev/docs/dsc#__docusaurus_skipToContent_fallback)

If you're enjoying Oh My Posh, consider becoming a [sponsor](https://github.com/sponsors/JanDeDobbeleer)
 to keep the project going strong 💪

On this page

Oh My Posh supports Desired State Configuration (DSC) for declarative configuration management, enabling automated deployment and consistent configuration across multiple systems.

Concept[​](https://ohmyposh.dev/docs/dsc#concept "Direct link to Concept")

---------------------------------------------------------------------------

Oh My Posh DSC builds on the traditional Oh My Posh configuration approach by adding automation and orchestration capabilities. Instead of manually configuring your prompt, you can define the desired state declaratively and let DSC ensure your system matches that state.

DSC works with **resources** that represent different aspects of your Oh My Posh setup:

*   **Configuration Resource**: Manages your Oh My Posh configuration files
*   **Shell Resource**: Handles shell initialization and integration
*   **Font Resource**: Tracks installed Nerd Fonts

These resources can be used standalone through the CLI or integrated with orchestration tools like WinGet and Microsoft DSC for automated deployments.

Overview[​](https://ohmyposh.dev/docs/dsc#overview "Direct link to Overview")

------------------------------------------------------------------------------

DSC support in Oh My Posh provides:

*   **Declarative configuration**: Define the desired state of your Oh My Posh setup
*   **Automated deployment**: Configure Oh My Posh as part of system provisioning workflows
*   **Shell integration**: Automatically configure shell initialization for bash, zsh, fish, PowerShell, and more
*   **Font management**: Track installed Nerd Fonts through DSC state
*   **Orchestration support**: Integration with WinGet and Microsoft DSC tools

DSC functionality is available through the `oh-my-posh` CLI and can be used standalone or with orchestration tools.

DSC Resources[​](https://ohmyposh.dev/docs/dsc#dsc-resources "Direct link to DSC Resources")

---------------------------------------------------------------------------------------------

Oh My Posh provides the following DSC resources:

### Configuration Resource[​](https://ohmyposh.dev/docs/dsc#configuration-resource "Direct link to Configuration Resource")

Manages Oh My Posh configuration files.

**Operations**: `get`, `set`, `export`, `schema`

    # Get current configuration stateoh-my-posh config dsc get# Apply a configurationoh-my-posh config dsc set --state '{"states":[{"source":"~/mytheme.omp.json","format":"json"}]}'# Get configuration schemaoh-my-posh config dsc schema

### Shell Resource[​](https://ohmyposh.dev/docs/dsc#shell-resource "Direct link to Shell Resource")

Manages shell initialization and integration.

**Operations**: `get`, `set`, `export`, `schema`

    # Get current shell configurationsoh-my-posh init bash dsc get# Configure shell initializationoh-my-posh init bash dsc set --state '{"states":[{"name":"bash","command":"oh-my-posh init bash --config ~/mytheme.omp.json"}]}'

### Font Resource[​](https://ohmyposh.dev/docs/dsc#font-resource "Direct link to Font Resource")

Tracks Nerd Fonts installed through Oh My Posh.

**Operations**: `get`, `export`, `schema`

    # Get installed fontsoh-my-posh font dsc get# Get font schemaoh-my-posh font dsc schema

Direct CLI Usage[​](https://ohmyposh.dev/docs/dsc#direct-cli-usage "Direct link to Direct CLI Usage")

------------------------------------------------------------------------------------------------------

You can use the DSC commands directly from the command line for configuration management.

### Managing Configurations[​](https://ohmyposh.dev/docs/dsc#managing-configurations "Direct link to Managing Configurations")

#### Get State[​](https://ohmyposh.dev/docs/dsc#get-state "Direct link to Get State")

Retrieve the current configuration state:

    oh-my-posh config dsc get

Example output:

    {  "states": [    {      "format": "json",      "source": "~/mytheme.omp.json"    }  ]}

#### Set State[​](https://ohmyposh.dev/docs/dsc#set-state "Direct link to Set State")

Apply a new configuration state:

    oh-my-posh config dsc set --state '{"states":[{"source":"~/mytheme.omp.json","format":"json"}]}'

This creates or updates the configuration file at the specified location with the provided format.

#### Schema[​](https://ohmyposh.dev/docs/dsc#schema "Direct link to Schema")

Get the JSON schema for the configuration resource:

    oh-my-posh config dsc schema

Use this to understand the structure and available options for configuration states.

### Managing shell Integration[​](https://ohmyposh.dev/docs/dsc#managing-shell-integration "Direct link to Managing shell Integration")

#### Bash[​](https://ohmyposh.dev/docs/dsc#bash "Direct link to Bash")

Configure Oh My Posh initialization for bash:

    # Get current stateoh-my-posh init bash dsc get# Set initializationoh-my-posh init bash dsc set --state '{"states":[{"name":"bash","command":"oh-my-posh init bash --config ~/mytheme.omp.json"}]}'

This automatically updates your `.bashrc` or `.bash_profile` with the Oh My Posh initialization command.

#### Zsh[​](https://ohmyposh.dev/docs/dsc#zsh "Direct link to Zsh")

Configure Oh My Posh initialization for zsh:

    # Get current stateoh-my-posh init zsh dsc get# Set initializationoh-my-posh init zsh dsc set --state '{"states":[{"name":"zsh","command":"oh-my-posh init zsh --config ~/mytheme.omp.json"}]}'

This automatically updates your `.zshrc` with the Oh My Posh initialization command.

#### PowerShell[​](https://ohmyposh.dev/docs/dsc#powershell "Direct link to PowerShell")

Configure Oh My Posh initialization for PowerShell:

    # Get current stateoh-my-posh init pwsh dsc get# Set initializationoh-my-posh init pwsh dsc set --state '{"states":[{"name":"pwsh","command":"oh-my-posh init pwsh --config ~/mytheme.omp.json"}]}'

This automatically updates your PowerShell profile with the Oh My Posh initialization command.

#### Fish[​](https://ohmyposh.dev/docs/dsc#fish "Direct link to Fish")

Configure Oh My Posh initialization for fish:

    # Get current stateoh-my-posh init fish dsc get# Set initializationoh-my-posh init fish dsc set --state '{"states":[{"name":"fish","command":"oh-my-posh init fish --config ~/mytheme.omp.json"}]}'

This automatically updates your fish `config.fish` with the Oh My Posh initialization command.

Orchestration with WinGet[​](https://ohmyposh.dev/docs/dsc#orchestration-with-winget "Direct link to Orchestration with WinGet")

---------------------------------------------------------------------------------------------------------------------------------

WinGet configuration enables you to install Oh My Posh and apply configuration in a single declarative file.

### Basic WinGet configuration[​](https://ohmyposh.dev/docs/dsc#basic-winget-configuration "Direct link to Basic WinGet configuration")

Create a configuration file to install and configure Oh My Posh:

oh-my-posh-setup.yaml

    $schema: https://raw.githubusercontent.com/PowerShell/DSC/main/schemas/v3/config/document.jsonmetadata:  winget:    processor: dscv3resources:  - name: Install Oh My Posh    type: Microsoft.WinGet.DSC/WinGetPackage    properties:      id: JanDeDobbeleer.OhMyPosh      source: winget

Apply the configuration:

    winget configure oh-my-posh-setup.yaml

### Complete setup with configuration and shell[​](https://ohmyposh.dev/docs/dsc#complete-setup-with-configuration-and-shell "Direct link to Complete setup with configuration and shell")

This example installs Oh My Posh, adds your configuration, and initializes PowerShell:

oh-my-posh-complete.yaml

    $schema: https://raw.githubusercontent.com/PowerShell/DSC/main/schemas/v3/config/document.jsonmetadata:  winget:    processor: dscv3resources:  - name: Install Oh My Posh    type: Microsoft.WinGet.DSC/WinGetPackage    properties:      id: JanDeDobbeleer.OhMyPosh      source: winget  - name: Add Oh My Posh configuration    type: OhMyPosh/Config    properties:      states:        - source: ~/mytheme.omp.json          format: json  - name: Initialize PowerShell    type: OhMyPosh/Shell    properties:      states:        - name: pwsh          command: oh-my-posh init pwsh --config ~/mytheme.omp.json

Apply with:

    winget configure oh-my-posh-complete.yaml

### Multi-shell configuration[​](https://ohmyposh.dev/docs/dsc#multi-shell-configuration "Direct link to Multi-shell configuration")

Initialize multiple shells with different configurations:

oh-my-posh-multi-shell.yaml

    $schema: https://raw.githubusercontent.com/PowerShell/DSC/main/schemas/v3/config/document.jsonmetadata:  winget:    processor: dscv3resources:  - name: Install Oh My Posh    type: Microsoft.WinGet.DSC/WinGetPackage    properties:      id: JanDeDobbeleer.OhMyPosh      source: winget  - name: Add work configuration    type: OhMyPosh/Config    properties:      states:        - source: ~/work-theme.omp.json          format: json  - name: Add personal configuration    type: OhMyPosh/Config    properties:      states:        - source: ~/personal-theme.omp.json          format: json  - name: Initialize PowerShell with work configuration    type: OhMyPosh/Shell    properties:      states:        - name: pwsh          command: oh-my-posh init pwsh --config ~/work-theme.omp.json  - name: Initialize Bash with personal configuration    type: OhMyPosh/Shell    properties:      states:        - name: bash          command: oh-my-posh init bash --config ~/personal-theme.omp.json

Orchestration with Microsoft DSC[​](https://ohmyposh.dev/docs/dsc#orchestration-with-microsoft-dsc "Direct link to Orchestration with Microsoft DSC")

------------------------------------------------------------------------------------------------------------------------------------------------------

Microsoft DSC (`dsc`) provides cross-platform configuration management capabilities. Oh My Posh provides native DSC resources that can be used in DSC configuration documents.

### Example DSC configuration[​](https://ohmyposh.dev/docs/dsc#example-dsc-configuration "Direct link to Example DSC configuration")

Create a configuration document for Oh My Posh:

oh-my-posh-dsc.yaml

    $schema: https://aka.ms/dsc/schemas/v3/bundled/config/document.jsonresources:  - name: Add Oh My Posh configuration    type: OhMyPosh/Config    properties:      states:        - source: ~/mytheme.omp.json          format: json  - name: Initialize PowerShell    type: OhMyPosh/Shell    properties:      states:        - name: pwsh          command: oh-my-posh init pwsh --config ~/mytheme.omp.json

Apply the configuration using the `dsc` CLI:

    dsc config set --document oh-my-posh-dsc.yaml

### Complete configuration with multiple shells[​](https://ohmyposh.dev/docs/dsc#complete-configuration-with-multiple-shells "Direct link to Complete configuration with multiple shells")

oh-my-posh-complete-dsc.yaml

    $schema: https://aka.ms/dsc/schemas/v3/bundled/config/document.jsonresources:  - name: Add primary configuration    type: OhMyPosh/Config    properties:      states:        - source: ~/primary-theme.omp.json          format: json  - name: Add secondary configuration    type: OhMyPosh/Config    properties:      states:        - source: ~/secondary-theme.omp.json          format: yaml  - name: Initialize PowerShell    type: OhMyPosh/Shell    properties:      states:        - name: pwsh          command: oh-my-posh init pwsh --config ~/primary-theme.omp.json  - name: Initialize Bash    type: OhMyPosh/Shell    properties:      states:        - name: bash          command: oh-my-posh init bash --config ~/primary-theme.omp.json  - name: Initialize Zsh    type: OhMyPosh/Shell    properties:      states:        - name: zsh          command: oh-my-posh init zsh --config ~/secondary-theme.omp.json

### Resource Types[​](https://ohmyposh.dev/docs/dsc#resource-types "Direct link to Resource Types")

Oh My Posh provides the following DSC resource types:

#### OhMyPosh/Config[​](https://ohmyposh.dev/docs/dsc#ohmyposhconfig "Direct link to OhMyPosh/Config")

Manages Oh My Posh configuration files.

**Properties:**

*   `states` (array): List of configuration states
    *   `source` (string): Path to the configuration file
    *   `format` (string): Format of the configuration file (`json`, `yaml`, `toml`)

#### OhMyPosh/Shell[​](https://ohmyposh.dev/docs/dsc#ohmyposhshell "Direct link to OhMyPosh/Shell")

Manages shell initialization.

**Properties:**

*   `states` (array): List of shell configurations
    *   `name` (string): Shell name (`bash`, `zsh`, `pwsh`, `fish`, etc.)
    *   `command` (string): Oh My Posh initialization command

#### OhMyPosh/Font[​](https://ohmyposh.dev/docs/dsc#ohmyposhfont "Direct link to OhMyPosh/Font")

Tracks installed Nerd Fonts. This resource is read-only and automatically populated when fonts are installed through Oh My Posh.

Configuration State Management[​](https://ohmyposh.dev/docs/dsc#configuration-state-management "Direct link to Configuration State Management")

------------------------------------------------------------------------------------------------------------------------------------------------

DSC state is stored in the Oh My Posh cache and persists across sessions. This enables:

*   **State tracking**: Oh My Posh remembers configurations set through DSC
*   **Idempotency**: Running the same DSC command multiple times produces the same result
*   **State validation**: Query current state before making changes

Advanced Usage[​](https://ohmyposh.dev/docs/dsc#advanced-usage "Direct link to Advanced Usage")

------------------------------------------------------------------------------------------------

### Multiple configurations[​](https://ohmyposh.dev/docs/dsc#multiple-configurations "Direct link to Multiple configurations")

You can manage multiple configuration files:

    oh-my-posh config dsc set --state '{  "states": [    {"source":"~/work.omp.json","format":"json"},    {"source":"~/personal.omp.json","format":"json"}  ]}'

### Shell-Specific Initialization[​](https://ohmyposh.dev/docs/dsc#shell-specific-initialization "Direct link to Shell-Specific Initialization")

Initialize multiple shells with different configuration:

    # Bash with one configurationoh-my-posh init bash dsc set --state '{"states":[{"name":"bash","command":"oh-my-posh init bash --config ~/bash-theme.omp.json"}]}'# PowerShell with another configurationoh-my-posh init pwsh dsc set --state '{"states":[{"name":"pwsh","command":"oh-my-posh init pwsh --config ~/pwsh-theme.omp.json"}]}'

Supported shells[​](https://ohmyposh.dev/docs/dsc#supported-shells "Direct link to Supported shells")

------------------------------------------------------------------------------------------------------

DSC shell configuration supports the following shells:

*   **bash**: Configures `.bashrc` or `.bash_profile`
*   **zsh**: Configures `.zshrc`
*   **fish**: Configures `~/.config/fish/config.fish`
*   **pwsh**: Configures PowerShell profile (`$PROFILE`)
*   **nu**: Configures `~/.config/nushell/config.nu`
*   **elvish**: Configures `.elvish/rc.elv`
*   **xonsh**: Configures `.xonshrc`

The shell integration automatically:

*   Creates configuration files if they don't exist
*   Updates existing Oh My Posh initialization commands
*   Preserves shell-specific command syntax
*   Maintains proper whitespace and formatting

See Also[​](https://ohmyposh.dev/docs/dsc#see-also "Direct link to See Also")

------------------------------------------------------------------------------

*   [General configuration](https://ohmyposh.dev/docs/configuration/general)
     - Main configuration documentation
*   [Installation](https://ohmyposh.dev/docs/installation/windows)
     - Installing Oh My Posh
*   [Themes](https://github.com/JanDeDobbeleer/oh-my-posh/tree/main/themes)
     - Available themes
*   [WinGet configuration](https://learn.microsoft.com/windows/package-manager/configuration/)
     - WinGet DSC documentation
*   [Microsoft DSC](https://learn.microsoft.com/powershell/dsc/overview)
     - Microsoft DSC documentation

*   [Concept](https://ohmyposh.dev/docs/dsc#concept)
    
*   [Overview](https://ohmyposh.dev/docs/dsc#overview)
    
*   [DSC Resources](https://ohmyposh.dev/docs/dsc#dsc-resources)
    *   [Configuration Resource](https://ohmyposh.dev/docs/dsc#configuration-resource)
        
    *   [Shell Resource](https://ohmyposh.dev/docs/dsc#shell-resource)
        
    *   [Font Resource](https://ohmyposh.dev/docs/dsc#font-resource)
        
*   [Direct CLI Usage](https://ohmyposh.dev/docs/dsc#direct-cli-usage)
    *   [Managing Configurations](https://ohmyposh.dev/docs/dsc#managing-configurations)
        
    *   [Managing shell Integration](https://ohmyposh.dev/docs/dsc#managing-shell-integration)
        
*   [Orchestration with WinGet](https://ohmyposh.dev/docs/dsc#orchestration-with-winget)
    *   [Basic WinGet configuration](https://ohmyposh.dev/docs/dsc#basic-winget-configuration)
        
    *   [Complete setup with configuration and shell](https://ohmyposh.dev/docs/dsc#complete-setup-with-configuration-and-shell)
        
    *   [Multi-shell configuration](https://ohmyposh.dev/docs/dsc#multi-shell-configuration)
        
*   [Orchestration with Microsoft DSC](https://ohmyposh.dev/docs/dsc#orchestration-with-microsoft-dsc)
    *   [Example DSC configuration](https://ohmyposh.dev/docs/dsc#example-dsc-configuration)
        
    *   [Complete configuration with multiple shells](https://ohmyposh.dev/docs/dsc#complete-configuration-with-multiple-shells)
        
    *   [Resource Types](https://ohmyposh.dev/docs/dsc#resource-types)
        
*   [Configuration State Management](https://ohmyposh.dev/docs/dsc#configuration-state-management)
    
*   [Advanced Usage](https://ohmyposh.dev/docs/dsc#advanced-usage)
    *   [Multiple configurations](https://ohmyposh.dev/docs/dsc#multiple-configurations)
        
    *   [Shell-Specific Initialization](https://ohmyposh.dev/docs/dsc#shell-specific-initialization)
        
*   [Supported shells](https://ohmyposh.dev/docs/dsc#supported-shells)
    
*   [See Also](https://ohmyposh.dev/docs/dsc#see-also)