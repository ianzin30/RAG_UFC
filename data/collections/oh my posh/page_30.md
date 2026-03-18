Source URL: https://ohmyposh.dev/docs/installation/linux

[Skip to main content](https://ohmyposh.dev/docs/installation/linux#__docusaurus_skipToContent_fallback)

If you're enjoying Oh My Posh, consider becoming a [sponsor](https://github.com/sponsors/JanDeDobbeleer)
 to keep the project going strong 💪

On this page

Set up your terminal[​](https://ohmyposh.dev/docs/installation/linux#set-up-your-terminal "Direct link to Set up your terminal")

---------------------------------------------------------------------------------------------------------------------------------

Oh My Posh uses ANSI color codes under the hood, these should work in every terminal, but you may have to set the environment variable `$TERM` to `xterm-256color` for it to work.

info

To display all icons, we recommend the use of a [Nerd Font](https://ohmyposh.dev/docs/installation/fonts)
.

Installation[​](https://ohmyposh.dev/docs/installation/linux#installation "Direct link to Installation")

---------------------------------------------------------------------------------------------------------

info

Before running the below commands, make sure that you have updated `curl` and the client certificate store on the target machine.

The installation script requires the following tools to be installed:

*   `curl`
*   `unzip`
*   `realpath`
*   `dirname`

Install the latest version for your system by running the following command:

    curl -s https://ohmyposh.dev/install.sh | bash -s

By default the script will install to `~/bin` or `~/.local/bin` depending on which one exists, or the existing Oh My Posh executable's installation folder. If you want to install to a different location you can specify it using the `-d` flag:

    curl -s https://ohmyposh.dev/install.sh | bash -s -- -d ~/bin

Next[​](https://ohmyposh.dev/docs/installation/linux#next "Direct link to Next")

---------------------------------------------------------------------------------

Now that Oh My Posh is installed, you can go ahead and configure your terminal and shell to get the prompt to look exactly like you want.

*   install a [font](https://ohmyposh.dev/docs/installation/fonts)
    
*   configure your terminal/editor to use the installed font
*   configure your shell to [use Oh My Posh](https://ohmyposh.dev/docs/installation/prompt)
    
*   (optional) configure a theme or [custom prompt configuration](https://ohmyposh.dev/docs/installation/customize)
    

*   [Set up your terminal](https://ohmyposh.dev/docs/installation/linux#set-up-your-terminal)
    
*   [Installation](https://ohmyposh.dev/docs/installation/linux#installation)
    
*   [Next](https://ohmyposh.dev/docs/installation/linux#next)