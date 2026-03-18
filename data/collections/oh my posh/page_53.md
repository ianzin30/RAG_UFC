Source URL: https://ohmyposh.dev/docs/segments/cli/kubectl

[Skip to main content](https://ohmyposh.dev/docs/segments/cli/kubectl#__docusaurus_skipToContent_fallback)

If you're enjoying Oh My Posh, consider becoming a [sponsor](https://github.com/sponsors/JanDeDobbeleer)
 to keep the project going strong 💪

On this page

What[​](https://ohmyposh.dev/docs/segments/cli/kubectl#what "Direct link to What")

-----------------------------------------------------------------------------------

Display the currently active [Kubernetes](https://kubernetes.io/)
 context name and namespace name.

Sample Configuration[​](https://ohmyposh.dev/docs/segments/cli/kubectl#sample-configuration "Direct link to Sample Configuration")

-----------------------------------------------------------------------------------------------------------------------------------

*   json
*   yaml
*   toml

    {  "type": "kubectl",  "style": "powerline",  "powerline_symbol": "",  "foreground": "#000000",  "background": "#ebcc34",  "template": " 󱃾 {{.Context}}{{if .Namespace}} :: {{.Namespace}}{{end}} ",  "options": {    "context_aliases": {      "arn:aws:eks:eu-west-1:1234567890:cluster/posh": "posh"    },    "cluster_aliases": {      "arn:aws:eks:eu-west-1:1234567890:cluster/posh": "posh-cluster"    }  }}

    type: kubectlstyle: powerlinepowerline_symbol: foreground: "#000000"background: "#ebcc34"template: " 󱃾 {{.Context}}{{if .Namespace}} :: {{.Namespace}}{{end}} "options:  context_aliases:    arn:aws:eks:eu-west-1:1234567890:cluster/posh: posh  cluster_aliases:    arn:aws:eks:eu-west-1:1234567890:cluster/posh: posh-cluster

    type = "kubectl"style = "powerline"powerline_symbol = ""foreground = "#000000"background = "#ebcc34"template = " 󱃾 {{.Context}}{{if .Namespace}} :: {{.Namespace}}{{end}} "[options.context_aliases]"arn:aws:eks:eu-west-1:1234567890:cluster/posh" = "posh"[options.cluster_aliases]"arn:aws:eks:eu-west-1:1234567890:cluster/posh" = "posh-cluster"

Options[​](https://ohmyposh.dev/docs/segments/cli/kubectl#options "Direct link to Options")

--------------------------------------------------------------------------------------------

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `display_error` | `boolean` | `false` | show the error context when failing to retrieve the kubectl information |
| `parse_kubeconfig` | `boolean` | `true` | parse kubeconfig files instead of calling out to kubectl to improve performance |
| `context_aliases` | `object` |     | custom context namespace |
| `cluster_aliases` | `object` |     | custom cluster name |

Template ([info](https://ohmyposh.dev/docs/configuration/templates)
)[​](https://ohmyposh.dev/docs/segments/cli/kubectl#template-info "Direct link to template-info")

----------------------------------------------------------------------------------------------------------------------------------------------------------------------

default template

    {{ .Context }}{{ if .Namespace }} :: {{ .Namespace }}{{ end }}

### Properties[​](https://ohmyposh.dev/docs/segments/cli/kubectl#properties "Direct link to Properties")

| Name | Type | Description |
| --- | --- | --- |
| `.Context` | `string` | the current kubectl context |
| `.Namespace` | `string` | the current kubectl context namespace |
| `.User` | `string` | the current kubectl context user |
| `.Cluster` | `string` | the current kubectl context cluster |

tip

It is common for the Kubernetes "default" namespace to be used when no namespace is provided. If you want your prompt to render an empty current namespace using the word "default", you can use something like this for the template:

    {{.Context}} :: {{if .Namespace}}{{.Namespace}}{{else}}default{{end}}

*   [What](https://ohmyposh.dev/docs/segments/cli/kubectl#what)
    
*   [Sample Configuration](https://ohmyposh.dev/docs/segments/cli/kubectl#sample-configuration)
    
*   [Options](https://ohmyposh.dev/docs/segments/cli/kubectl#options)
    
*   [Template (info)](https://ohmyposh.dev/docs/segments/cli/kubectl#template-info)
    *   [Properties](https://ohmyposh.dev/docs/segments/cli/kubectl#properties)