Source URL: https://ohmyposh.dev/docs/installation/macos

[Skip to main content](https://ohmyposh.dev/docs/installation/macos#__docusaurus_skipToContent_fallback)

If you're enjoying Oh My Posh, consider becoming a [sponsor](https://github.com/sponsors/JanDeDobbeleer)
 to keep the project going strong 💪

On this page

Set up your terminal[​](https://ohmyposh.dev/docs/installation/macos#set-up-your-terminal "Direct link to Set up your terminal")

---------------------------------------------------------------------------------------------------------------------------------

As the standard terminal only supports [256 colors](https://ohmyposh.dev/docs/configuration/colors#standard-colors)
, we advise using [iTerm2](https://iterm2.com/)
 or any other modern day macOS terminal that supports ANSI characters.

info

To display all icons, we recommend the use of a [Nerd Font](https://ohmyposh.dev/docs/installation/fonts)
.

Installation[​](https://ohmyposh.dev/docs/installation/macos#installation "Direct link to Installation")

---------------------------------------------------------------------------------------------------------

*   Homebrew
*   MacPorts

A [Homebrew](https://brew.sh/)
 Formula and Cask are available for easy installation.

    brew install jandedobbeleer/oh-my-posh/oh-my-posh

Updating is done via:

    brew update && brew upgrade oh-my-posh

tip

In case you see [strange behaviour](https://github.com/JanDeDobbeleer/oh-my-posh/issues/1287)
 in your shell, reload it after upgrading Oh My Posh. For example in zsh:

    brew update && brew upgrade && exec zsh

You can install Oh My Posh via [MacPorts](https://www.macports.org/)
 which is maintained by the [community](https://ports.macports.org/port/oh-my-posh/)
.

    sudo port selfupdatesudo port install oh-my-posh

Oh My Posh will be installed at `/opt/local/bin/oh-my-posh`.

Updating is done via:

    sudo port selfupdatesudo port upgrade oh-my-posh

More details on the [ports page](https://ports.macports.org/port/oh-my-posh/)
 for Oh My Posh.

Troubleshooting[​](https://ohmyposh.dev/docs/installation/macos#troubleshooting "Direct link to Troubleshooting")

------------------------------------------------------------------------------------------------------------------

tip

If you see an error that says, "[conditional binary operator expected](https://github.com/JanDeDobbeleer/oh-my-posh/discussions/3429)
" you probably need to update to a newer version of bash.

    brew install bashgrep -qxF "$(brew --prefix)/bin/bash" /etc/shells || sudo bash -c 'echo "$(brew --prefix)/bin/bash" >> /etc/shells'chsh -s "$(brew --prefix)/bin/bash" $USER

Next[​](https://ohmyposh.dev/docs/installation/macos#next "Direct link to Next")

---------------------------------------------------------------------------------

Now that Oh My Posh is installed, you can go ahead and configure your terminal and shell to get the prompt to look exactly like you want.

*   install a [font](https://ohmyposh.dev/docs/installation/fonts)
    
*   configure your terminal/editor to use the installed font
*   configure your shell to [use Oh My Posh](https://ohmyposh.dev/docs/installation/prompt)
    
*   (optional) configure a theme or [custom prompt configuration](https://ohmyposh.dev/docs/installation/customize)
    

*   [Set up your terminal](https://ohmyposh.dev/docs/installation/macos#set-up-your-terminal)
    
*   [Installation](https://ohmyposh.dev/docs/installation/macos#installation)
    
*   [Troubleshooting](https://ohmyposh.dev/docs/installation/macos#troubleshooting)
    
*   [Next](https://ohmyposh.dev/docs/installation/macos#next)