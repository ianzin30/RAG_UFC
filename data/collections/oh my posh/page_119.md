Source URL: https://ohmyposh.dev/docs/segments/system/connection

[Skip to main content](https://ohmyposh.dev/docs/segments/system/connection#__docusaurus_skipToContent_fallback)

If you're enjoying Oh My Posh, consider becoming a [sponsor](https://github.com/sponsors/JanDeDobbeleer)
 to keep the project going strong 💪

On this page

What[​](https://ohmyposh.dev/docs/segments/system/connection#what "Direct link to What")

-----------------------------------------------------------------------------------------

Show details about the currently connected network.

info

Currently only supports Windows. Pull requests for Darwin and Linux support are welcome :)

Sample Configuration[​](https://ohmyposh.dev/docs/segments/system/connection#sample-configuration "Direct link to Sample Configuration")

-----------------------------------------------------------------------------------------------------------------------------------------

*   json
*   yaml
*   toml

    {  "type": "connection",  "style": "powerline",  "background": "#8822ee",  "foreground": "#222222",  "powerline_symbol": ""}

    type: connectionstyle: powerlinebackground: "#8822ee"foreground: "#222222"powerline_symbol: 

    type = "connection"style = "powerline"background = "#8822ee"foreground = "#222222"powerline_symbol = ""

Options[​](https://ohmyposh.dev/docs/segments/system/connection#options "Direct link to Options")

--------------------------------------------------------------------------------------------------

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `type` | `string` | `wifi\|ethernet` | the type of connection to display. Can be a single value or multiple joined by a pipe \| . The first to resolve is shown. Possible values:<br><br>*   `wifi`<br>*   `ethernet`<br>*   `bluetooth`<br>*   `cellular` |

Template ([info](https://ohmyposh.dev/docs/configuration/templates)
)[​](https://ohmyposh.dev/docs/segments/system/connection#template-info "Direct link to template-info")

----------------------------------------------------------------------------------------------------------------------------------------------------------------------------

default template

     {{ if eq .Type \"wifi\"}}\uf1eb{{ else if eq .Type \"ethernet\"}}\ueba9{{ end }}

### Properties[​](https://ohmyposh.dev/docs/segments/system/connection#properties "Direct link to Properties")

| Name | Type | Description |
| --- | --- | --- |
| `.Type` | `string` | the connection type type. Single values of `type` above |
| `.Name` | `string` | the name of the connection |

*   [What](https://ohmyposh.dev/docs/segments/system/connection#what)
    
*   [Sample Configuration](https://ohmyposh.dev/docs/segments/system/connection#sample-configuration)
    
*   [Options](https://ohmyposh.dev/docs/segments/system/connection#options)
    
*   [Template (info)](https://ohmyposh.dev/docs/segments/system/connection#template-info)
    *   [Properties](https://ohmyposh.dev/docs/segments/system/connection#properties)