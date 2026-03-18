Source URL: https://ohmyposh.dev/docs/segments/music/spotify

[Skip to main content](https://ohmyposh.dev/docs/segments/music/spotify#__docusaurus_skipToContent_fallback)

If you're enjoying Oh My Posh, consider becoming a [sponsor](https://github.com/sponsors/JanDeDobbeleer)
 to keep the project going strong 💪

On this page

What[​](https://ohmyposh.dev/docs/segments/music/spotify#what "Direct link to What")

-------------------------------------------------------------------------------------

Show the currently playing song in the [Spotify](https://www.spotify.com/)
 client.

caution

Be aware this can make the prompt a tad bit slower as it needs to get a response from the Spotify player.

On _macOS & Linux_, all states are supported (playing/paused/stopped).

On _Windows/WSL_, **only the playing state is supported** (no information when paused/stopped). It supports fetching information from the native Spotify application and Edge PWA.

Sample Configuration[​](https://ohmyposh.dev/docs/segments/music/spotify#sample-configuration "Direct link to Sample Configuration")

-------------------------------------------------------------------------------------------------------------------------------------

*   json
*   yaml
*   toml

    {  "type": "spotify",  "style": "powerline",  "powerline_symbol": "",  "foreground": "#ffffff",  "background": "#1BD760",  "options": {    "playing_icon": " ",    "paused_icon": " ",    "stopped_icon": " "  }}

    type: spotifystyle: powerlinepowerline_symbol: foreground: "#ffffff"background: "#1BD760"options:  playing_icon: " "  paused_icon: " "  stopped_icon: " "

    type = "spotify"style = "powerline"powerline_symbol = ""foreground = "#ffffff"background = "#1BD760"[options]playing_icon = " "paused_icon = " "stopped_icon = " "

Options[​](https://ohmyposh.dev/docs/segments/music/spotify#options "Direct link to Options")

----------------------------------------------------------------------------------------------

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `playing_icon` | `string` | `\ue602` | text/icon to show when playing |
| `paused_icon` | `string` | `\uf04c` | text/icon to show when paused |
| `stopped_icon` | `string` | `\uf04d` | text/icon to show when stopped |

Template ([info](https://ohmyposh.dev/docs/configuration/templates)
)[​](https://ohmyposh.dev/docs/segments/music/spotify#template-info "Direct link to template-info")

------------------------------------------------------------------------------------------------------------------------------------------------------------------------

default template

    {{ .Icon }}{{ if ne .Status \"stopped\" }}{{ .Artist }} - {{ .Track }}{{ end }}

### Properties[​](https://ohmyposh.dev/docs/segments/music/spotify#properties "Direct link to Properties")

| Name | Type | Description |
| --- | --- | --- |
| `.Status` | `string` | player status (`playing`, `paused`, `stopped`) |
| `.Artist` | `string` | current artist |
| `.Track` | `string` | current track |
| `.Icon` | `string` | icon (based on `.Status`) |

*   [What](https://ohmyposh.dev/docs/segments/music/spotify#what)
    
*   [Sample Configuration](https://ohmyposh.dev/docs/segments/music/spotify#sample-configuration)
    
*   [Options](https://ohmyposh.dev/docs/segments/music/spotify#options)
    
*   [Template (info)](https://ohmyposh.dev/docs/segments/music/spotify#template-info)
    *   [Properties](https://ohmyposh.dev/docs/segments/music/spotify#properties)