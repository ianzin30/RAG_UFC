Source URL: https://ohmyposh.dev/docs/configuration/general

[Skip to main content](https://ohmyposh.dev/docs/configuration/general#__docusaurus_skipToContent_fallback)

If you're enjoying Oh My Posh, consider becoming a [sponsor](https://github.com/sponsors/JanDeDobbeleer)
 to keep the project going strong 💪

On this page

Oh My Posh renders your prompt based on the definition of _blocks_ (like Lego) which contain one or more _segments_. A really simple configuration could look like this. The default format is `json`, but we also support `toml` and `yaml`. There's a [schema](https://github.com/JanDeDobbeleer/oh-my-posh/blob/main/themes/schema.json)
 available which is kept up-to-date and helps with autocomplete and validation of the configuration.

info

There are a few [themes](https://github.com/JanDeDobbeleer/oh-my-posh/tree/main/themes)
 available which are basically predefined configurations. You can use these as they are, or as a starting point to create your own configuration.

*   json
*   yaml
*   toml

    {  "$schema": "https://raw.githubusercontent.com/JanDeDobbeleer/oh-my-posh/main/themes/schema.json",  "final_space": true,  "version": 4,  "blocks": [    {      "type": "prompt",      "alignment": "left",      "segments": [        {          "type": "path",          "style": "powerline",          "powerline_symbol": "\uE0B0",          "foreground": "#ffffff",          "background": "#61AFEF",          "options": {            "style": "folder"          }        }      ]    }  ]}

    # yaml-language-server: $schema=https://raw.githubusercontent.com/JanDeDobbeleer/oh-my-posh/main/themes/schema.jsonfinal_space: trueversion: 4blocks:  - type: prompt    alignment: left    segments:      - type: path        style: powerline        powerline_symbol: ""        foreground: "#ffffff"        background: "#61AFEF"        options:          style: folder

    "$schema" = "https://raw.githubusercontent.com/JanDeDobbeleer/oh-my-posh/main/themes/schema.json"final_space = trueversion = 4[[blocks]]type = "prompt"alignment = "left"  [[blocks.segments]]  type = "path"  style = "powerline"  powerline_symbol = ""  foreground = "#ffffff"  background = "#61AFEF"    [blocks.segments.options]    style = "folder"

With this configuration, a single powerline segment is rendered that shows the name of the folder you're currently in. To set this configuration in combination with an Oh My Posh [executable](https://github.com/JanDeDobbeleer/oh-my-posh/releases/latest)
, use the `--config` flag to set a path to a file containing the above code. The `--shell universal` flag is used to print the prompt without escape characters to see the prompt as it would be shown inside a prompt function for your shell.

caution

The command below will not persist the configuration for your shell but print the prompt in your terminal. If you want to use your own configuration permanently, adjust the prompt configuration to use your custom configuration.

    oh-my-posh print primary --config sample.json --shell uni

If all goes according to plan, you should see the prompt being printed out on the line below. In case you see a lot of boxes with question marks, set up your terminal to use a [supported font](https://ohmyposh.dev/docs/installation/fonts)
 before continuing.

tip

The `--config` flag can accept either a local filepath or a remotely hosted config file.

For example, the following is a valid `--config` flag: `--config 'https://raw.githubusercontent.com/JanDeDobbeleer/oh-my-posh/main/themes/jandedobbeleer.omp.json'`

Settings[​](https://ohmyposh.dev/docs/configuration/general#settings "Direct link to Settings")

------------------------------------------------------------------------------------------------

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `final_space` | `boolean` |     | when true adds a space at the end of the prompt |
| `pwd` | `string` |     | notify terminal of current working directory, values can be `osc99`, `osc7` or `osc51` depending on your terminal. Supports [templates](https://ohmyposh.dev/docs/configuration/templates#config-variables) |
| `terminal_background` | `string` |     | [color](https://ohmyposh.dev/docs/configuration/colors)<br> - terminal background color, set to your terminal's background color when you notice black elements in Windows Terminal or the Visual Studio Code integrated terminal |
| `accent_color` | `string` |     | [color](https://ohmyposh.dev/docs/configuration/colors)<br> - accent color, used as a fallback when the `accent` [color](https://ohmyposh.dev/docs/configuration/colors#standard-colors)<br> is not supported |
| `var` | `map[string]any` |     | config variables to use in [templates](https://ohmyposh.dev/docs/configuration/templates#config-variables)<br>. Can be any value |
| `shell_integration` | `boolean` | `false` | enable shell integration using FinalTerm's OSC sequences. Works in bash, cmd (Clink v1.14.25+), fish, powershell and zsh |
| `enable_cursor_positioning` | `boolean` | `false` | enable fetching the cursor position in bash and zsh to allow automatic hiding of leading newlines when at the top of the shell |
| `patch_pwsh_bleed` | `boolean` | `false` | patch a PowerShell bug where the background colors bleed into the next line at the end of the buffer (can be removed when [this](https://github.com/PowerShell/PowerShell/pull/19019)<br> is merged) |
| `upgrade` | `Upgrade` |     | enable auto upgrade or the upgrade notice. See [Upgrade](https://ohmyposh.dev/docs/installation/upgrade) |
| `iterm_features` | `[]string` | `false` | enable iTerm2 specific features:<br><br>*   `prompt_mark`: add the `iterm2_prompt_mark` [function](https://iterm2.com/documentation-shell-integration.html)<br>     for supported shells<br>*   `current_dir`: expose the current directory for iTerm2<br>*   `remote_host`: expose the current remote and user for iTerm2 |
| `maps` | [`Maps`](https://ohmyposh.dev/docs/configuration/general#maps) |     | a list of custom text mappings |
| `async` | `boolean` | `false` | load the prompt async. Will either load the standard prompt, or allow you to start typing right away. Supported for `pwsh`, `powershell`, `zsh`, `bash` and `fish` |
| `version` | `int` | `4` | the config version, currently at `4` |
| `extends` | `string` |     | the configuration to [extend](https://ohmyposh.dev/docs/configuration/general#extends)<br> from |
| `streaming` | `int` |     | enable streaming mode with a timeout in milliseconds for pending segments. See [streaming](https://ohmyposh.dev/docs/experimental/streaming) |

### Maps[​](https://ohmyposh.dev/docs/configuration/general#maps "Direct link to Maps")

| Name | Type | Description |
| --- | --- | --- |
| `user_name` | `object` | text replacement mapping for user names |
| `host_name` | `object` | text replacement mapping for host names |
| `shell_name` | `object` | text replacement mapping for shell names. This modifies the `.Shell` global property. |

*   json
*   yaml
*   toml

    {  "maps": {    "user_name": {      "jan": "🚀",      "root": "⚡"    },    "host_name": {      "laptop123": "work"    }  }}

    maps:  user_name:    jan: 🚀    root: ⚡  host_name:    laptop123: work

    [maps.user_name]jan = "🚀"root = "⚡"[maps.host_name]laptop123 = "work"

### Extends[​](https://ohmyposh.dev/docs/configuration/general#extends "Direct link to Extends")

The `extends` key allows you to extend an existing configuration. This is useful when you want to build upon a base configuration without duplicating all the settings like a [theme](https://github.com/JanDeDobbeleer/oh-my-posh/tree/main/themes)
. The value should be a path to another configuration file, which can be either local or remote.

Replacing values is done by repeating the value in the new configuration. For example, if you want to change the `accent_color` in a base configuration, you can do so by specifying the `accent_color` key in your new configuration. The new value will override the one in the base configuration.

To override segments and blocks, specify the block using the same `type` and `alignment` as the base configuration. You can then add or modify the segments within that block. Segments are matched by their `alias` or `type`, so you can add new segments or modify existing ones without affecting the rest of the configuration.

For more advanced use cases, you can also specify the index of the `block` or `segment` you want to override. This allows you to override `blocks` or `segments` at specific positions in the configuration. Be aware that the index is **1-based**, so the first `block` or `segment` has an index of `1`.

### JSON Schema Validation[​](https://ohmyposh.dev/docs/configuration/general#json-schema-validation "Direct link to JSON Schema Validation")

As mentioned above, Oh My Posh configurations can utilize JSON Schema to validate their contents. Configurations should include a link to the [external schema document](https://github.com/JanDeDobbeleer/oh-my-posh/blob/main/themes/schema.json)
 which prescribes the appropriate structure and contents for various elements. If your code editor is configured to use JSON Schema, it will compare your configuration to the external document, and issue warnings for discrepancies.

For example, given the following code:

    ..."segments": [  {    "type": "an_invalid_entry",    "template": "{{ if gt .Code 0 }}\uf134{{ end }}",  }]...

Warnings will be raised for type, since `an_invalid_entry` is not in the list of acceptable values, as well as for the entire segment item (enclosed in `{}`), since it lacks the required `style` key. Take advantage of these warnings, and ignore them at your peril.

### Accepted Formats[​](https://ohmyposh.dev/docs/configuration/general#accepted-formats "Direct link to Accepted Formats")

Oh My Posh supports three file formats for configurations: `json`, `yaml`, and `toml`.

Various converters exist to convert between these, although they aren't perfect and will require manual adjustment. Notably, the schema implementation for json is as follows:

    {  "$schema": "https://raw.githubusercontent.com/JanDeDobbeleer/oh-my-posh/main/themes/schema.json"}

While for yaml:

    # yaml-language-server: $schema=https://raw.githubusercontent.com/JanDeDobbeleer/oh-my-posh/main/themes/schema.json

Converters won't catch this change, so you will need to adjust manually.

*   [Settings](https://ohmyposh.dev/docs/configuration/general#settings)
    *   [Maps](https://ohmyposh.dev/docs/configuration/general#maps)
        
    *   [Extends](https://ohmyposh.dev/docs/configuration/general#extends)
        
    *   [JSON Schema Validation](https://ohmyposh.dev/docs/configuration/general#json-schema-validation)
        
    *   [Accepted Formats](https://ohmyposh.dev/docs/configuration/general#accepted-formats)