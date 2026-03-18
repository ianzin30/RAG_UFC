Source URL: https://ohmyposh.dev/docs/segments/cli/copilot

[Skip to main content](https://ohmyposh.dev/docs/segments/cli/copilot#__docusaurus_skipToContent_fallback)

If you're enjoying Oh My Posh, consider becoming a [sponsor](https://github.com/sponsors/JanDeDobbeleer)
 to keep the project going strong 💪

On this page

What[​](https://ohmyposh.dev/docs/segments/cli/copilot#what "Direct link to What")

-----------------------------------------------------------------------------------

Display your [GitHub Copilot](https://github.com/features/copilot)
 usage statistics and quota information including premium interactions, inline completions, and chat usage. This segment was inspired by [Elio Struyf's GitHub Copilot Usage Tauri application](https://github.com/estruyf/github-copilot-usage-tauri)
.

Authentication[​](https://ohmyposh.dev/docs/segments/cli/copilot#authentication "Direct link to Authentication")

-----------------------------------------------------------------------------------------------------------------

This segment requires authentication with GitHub to access Copilot usage data. Use the built-in OAuth device code flow:

    oh-my-posh auth copilot

This will:

1.  Display a device code and verification URL
2.  Open your browser to GitHub's authorization page
3.  Prompt you to enter the device code
4.  Store the access token securely for future use

The token is stored securely and will be used automatically by the segment.

Sample Configuration[​](https://ohmyposh.dev/docs/segments/cli/copilot#sample-configuration "Direct link to Sample Configuration")

-----------------------------------------------------------------------------------------------------------------------------------

*   json
*   yaml
*   toml

    {  "type": "copilot",  "style": "diamond",  "leading_diamond": "",  "trailing_diamond": "",  "foreground": "#111111",  "background": "#fee898",  "template": "  {{ .Premium.Percent.Gauge }} ",  "cache": {    "duration": "5m",    "strategy": "session"  },  "options": {    "http_timeout": 1000  }}

    type: copilotstyle: diamondleading_diamond: trailing_diamond: foreground: "#111111"background: "#fee898"template: "  {{ .Premium.Percent.Gauge }} "cache:  duration: 5m  strategy: sessionoptions:  http_timeout: 1000

    type = "copilot"style = "diamond"leading_diamond = ""trailing_diamond = ""foreground = "#111111"background = "#fee898"template = "  {{ .Premium.Percent.Gauge }} "[cache]duration = "5m"strategy = "session"[options]http_timeout = 1000

Options[​](https://ohmyposh.dev/docs/segments/cli/copilot#options "Direct link to Options")

--------------------------------------------------------------------------------------------

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `http_timeout` | `int` | `20` | The default timeout for HTTP requests in milliseconds |

Template ([info](https://ohmyposh.dev/docs/configuration/templates)
)[​](https://ohmyposh.dev/docs/segments/cli/copilot#template-info "Direct link to template-info")

----------------------------------------------------------------------------------------------------------------------------------------------------------------------

default template

     \uec1e {{ .Premium.Percent.Gauge }}

### Properties[​](https://ohmyposh.dev/docs/segments/cli/copilot#properties "Direct link to Properties")

| Name | Type | Description |
| --- | --- | --- |
| `.Premium` | `CopilotUsage` | Premium interactions usage data |
| `.Premium.Used` | `int` | Number of premium interactions used |
| `.Premium.Limit` | `int` | Total premium interactions available |
| `.Premium.Percent` | `Percentage` | Percentage of premium quota used (0-100) |
| `.Premium.Remaining` | `Percentage` | Percentage of premium quota remaining (0-100) |
| `.Premium.Unlimited` | `bool` | Whether premium quota is unlimited |
| `.Inline` | `CopilotUsage` | Inline completions usage data |
| `.Inline.Used` | `int` | Number of inline completions used |
| `.Inline.Limit` | `int` | Total inline completions available |
| `.Inline.Percent` | `Percentage` | Percentage of inline quota used (0-100) |
| `.Inline.Remaining` | `Percentage` | Percentage of inline quota remaining (0-100) |
| `.Inline.Unlimited` | `bool` | Whether inline quota is unlimited |
| `.Chat` | `CopilotUsage` | Chat usage data |
| `.Chat.Used` | `int` | Number of chat interactions used |
| `.Chat.Limit` | `int` | Total chat interactions available |
| `.Chat.Percent` | `Percentage` | Percentage of chat quota used (0-100) |
| `.Chat.Remaining` | `Percentage` | Percentage of chat quota remaining (0-100) |
| `.Chat.Unlimited` | `bool` | Whether chat quota is unlimited |
| `.BillingCycleEnd` | `string` | End date of current billing cycle |

### Percentage Methods[​](https://ohmyposh.dev/docs/segments/cli/copilot#percentage-methods "Direct link to Percentage Methods")

The `Percentage` type provides additional functionality beyond just the numeric value:

| Method | Returns | Description |
| --- | --- | --- |
| `.Gauge()` | `string` | Visual gauge showing remaining capacity using 5 bar blocks (▰▰▰▰▱) |
| `.GaugeUsed()` | `string` | Visual gauge showing used capacity using 5 bar blocks (▰▱▱▱▱) |
| `.String()` | `string` | Numeric percentage value (e.g., "75" for use in templates) |

**Example gauge visualization (shows remaining capacity):**

*   0% used (100% remaining): `▰▰▰▰▰`
*   20% used (80% remaining): `▰▰▰▰▱`
*   40% used (60% remaining): `▰▰▰▱▱`
*   60% used (40% remaining): `▰▰▱▱▱`
*   80% used (20% remaining): `▰▱▱▱▱`
*   100% used (0% remaining): `▱▱▱▱▱`

**Example gaugeUsed visualization (shows used capacity):**

*   0% used: `▱▱▱▱▱`
*   20% used: `▰▱▱▱▱`
*   40% used: `▰▰▱▱▱`
*   60% used: `▰▰▰▱▱`
*   80% used: `▰▰▰▰▱`
*   100% used: `▰▰▰▰▰`

**Example template with gauge:**

    "template": "{{ .Premium.Percent.Gauge() }} {{ .Premium.Used }}/{{ .Premium.Limit }}"

**Example template showing used capacity:**

    "template": "{{ .Premium.Percent.GaugeUsed() }} {{ .Premium.Used }}/{{ .Premium.Limit }}"

*   [What](https://ohmyposh.dev/docs/segments/cli/copilot#what)
    
*   [Authentication](https://ohmyposh.dev/docs/segments/cli/copilot#authentication)
    
*   [Sample Configuration](https://ohmyposh.dev/docs/segments/cli/copilot#sample-configuration)
    
*   [Options](https://ohmyposh.dev/docs/segments/cli/copilot#options)
    
*   [Template (info)](https://ohmyposh.dev/docs/segments/cli/copilot#template-info)
    *   [Properties](https://ohmyposh.dev/docs/segments/cli/copilot#properties)
        
    *   [Percentage Methods](https://ohmyposh.dev/docs/segments/cli/copilot#percentage-methods)