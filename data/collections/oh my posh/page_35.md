Source URL: https://ohmyposh.dev/docs/installation/windows

[Skip to main content](https://ohmyposh.dev/docs/installation/windows#__docusaurus_skipToContent_fallback)

If you're enjoying Oh My Posh, consider becoming a [sponsor](https://github.com/sponsors/JanDeDobbeleer)
 to keep the project going strong 💪

On this page

Set up your terminal[​](https://ohmyposh.dev/docs/installation/windows#set-up-your-terminal "Direct link to Set up your terminal")

-----------------------------------------------------------------------------------------------------------------------------------

While Oh My Posh works on the standard terminal, we advise using the [Windows Terminal](https://github.com/microsoft/terminal)
.

info

To display all icons, we recommend the use of a [Nerd Font](https://ohmyposh.dev/docs/installation/fonts)
.

caution

When using oh-my-posh inside the WSL, make sure to follow the [Linux](https://ohmyposh.dev/docs/installation/linux)
 installation guide.

[![msstore](https://ohmyposh.dev/img/msstore-dark.svg)](https://apps.microsoft.com/detail/xp8k0hkjfrxgck?mode=mini)

Installation[​](https://ohmyposh.dev/docs/installation/windows#installation "Direct link to Installation")

-----------------------------------------------------------------------------------------------------------

*   winget
*   manual
*   chocolatey

Open a PowerShell prompt and run the following command:

    winget install JanDeDobbeleer.OhMyPosh --source winget

Open a PowerShell prompt and run the following command:

    Set-ExecutionPolicy Bypass -Scope Process -Force; Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://ohmyposh.dev/install.ps1'))

info

The chocolatey package is maintained by the community and might not be up to date. In case of issues, please contact the [maintainer](https://github.com/digitalcoyote/chocolatey-packages)
.

Open a PowerShell prompt and run the following command:

    choco install oh-my-posh

Next[​](https://ohmyposh.dev/docs/installation/windows#next "Direct link to Next")

-----------------------------------------------------------------------------------

Now that Oh My Posh is installed, you can go ahead and configure your terminal and shell to get the prompt to look exactly like you want.

*   install a [font](https://ohmyposh.dev/docs/installation/fonts)
    
*   configure your terminal/editor to use the installed font
*   configure your shell to [use Oh My Posh](https://ohmyposh.dev/docs/installation/prompt)
    
*   (optional) configure a theme or [custom prompt configuration](https://ohmyposh.dev/docs/installation/customize)
    

Update[​](https://ohmyposh.dev/docs/installation/windows#update "Direct link to Update")

-----------------------------------------------------------------------------------------

*   winget
*   manual
*   chocolatey

Open a PowerShell prompt and run the following command:

    winget upgrade JanDeDobbeleer.OhMyPosh --source winget

Open a PowerShell prompt and run the following command:

    Set-ExecutionPolicy Bypass -Scope Process -Force; Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://ohmyposh.dev/install.ps1'))

info

The chocolatey package is maintained by the community and might not be up to date. In case of issues, please contact the [maintainer](https://github.com/digitalcoyote/chocolatey-packages)
.

Open a PowerShell prompt and run the following command:

    choco upgrade oh-my-posh

*   [Set up your terminal](https://ohmyposh.dev/docs/installation/windows#set-up-your-terminal)
    
*   [Installation](https://ohmyposh.dev/docs/installation/windows#installation)
    
*   [Next](https://ohmyposh.dev/docs/installation/windows#next)
    
*   [Update](https://ohmyposh.dev/docs/installation/windows#update)