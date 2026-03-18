Source URL: https://ohmyposh.dev/docs/share

[Skip to main content](https://ohmyposh.dev/docs/share#__docusaurus_skipToContent_fallback)

If you're enjoying Oh My Posh, consider becoming a [sponsor](https://github.com/sponsors/JanDeDobbeleer)
 to keep the project going strong 💪

On this page

You can export your prompt to an image which you can share online. You have the ability to align it correctly and add your name for credits too.

caution

Some glyphs aren't rendered correctly, that's not you but the limitations of the renderer. Depending on your config, you might have to tweak the output a little bit.

The oh-my-posh executable has the `config export image` command to export your current theme configuration to a PNG image file (if no other options are specified this will be the name of the config file, or `prompt.png`).

    oh-my-posh config export image

Settings File[​](https://ohmyposh.dev/docs/share#settings-file "Direct link to Settings File")

-----------------------------------------------------------------------------------------------

The `--settings` flag allows you to provide a JSON file to customize the exported image. This file lets you override colors, set the author name, and specify the background color.

~/.image.settings.json

    {  "colors": {    "red": "#FF6B6B",    "blue": "#4ECDC4",    "green": "#45B7D1",    "yellow": "#FFA07A",    "magenta": "#98D8C8",    "cyan": "#F7DC6F"  },  "fonts": {    "regular": "C:/Users/user/Downloads/BigBlueTerminal/BigBlueTerm437NerdFont-Regular.ttf",    "bold": "C:/Users/user/Downloads/BigBlueTerminal/BigBlueTerm437NerdFont-Regular.ttf",    "italic": "C:/Users/user/Downloads/BigBlueTerminal/BigBlueTerm437NerdFont-Regular.ttf"  },  "author": "Your Name",  "background_color": "#282828",  "cursor": "\udb81\udde7"}

### Settings Options[​](https://ohmyposh.dev/docs/share#settings-options "Direct link to Settings Options")

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `colors` | `object` |     | Map of ANSI color names to hex color codes. See [16 ANSI color names](https://ohmyposh.dev/docs/configuration/colors#standard-colors) |
| `author` | `string` |     | Your name or credit to display on the image |
| `background_color` | `string` | `#151515` | Hex code for the image background |
| `fonts` | `object` |     | Font settings for the image, including regular, bold, and italic styles |
| `cursor` | `string` | `_` | A custom cursor |

### Usage[​](https://ohmyposh.dev/docs/share#usage "Direct link to Usage")

    oh-my-posh config export image --settings ~/.image.settings.json

This will export your prompt image using the custom colors and settings from the file.

*   [Settings File](https://ohmyposh.dev/docs/share#settings-file)
    *   [Settings Options](https://ohmyposh.dev/docs/share#settings-options)
        
    *   [Usage](https://ohmyposh.dev/docs/share#usage)