Source URL: https://ohmyposh.dev/docs/segments/cli/claude

[Skip to main content](https://ohmyposh.dev/docs/segments/cli/claude#__docusaurus_skipToContent_fallback)

If you're enjoying Oh My Posh, consider becoming a [sponsor](https://github.com/sponsors/JanDeDobbeleer)
 to keep the project going strong 💪

On this page

What[​](https://ohmyposh.dev/docs/segments/cli/claude#what "Direct link to What")

----------------------------------------------------------------------------------

Display Claude Code session information including the current AI model, token usage, costs, and workspace details. Shows a visual gauge of context window usage and formatted cost/token information for monitoring your Claude usage.

This segment integrates with [Claude Code's statusline functionality](https://code.claude.com/docs/en/statusline)
 to provide real-time session data in your prompt.

Sample Configuration[​](https://ohmyposh.dev/docs/segments/cli/claude#sample-configuration "Direct link to Sample Configuration")

----------------------------------------------------------------------------------------------------------------------------------

*   json
*   yaml
*   toml

    {  "type": "claude",  "style": "diamond",  "leading_diamond": "",  "trailing_diamond": "",  "foreground": "#FFFFFF",  "background": "#FF6B35",  "template": " 󰯉 {{ .Model.DisplayName }}  {{ .TokenUsagePercent.Gauge }} "}

    type: claudestyle: diamondleading_diamond: trailing_diamond: foreground: "#FFFFFF"background: "#FF6B35"template: " 󰯉 {{ .Model.DisplayName }}  {{ .TokenUsagePercent.Gauge }} "

    type = "claude"style = "diamond"leading_diamond = ""trailing_diamond = ""foreground = "#FFFFFF"background = "#FF6B35"template = " 󰯉 {{ .Model.DisplayName }}  {{ .TokenUsagePercent.Gauge }} "

Template ([info](https://ohmyposh.dev/docs/configuration/templates)
)[​](https://ohmyposh.dev/docs/segments/cli/claude#template-info "Direct link to template-info")

---------------------------------------------------------------------------------------------------------------------------------------------------------------------

default template

     \udb82\udfc9 {{ .Model.DisplayName }} \uf2d0 {{ .TokenUsagePercent.Gauge }}

### Properties[​](https://ohmyposh.dev/docs/segments/cli/claude#properties "Direct link to Properties")

| Name | Type | Description |
| --- | --- | --- |
| `.SessionID` | `string` | Unique identifier for the Claude session |
| `.Model` | `Model` | AI model information |
| `.Workspace` | `Workspace` | Workspace directory information |
| `.Cost` | `Cost` | Cost and duration information |
| `.ContextWindow` | `ContextWindow` | Token usage information |
| `.TokenUsagePercent` | `Percentage` | Percentage of context window used (0-100) |
| `.FormattedCost` | `string` | Formatted cost string (e.g., "$0.15" or "$0.0012") |
| `.FormattedTokens` | `string` | Human-readable token count (e.g., "1.2K", "15.3M") |

#### Model Properties[​](https://ohmyposh.dev/docs/segments/cli/claude#model-properties "Direct link to Model Properties")

| Name | Type | Description |
| --- | --- | --- |
| `.ID` | `string` | Technical model identifier |
| `.DisplayName` | `string` | Human-readable model name (e.g., "Claude 3.5 Sonnet") |

#### Workspace Properties[​](https://ohmyposh.dev/docs/segments/cli/claude#workspace-properties "Direct link to Workspace Properties")

| Name | Type | Description |
| --- | --- | --- |
| `.CurrentDir` | `string` | Current working directory |
| `.ProjectDir` | `string` | Root project directory |

#### Cost Properties[​](https://ohmyposh.dev/docs/segments/cli/claude#cost-properties "Direct link to Cost Properties")

| Name | Type | Description |
| --- | --- | --- |
| `.TotalCostUSD` | `float64` | Total cost in USD |
| `.TotalDurationMS` | `int64` | Total session duration in milliseconds |

#### ContextWindow Properties[​](https://ohmyposh.dev/docs/segments/cli/claude#contextwindow-properties "Direct link to ContextWindow Properties")

| Name | Type | Description |
| --- | --- | --- |
| `.TotalInputTokens` | `int` | Total input tokens used in the session |
| `.TotalOutputTokens` | `int` | Total output tokens generated in the session |
| `.ContextWindowSize` | `int` | Maximum context window size for the model |
| `.CurrentUsage` | `CurrentUsage` | Current message token usage |

#### CurrentUsage Properties[​](https://ohmyposh.dev/docs/segments/cli/claude#currentusage-properties "Direct link to CurrentUsage Properties")

| Name | Type | Description |
| --- | --- | --- |
| `.InputTokens` | `int` | Input tokens for the current message |
| `.OutputTokens` | `int` | Output tokens for the current message |

### Percentage Methods[​](https://ohmyposh.dev/docs/segments/cli/claude#percentage-methods "Direct link to Percentage Methods")

The `TokenUsagePercent` property is a `Percentage` type that provides additional functionality:

| Method | Returns | Description |
| --- | --- | --- |
| `.Gauge` | `string` | Visual gauge showing remaining capacity using 5 bar blocks (▰▰▰▰▱) |
| `.GaugeUsed` | `string` | Visual gauge showing used capacity using 5 bar blocks (▰▱▱▱▱) |
| `.String` | `string` | Numeric percentage value (e.g., "75" for use in templates) |

How it works[​](https://ohmyposh.dev/docs/segments/cli/claude#how-it-works "Direct link to How it works")

----------------------------------------------------------------------------------------------------------

The segment reads session information from the `POSH_CLAUDE_STATUS` environment variable, which is automatically set when using the `oh-my-posh claude` command. The data includes:

*   Current AI model information
*   Token usage and context window utilization
*   Session costs and duration
*   Workspace directory information

The segment only displays when Claude Code is actively providing session data.

*   [What](https://ohmyposh.dev/docs/segments/cli/claude#what)
    
*   [Sample Configuration](https://ohmyposh.dev/docs/segments/cli/claude#sample-configuration)
    
*   [Template (info)](https://ohmyposh.dev/docs/segments/cli/claude#template-info)
    *   [Properties](https://ohmyposh.dev/docs/segments/cli/claude#properties)
        
    *   [Percentage Methods](https://ohmyposh.dev/docs/segments/cli/claude#percentage-methods)
        
*   [How it works](https://ohmyposh.dev/docs/segments/cli/claude#how-it-works)