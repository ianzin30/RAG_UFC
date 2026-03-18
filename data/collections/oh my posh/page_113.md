Source URL: https://ohmyposh.dev/docs/segments/scm/jujutsu

[Skip to main content](https://ohmyposh.dev/docs/segments/scm/jujutsu#__docusaurus_skipToContent_fallback)

If you're enjoying Oh My Posh, consider becoming a [sponsor](https://github.com/sponsors/JanDeDobbeleer)
 to keep the project going strong 💪

On this page

What[​](https://ohmyposh.dev/docs/segments/scm/jujutsu#what "Direct link to What")

-----------------------------------------------------------------------------------

Display [Jujutsu](https://www.jj-vcs.dev/)
 information when in a Jujutsu repository.

Sample Configuration[​](https://ohmyposh.dev/docs/segments/scm/jujutsu#sample-configuration "Direct link to Sample Configuration")

-----------------------------------------------------------------------------------------------------------------------------------

*   json
*   yaml
*   toml

    {  "type": "jujutsu",  "style": "powerline",  "powerline_symbol": "",  "foreground": "#193549",  "background": "#ffeb3b",  "options": {    "fetch_status": true,    "ignore_working_copy": false,    "fetch_ahead_counter": true,    "ahead_icon": "⇡"  }}

    type: jujutsustyle: powerlinepowerline_symbol: foreground: "#193549"background: "#ffeb3b"options:  fetch_status: true  ignore_working_copy: false  fetch_ahead_counter: true  ahead_icon: ⇡

    type = "jujutsu"style = "powerline"powerline_symbol = ""foreground = "#193549"background = "#ffeb3b"[options]fetch_status = trueignore_working_copy = falsefetch_ahead_counter = trueahead_icon = "⇡"

Options[​](https://ohmyposh.dev/docs/segments/scm/jujutsu#options "Direct link to Options")

--------------------------------------------------------------------------------------------

### Fetching information[​](https://ohmyposh.dev/docs/segments/scm/jujutsu#fetching-information "Direct link to Fetching information")

As doing Jujutsu (jj) calls can slow down the prompt experience, we do not fetch information by default. Set `status_formats` to `true` to enable fetching additional information (and populate the template).

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `change_id_min_len` | `int` | `0` | `ChangeID` will be at least this many characters, even if a shorter one would be unique |
| `fetch_status` | `boolean` | `false` | fetch the local changes |
| `ignore_working_copy` | `boolean` | `true` | don't snapshot/update the working copy |
| `fetch_ahead_counter` | `boolean` | `false` | fetch a counter for number of changes between working copy and closest bookmark |
| `ahead_icon` | `string` | `\u21e1` | icon/character between bookmark and ahead counter |
| `native_fallback` | `boolean` | `false` | when set to `true` and `jj.exe` is not available when inside a WSL2 shared Windows drive, we will fallback to the native `jj` executable to fetch data. Not all information can be displayed in this case |
| `status_formats` | `map[string]string` |     | a key, value map allowing to override how individual status items are displayed. For example, `"status_formats": { "Added": "Added: %d" }` will display the added count as `Added: 1` instead of `+1`. See the [Status](https://ohmyposh.dev/docs/segments/scm/jujutsu#status)<br> section for available overrides |

Template ([info](https://ohmyposh.dev/docs/configuration/templates)
)[​](https://ohmyposh.dev/docs/segments/scm/jujutsu#template-info "Direct link to template-info")

----------------------------------------------------------------------------------------------------------------------------------------------------------------------

default template

     \uf1fa{{.ChangeID}}{{if .Working.Changed}} \uf044 {{ .Working.String }}{{ end }}

### Properties[​](https://ohmyposh.dev/docs/segments/scm/jujutsu#properties "Direct link to Properties")

| Name | Type | Description |
| --- | --- | --- |
| `.Working` | `Status` | changes in the working copy (see below) |
| `.ChangeID` | `string` | The shortest unique prefix of the working copy change that's at least change\_id\_min\_len long |
| `.ClosestBookmarks` | `string` | Closest bookmark(s) on ancestors |

### Status[​](https://ohmyposh.dev/docs/segments/scm/jujutsu#status "Direct link to Status")

| Name | Type | Description |
| --- | --- | --- |
| `.Modified` | `int` | number of modified files |
| `.Deleted` | `int` | number of deleted files |
| `.Added` | `int` | number of added files |
| `.Moved` | `int` | number of renamed files |
| `.Changed` | `boolean` | if the status contains changes or not |
| `.String` | `string` | a string representation of the changes above |

Local changes use the following syntax:

| Icon | Description |
| --- | --- |
| `~` | Modified |
| `-` | Deleted |
| `+` | Added |
| `>` | Moved |

*   [What](https://ohmyposh.dev/docs/segments/scm/jujutsu#what)
    
*   [Sample Configuration](https://ohmyposh.dev/docs/segments/scm/jujutsu#sample-configuration)
    
*   [Options](https://ohmyposh.dev/docs/segments/scm/jujutsu#options)
    *   [Fetching information](https://ohmyposh.dev/docs/segments/scm/jujutsu#fetching-information)
        
*   [Template (info)](https://ohmyposh.dev/docs/segments/scm/jujutsu#template-info)
    *   [Properties](https://ohmyposh.dev/docs/segments/scm/jujutsu#properties)
        
    *   [Status](https://ohmyposh.dev/docs/segments/scm/jujutsu#status)