Source URL: https://ohmyposh.dev/docs/segments/cli/helm

[Skip to main content](https://ohmyposh.dev/docs/segments/cli/helm#__docusaurus_skipToContent_fallback)

If you're enjoying Oh My Posh, consider becoming a [sponsor](https://github.com/sponsors/JanDeDobbeleer)
 to keep the project going strong 💪

On this page

What[​](https://ohmyposh.dev/docs/segments/cli/helm#what "Direct link to What")

--------------------------------------------------------------------------------

Display the version of [Helm](https://helm.sh/)

Sample Configuration[​](https://ohmyposh.dev/docs/segments/cli/helm#sample-configuration "Direct link to Sample Configuration")

--------------------------------------------------------------------------------------------------------------------------------

*   json
*   yaml
*   toml

    {  "background": "#a7cae1",  "foreground": "#100e23",  "powerline_symbol": "",  "template": "  {{ .Version }}",  "style": "powerline",  "type": "helm"}

    background: "#a7cae1"foreground: "#100e23"powerline_symbol: template: "  {{ .Version }}"style: powerlinetype: helm

    background = "#a7cae1"foreground = "#100e23"powerline_symbol = ""template = "  {{ .Version }}"style = "powerline"type = "helm"

Options[​](https://ohmyposh.dev/docs/segments/cli/helm#options "Direct link to Options")

-----------------------------------------------------------------------------------------

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `display_mode` | `string` | `always` | *   `always`: the segment is always displayed<br>*   `files`: the segment is only displayed when a chart source file `Chart.yaml` (or `Chart.yml`) or helmfile `helmfile.yaml` (or `helmfile.yml`) is present |

Template ([info](https://ohmyposh.dev/docs/configuration/templates)
)[​](https://ohmyposh.dev/docs/segments/cli/helm#template-info "Direct link to template-info")

-------------------------------------------------------------------------------------------------------------------------------------------------------------------

default template

     Helm {{ .Version }}

### Properties[​](https://ohmyposh.dev/docs/segments/cli/helm#properties "Direct link to Properties")

| Name | Type | Description |
| --- | --- | --- |
| `.Version` | `string` | Helm cli version |

*   [What](https://ohmyposh.dev/docs/segments/cli/helm#what)
    
*   [Sample Configuration](https://ohmyposh.dev/docs/segments/cli/helm#sample-configuration)
    
*   [Options](https://ohmyposh.dev/docs/segments/cli/helm#options)
    
*   [Template (info)](https://ohmyposh.dev/docs/segments/cli/helm#template-info)
    *   [Properties](https://ohmyposh.dev/docs/segments/cli/helm#properties)