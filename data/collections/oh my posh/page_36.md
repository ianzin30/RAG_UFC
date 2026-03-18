Source URL: https://ohmyposh.dev/docs/segments/cli/argocd

[Skip to main content](https://ohmyposh.dev/docs/segments/cli/argocd#__docusaurus_skipToContent_fallback)

If you're enjoying Oh My Posh, consider becoming a [sponsor](https://github.com/sponsors/JanDeDobbeleer)
 to keep the project going strong 💪

On this page

What[​](https://ohmyposh.dev/docs/segments/cli/argocd#what "Direct link to What")

----------------------------------------------------------------------------------

Display the current [ArgoCD](https://argo-cd.readthedocs.io/en/stable/)
 context name, user and/or server.

Sample Configuration[​](https://ohmyposh.dev/docs/segments/cli/argocd#sample-configuration "Direct link to Sample Configuration")

----------------------------------------------------------------------------------------------------------------------------------

*   json
*   yaml
*   toml

    {  "type": "argocd",  "style": "powerline",  "powerline_symbol": "",  "foreground": "#ffffff",  "background": "#FFA400",  "template": "  {{ .Name }}:{{ .User }}@{{ .Server }} "}

    type: argocdstyle: powerlinepowerline_symbol: foreground: "#ffffff"background: "#FFA400"template: "  {{ .Name }}:{{ .User }}@{{ .Server }} "

    type = "argocd"style = "powerline"powerline_symbol = ""foreground = "#ffffff"background = "#FFA400"template = "  {{ .Name }}:{{ .User }}@{{ .Server }} "

Template ([info](https://ohmyposh.dev/docs/configuration/templates)
)[​](https://ohmyposh.dev/docs/segments/cli/argocd#template-info "Direct link to template-info")

---------------------------------------------------------------------------------------------------------------------------------------------------------------------

default template

    {{ .Name }}

### Properties[​](https://ohmyposh.dev/docs/segments/cli/argocd#properties "Direct link to Properties")

| Name | Type | Description |
| --- | --- | --- |
| `.Name` | `string` | the current context name |
| `.Server` | `string` | the server of the current context |
| `.User` | `string` | the user of the current context |

*   [What](https://ohmyposh.dev/docs/segments/cli/argocd#what)
    
*   [Sample Configuration](https://ohmyposh.dev/docs/segments/cli/argocd#sample-configuration)
    
*   [Template (info)](https://ohmyposh.dev/docs/segments/cli/argocd#template-info)
    *   [Properties](https://ohmyposh.dev/docs/segments/cli/argocd#properties)